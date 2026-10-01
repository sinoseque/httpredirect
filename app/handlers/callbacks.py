import httpx

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..config import CHANNEL_LIST_URL, REDIRECT_NAME, logger
from ..database import RedirectRepository, SessionLocal
from ..decorators import restricted
from ..helpers import _fetch_json, _build_delete_page, _build_reredirect_page, _build_redirect_list_parts, _send_list_parts, import_from_json_hashes


@restricted
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'list':
        async with SessionLocal() as db:
            links = await RedirectRepository(db).all()
            if not links:
                await query.edit_message_text("No hay rutas configuradas.")
                return

        parts = _build_redirect_list_parts(links)

        async def send_first(part):
            await query.edit_message_text(part, parse_mode='Markdown', disable_web_page_preview=True)

        async def send_rest(part):
            await update.effective_message.reply_text(part, parse_mode='Markdown', disable_web_page_preview=True)

        await _send_list_parts(parts, send_first, send_rest)

    elif query.data == 'clear_confirm':
        async with SessionLocal() as db:
            count = await RedirectRepository(db).delete_all()
            await db.commit()
        await query.edit_message_text(f"🗑 Se eliminaron {count} redireccionamientos.")

    elif query.data == 'addlist_url':
        await query.edit_message_text("⏳ Descargando lista desde URL...")
        try:
            data = await _fetch_json(CHANNEL_LIST_URL)
            count = await import_from_json_hashes(data)
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
        async with SessionLocal() as db:
            repo = RedirectRepository(db)
            reredirect_url = f"@reredirect:{target_name}"
            await repo.upsert(REDIRECT_NAME, reredirect_url)
            await db.commit()

            target = await repo.find_by_name(target_name)
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
        async with SessionLocal() as db:
            deleted = await RedirectRepository(db).delete_by_name(target_name)
            await db.commit()
            if deleted:
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
