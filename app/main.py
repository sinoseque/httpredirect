import json
import re
import asyncio
from contextlib import asynccontextmanager

import httpx

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, PlainTextResponse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from functools import wraps

from .config import TOKEN, ALLOWED_ID, ACESTREAM_BASE, CHANNEL_LIST_URL, REDIRECT_NAME, logger
from .database import SessionLocal, Redirect


def restricted(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id != ALLOWED_ID:
            if update.callback_query:
                await update.callback_query.answer("⛔ No autorizado.", show_alert=True)
            else:
                await update.effective_message.reply_text("⛔ No autorizado.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# --- HELPERS ---

def normalize_name(title):
    name = title.lower()
    name = name.replace('*', 'o').replace('&', 'y').replace('@', 'a').replace('#', 'h')
    name = re.sub(r'[^a-z0-9\- ]', '', name)
    name = name.strip().replace(' ', '-')
    name = re.sub(r'-+', '-', name)
    return name


def _resolve_duplicates(items):
    seen = {}
    resolved = []
    for name, target_url in items:
        if name in seen:
            seen[name] += 1
            resolved.append((f"{name}-{seen[name]}", target_url))
        else:
            seen[name] = 0
            resolved.append((name, target_url))
    return resolved


PAGE_SIZE = 10


def _build_reredirect_page(links, page):
    total_pages = (len(links) + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_links = links[start:end]

    buttons = [InlineKeyboardButton(name, callback_data=f"reredirect:{name}") for name, _ in page_links]
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Anterior", callback_data=f"reredirect_page:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Siguiente ▶️", callback_data=f"reredirect_page:{page+1}"))
    if nav:
        keyboard.append(nav)

    text = (
        f"🎯 **Selecciona la ruta a la que quieres que apunte `{REDIRECT_NAME}`:**\n"
        f"Página {page+1}/{total_pages}"
    )
    return text, InlineKeyboardMarkup(keyboard)


def _build_delete_page(links, page):
    total_pages = (len(links) + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_links = links[start:end]

    buttons = [InlineKeyboardButton(name, callback_data=f"delete_select:{name}") for name, _ in page_links]
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Anterior", callback_data=f"delete_page:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Siguiente ▶️", callback_data=f"delete_page:{page+1}"))
    if nav:
        keyboard.append(nav)

    text = (
        f"🗑 **Selecciona la ruta que quieres borrar:**\n"
        f"Página {page+1}/{total_pages}"
    )
    return text, InlineKeyboardMarkup(keyboard)


async def _fetch_json(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url, timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True
        )
        logger.debug("GET %s -> status %d", url, resp.status_code)
        logger.debug("Respuesta: %s", resp.text[:500])
        resp.raise_for_status()
        return resp.json()


def _upsert_redirects(items):
    with SessionLocal() as db:
        for name, target_url in items:
            link = db.query(Redirect).filter(Redirect.name == name).first()
            if link:
                link.target_url = target_url
            else:
                db.add(Redirect(name=name, target_url=target_url))
        db.commit()
    return len(items)


def import_from_json_hashes(data):
    if not ACESTREAM_BASE:
        raise ValueError("URL_BASE_ACESTREAM no está definida.")
    items = []
    for item in data.get("hashes", []):
        title = item.get("title", "")
        hash_id = item.get("hash", "")
        if not title or not hash_id:
            continue
        name = normalize_name(title)
        items.append((name, f"{ACESTREAM_BASE}{hash_id}"))
    items = _resolve_duplicates(items)
    return _upsert_redirects(items)


def import_from_json_simple(data):
    if not ACESTREAM_BASE:
        raise ValueError("URL_BASE_ACESTREAM no está definida.")
    items = []
    for item in data:
        name = item.get("name", "")
        ace_id = item.get("ace_id", "")
        if not name or not ace_id:
            continue
        items.append((name, f"{ACESTREAM_BASE}{ace_id}"))
    items = _resolve_duplicates(items)
    return _upsert_redirects(items)


# --- HANDLERS DEL BOT ---

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📋 Listar enlaces", callback_data='list')]]
    msg = (
        "🚀 **Redirect Bot Activo**\n\n"
        "**Comandos:**\n"
        "🔹 `/set <nombre> <url>` -> Redirección normal\n"
        "🔹 `/setace <nombre> <id>` -> Redirección AceStream\n"
        "🔹 `/del <nombre>` -> Borrar ruta (con confirmación)\n"
        "🔹 `/clear` -> Eliminar **todas** las rutas\n"
        "🔹 `/addlist` -> Importar lista de canales\n"
        "🔹 `/list` -> Listar todas las rutas\n"
        "🔹 `/reredirect` -> Apuntar `REDIRECT_NAME` a otro canal"
    )
    await update.effective_message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


@restricted
async def set_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name, url = context.args[0], context.args[1]
        with SessionLocal() as db:
            link = db.query(Redirect).filter(Redirect.name == name).first()
            if link: link.target_url = url
            else: db.add(Redirect(name=name, target_url=url))
            db.commit()
        await update.effective_message.reply_text(f"✅ Guardado: `{name}` -> `{url}`", parse_mode='Markdown')
    except Exception as e:
        logger.exception("Error en /set: %s", e)
        await update.effective_message.reply_text("❌ Error. Uso: `/set nombre url`")


@restricted
async def set_acestream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ACESTREAM_BASE:
        await update.effective_message.reply_text("❌ Error: `URL_BASE_ACESTREAM` no está definida.")
        return
    try:
        name, ace_id = context.args[0], context.args[1]
        full_url = f"{ACESTREAM_BASE}{ace_id}"
        with SessionLocal() as db:
            link = db.query(Redirect).filter(Redirect.name == name).first()
            if link: link.target_url = full_url
            else: db.add(Redirect(name=name, target_url=full_url))
            db.commit()
        await update.effective_message.reply_text(f"📺 **AceStream guardado:**\n`{name}` -> `{ace_id}`", parse_mode='Markdown')
    except Exception as e:
        logger.exception("Error en /setace: %s", e)
        await update.effective_message.reply_text("❌ Error. Uso: `/setace nombre id_acestream`")


@restricted
async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with SessionLocal() as db:
        links = db.query(Redirect).all()
        if not links:
            await update.effective_message.reply_text("📭 No hay rutas configuradas.")
            return

    lines = [f"🔹 `{l.name}` ➔ {l.target_url}" for l in links]
    header = "🛰 **Rutas actuales:**\n\n"
    max_len = 4000

    parts = []
    current = header
    for line in lines:
        candidate = current + line + "\n"
        if len(candidate) > max_len:
            parts.append(current)
            current = header + line + "\n"
        else:
            current = candidate
    if current:
        parts.append(current)

    await update.effective_message.reply_text(parts[0], parse_mode='Markdown', disable_web_page_preview=True)
    for part in parts[1:]:
        await update.effective_message.reply_text(part, parse_mode='Markdown', disable_web_page_preview=True)


@restricted
async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        name = context.args[0]
        with SessionLocal() as db:
            link = db.query(Redirect).filter(Redirect.name == name).first()
            if not link:
                await update.effective_message.reply_text(f"❓ No encontré `{name}`.")
                return
        keyboard = [
            [InlineKeyboardButton("✅ Sí, borrar", callback_data=f"delete_execute:{name}")],
            [InlineKeyboardButton("❌ No, cancelar", callback_data="delete_cancel_named")]
        ]
        await update.effective_message.reply_text(
            f"⚠️ ¿Estás seguro de que quieres borrar `{name}`?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        with SessionLocal() as db:
            links = db.query(Redirect).all()
            if not links:
                await update.effective_message.reply_text("📭 No hay rutas configuradas para borrar.")
                return
        context.user_data['delete_links'] = [(l.name, l.target_url) for l in links]
        text, reply_markup = _build_delete_page(context.user_data['delete_links'], 0)
        await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


@restricted
async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with SessionLocal() as db:
        count = db.query(Redirect).count()
        if count == 0:
            await update.effective_message.reply_text("📭 No hay rutas configuradas para borrar.")
            return
    keyboard = [[InlineKeyboardButton("✅ Sí, borrar todo", callback_data="clear_confirm")]]
    await update.effective_message.reply_text(
        f"⚠️ ¿Estás seguro de que quieres borrar **todas** las rutas ({count} en total)?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


@restricted
async def addlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ACESTREAM_BASE:
        await update.effective_message.reply_text("❌ Error: `URL_BASE_ACESTREAM` no está definida.")
        return

    buttons = []
    if CHANNEL_LIST_URL:
        buttons.append([InlineKeyboardButton("📡 Desde URL configurada", callback_data="addlist_url")])
    buttons.append([InlineKeyboardButton("🔗 Pegar URL", callback_data="addlist_paste_url")])
    buttons.append([InlineKeyboardButton("📝 Pegar JSON", callback_data="addlist_paste_json")])

    await update.effective_message.reply_text(
        "📥 **Importar lista de canales**\n\n¿De dónde quieres cargar los datos?",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )


@restricted
async def handle_json_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.pop('awaiting', None)
    if not mode:
        return

    try:
        if mode == 'url':
            data = await _fetch_json(update.effective_message.text)
            count = import_from_json_hashes(data)
        elif mode == 'simple':
            data = json.loads(update.effective_message.text)
            count = import_from_json_simple(data)
        else:
            data = json.loads(update.effective_message.text)
            count = import_from_json_hashes(data)
        await update.effective_message.reply_text(f"✅ Importación completada: **{count}** rutas añadidas/actualizadas.", parse_mode='Markdown')
    except Exception as e:
        logger.exception("Error al procesar entrada JSON: %s", e)
        await update.effective_message.reply_text(f"❌ Error al procesar los datos: {e}")


@restricted
async def reredirect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not REDIRECT_NAME:
        await update.effective_message.reply_text(
            "❌ **REDIRECT_NAME** no está definida.\n\n"
            "Para usar `/reredirect` necesitas añadir la variable de entorno "
            "`REDIRECT_NAME` en tu `docker-compose.yml`:\n\n"
            "```yaml\n"
            "environment:\n"
            "  - REDIRECT_NAME=f\n"
            "```\n\n"
            "Después de añadirla, reinicia el contenedor.",
            parse_mode='Markdown'
        )
        return

    with SessionLocal() as db:
        links = db.query(Redirect).filter(Redirect.name != REDIRECT_NAME).all()
        if not links:
            await update.effective_message.reply_text("📭 No hay otras rutas configuradas para apuntar.")
            return

    context.user_data['reredirect_links'] = [(l.name, l.target_url) for l in links]
    text, reply_markup = _build_reredirect_page(context.user_data['reredirect_links'], 0)
    await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


@restricted
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'list':
        with SessionLocal() as db:
            links = db.query(Redirect).all()
            if not links:
                await query.edit_message_text("No hay rutas configuradas.")
                return

        lines = [f"🔹 `{l.name}` ➔ {l.target_url}" for l in links]
        header = "🛰 **Rutas actuales:**\n\n"
        max_len = 4000

        parts = []
        current = header
        for line in lines:
            candidate = current + line + "\n"
            if len(candidate) > max_len:
                parts.append(current)
                current = header + line + "\n"
            else:
                current = candidate
        if current:
            parts.append(current)

        await query.edit_message_text(parts[0], parse_mode='Markdown', disable_web_page_preview=True)
        for part in parts[1:]:
            await update.effective_message.reply_text(part, parse_mode='Markdown', disable_web_page_preview=True)

    elif query.data == 'clear_confirm':
        with SessionLocal() as db:
            count = db.query(Redirect).delete()
            db.commit()
        await query.edit_message_text(f"🗑 Se eliminaron {count} redireccionamientos.")

    elif query.data == 'addlist_url':
        await query.edit_message_text("⏳ Descargando lista desde URL...")
        try:
            data = await _fetch_json(CHANNEL_LIST_URL)
            count = import_from_json_hashes(data)
            await query.edit_message_text(f"✅ Importación completada: **{count}** rutas añadidas/actualizadas.", parse_mode='Markdown')
        except httpx.HTTPStatusError as e:
            logger.exception("Error HTTP %s en URL configurada", e.response.status_code)
            await query.edit_message_text(f"❌ Error HTTP {e.response.status_code} al descargar desde la URL configurada.")
        except Exception as e:
            logger.exception("Error importando desde URL configurada: %s", e)
            await query.edit_message_text(f"❌ Error al descargar o procesar: {e}")

    elif query.data == 'addlist_paste_url':
        context.user_data['awaiting'] = 'url'
        await query.edit_message_text(
            "🔗 **Pega la URL** del JSON que quieras importar.\n\n"
            "El JSON debe tener el formato con `hashes`, `title` y `hash` (igual que la URL configurada).",
            parse_mode='Markdown'
        )

    elif query.data == 'addlist_paste_json':
        context.user_data['awaiting'] = 'simple'
        example = (
            '```json\n[\n'
            '  {"name": "canal1", "ace_id": "313213b3b99c0f..."},\n'
            '  {"name": "canal2", "ace_id": "8522af51ae7189..."}\n'
            ']\n```'
        )
        await query.edit_message_text(
            f"📝 **Pega el JSON** con los canales a importar.\n\n"
            f"Formato esperado:\n{example}",
            parse_mode='Markdown'
        )

    elif query.data.startswith('reredirect_page:'):
        page = int(query.data[len('reredirect_page:'):])
        links = context.user_data.get('reredirect_links', [])
        text, reply_markup = _build_reredirect_page(links, page)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data.startswith('reredirect:'):
        target_name = query.data[len('reredirect:'):]
        context.user_data.pop('reredirect_links', None)
        with SessionLocal() as db:
            link = db.query(Redirect).filter(Redirect.name == REDIRECT_NAME).first()
            reredirect_url = f"@reredirect:{target_name}"
            if link:
                link.target_url = reredirect_url
            else:
                db.add(Redirect(name=REDIRECT_NAME, target_url=reredirect_url))
            db.commit()

            target = db.query(Redirect).filter(Redirect.name == target_name).first()
            target_url = target.target_url if target else '?'

        await query.edit_message_text(
            f"✅ **Ruta actualizada:**\n\n"
            f"`{REDIRECT_NAME}` ➔ `{target_name}` ➔ {target_url}",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    elif query.data.startswith('delete_page:'):
        page = int(query.data[len('delete_page:'):])
        links = context.user_data.get('delete_links', [])
        text, reply_markup = _build_delete_page(links, page)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data.startswith('delete_select:'):
        target_name = query.data[len('delete_select:'):]
        context.user_data['delete_target'] = target_name
        keyboard = [
            [InlineKeyboardButton("✅ Sí, borrar", callback_data=f"delete_execute:{target_name}")],
            [InlineKeyboardButton("❌ No, volver", callback_data="delete_cancel")]
        ]
        await query.edit_message_text(
            f"⚠️ ¿Estás seguro de que quieres borrar `{target_name}`?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif query.data.startswith('delete_execute:'):
        target_name = query.data[len('delete_execute:'):]
        context.user_data.pop('delete_links', None)
        context.user_data.pop('delete_target', None)
        with SessionLocal() as db:
            link = db.query(Redirect).filter(Redirect.name == target_name).first()
            if link:
                db.delete(link)
                db.commit()
                await query.edit_message_text(f"🗑 `{target_name}` eliminado.")
            else:
                await query.edit_message_text(f"❓ No encontré `{target_name}`.")

    elif query.data == 'delete_cancel':
        context.user_data.pop('delete_target', None)
        links = context.user_data.get('delete_links', [])
        text, reply_markup = _build_delete_page(links, 0)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == 'delete_cancel_named':
        await query.edit_message_text("❌ Cancelado.")


# --- CICLO DE VIDA ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = []
    if not TOKEN:
        missing.append("TELEGRAM_TOKEN")
    if ALLOWED_ID == 0:
        missing.append("ALLOWED_USER_ID")
    if missing:
        logger.error("Variables de entorno no configuradas: %s", ", ".join(missing))
        yield
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set", set_cmd))
    application.add_handler(CommandHandler("setace", set_acestream))
    application.add_handler(CommandHandler("del", del_cmd))
    application.add_handler(CommandHandler("clear", clear_cmd))
    application.add_handler(CommandHandler("addlist", addlist_cmd))
    application.add_handler(CommandHandler("reredirect", reredirect_cmd))
    application.add_handler(CommandHandler("list", list_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_json_input))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Registro automático de comandos
    await application.initialize()
    await application.bot.set_my_commands([
        BotCommand("start", "Menú principal"),
        BotCommand("set", "Redirección normal: /set nombre url"),
        BotCommand("setace", "AceStream: /setace nombre id"),
        BotCommand("del", "Borrar ruta: /del nombre o lista interactiva"),
        BotCommand("clear", "Borrar todas las rutas"),
        BotCommand("addlist", "Importar lista de canales"),
        BotCommand("reredirect", "Apuntar ruta fija a otro canal"),
        BotCommand("list", "Listar todas las rutas")
    ])

    await application.start()
    await application.updater.start_polling()
    logger.info("Bot y comandos registrados correctamente.")

    yield

    await application.updater.stop()
    await application.stop()
    await application.shutdown()


# --- FASTAPI ---

app = FastAPI(title="httpredirect", lifespan=lifespan)


@app.get("/r/{name}")
def dynamic_redirect(name: str):
    with SessionLocal() as db:
        link = db.query(Redirect).filter(Redirect.name == name).first()
        if not link:
            raise HTTPException(status_code=404)

        target = link.target_url
        visited = {name}
        while target.startswith("@reredirect:"):
            inner_name = target[len("@reredirect:"):]
            if inner_name in visited:
                return PlainTextResponse(
                    "⚠️ Ciclo detectado en la cadena de redirecciones.",
                    status_code=404
                )
            visited.add(inner_name)
            inner = db.query(Redirect).filter(Redirect.name == inner_name).first()
            if not inner:
                return PlainTextResponse(
                    f"⚠️ La ruta '{name}' apunta a '{inner_name}', pero esa ruta ya no existe.",
                    status_code=404
                )
            target = inner.target_url

        if target.startswith("http"):
            try:
                with httpx.Client(follow_redirects=True, timeout=10) as client:
                    resp = client.get(target)
                    target = str(resp.url)
            except Exception:
                logger.debug("Error al resolver cadena de redirects para %s", target)

        return RedirectResponse(url=target, status_code=302)


@app.head("/r/{name}")
def dynamic_redirect_head(name: str):
    return dynamic_redirect(name)
