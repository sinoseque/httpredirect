import os
import json
import re
import asyncio
import logging
from contextlib import asynccontextmanager

import httpx

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import Column, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- CONFIGURACIÓN ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("httpredirect")

TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
ACESTREAM_BASE = os.getenv("URL_BASE_ACESTREAM", "")
CHANNEL_LIST_URL = os.getenv("CHANNEL_LIST_URL", "")
DATABASE_URL = "sqlite:///./data/redirects.db"

os.makedirs("./data", exist_ok=True)

# --- BASE DE DATOS ---
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Redirect(Base):
    __tablename__ = "redirects"
    name = Column(String, primary_key=True, index=True)
    target_url = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- HELPERS ---

def normalize_name(title):
    name = title.lower()
    name = re.sub(r'[^a-z0-9\- ]', '', name)
    name = name.strip().replace(' ', '-')
    name = re.sub(r'-+', '-', name)
    return name

def import_from_json_hashes(data):
    count = 0
    with SessionLocal() as db:
        for item in data.get("hashes", []):
            title = item.get("title", "")
            hash_id = item.get("hash", "")
            if not title or not hash_id:
                continue
            name = normalize_name(title)
            target_url = f"{ACESTREAM_BASE}{hash_id}"
            link = db.query(Redirect).filter(Redirect.name == name).first()
            if link:
                link.target_url = target_url
            else:
                db.add(Redirect(name=name, target_url=target_url))
            count += 1
        db.commit()
    return count

def import_from_json_simple(data):
    count = 0
    with SessionLocal() as db:
        for item in data:
            name = item.get("name", "")
            ace_id = item.get("ace_id", "")
            if not name or not ace_id:
                continue
            target_url = f"{ACESTREAM_BASE}{ace_id}"
            link = db.query(Redirect).filter(Redirect.name == name).first()
            if link:
                link.target_url = target_url
            else:
                db.add(Redirect(name=name, target_url=target_url))
            count += 1
        db.commit()
    return count

# --- HANDLERS DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    keyboard = [[InlineKeyboardButton("📋 Listar enlaces", callback_data='list')]]
    msg = (
        "🚀 **Redirect Bot Activo**\n\n"
        "**Comandos:**\n"
        "🔹 `/set <nombre> <url>` -> Redirección normal\n"
        "🔹 `/setace <nombre> <id>` -> Redirección AceStream\n"
        "🔹 `/del <nombre>` -> Eliminar ruta\n"
        "🔹 `/clear` -> Eliminar **todas** las rutas\n"
        "🔹 `/addlist` -> Importar lista de canales"
    )
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def set_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    try:
        name, url = context.args[0], context.args[1]
        with SessionLocal() as db:
            link = db.query(Redirect).filter(Redirect.name == name).first()
            if link: link.target_url = url
            else: db.add(Redirect(name=name, target_url=url))
            db.commit()
        await update.message.reply_text(f"✅ Guardado: `{name}` -> `{url}`", parse_mode='Markdown')
    except:
        await update.message.reply_text("❌ Error. Uso: `/set nombre url`")

async def set_acestream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    if not ACESTREAM_BASE:
        await update.message.reply_text("❌ Error: `URL_BASE_ACESTREAM` no está definida.")
        return
    try:
        name, ace_id = context.args[0], context.args[1]
        full_url = f"{ACESTREAM_BASE}{ace_id}"
        with SessionLocal() as db:
            link = db.query(Redirect).filter(Redirect.name == name).first()
            if link: link.target_url = full_url
            else: db.add(Redirect(name=name, target_url=full_url))
            db.commit()
        await update.message.reply_text(f"📺 **AceStream guardado:**\n`{name}` -> `{ace_id}`", parse_mode='Markdown')
    except:
        await update.message.reply_text("❌ Error. Uso: `/setace nombre id_acestream`")

async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    try:
        name = context.args[0]
        with SessionLocal() as db:
            link = db.query(Redirect).filter(Redirect.name == name).first()
            if link:
                db.delete(link)
                db.commit()
                await update.message.reply_text(f"🗑 `{name}` eliminado.")
            else:
                await update.message.reply_text(f"❓ No encontré `{name}`.")
    except:
        await update.message.reply_text("❌ Uso: `/del nombre`")

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    with SessionLocal() as db:
        count = db.query(Redirect).count()
        if count == 0:
            await update.message.reply_text("📭 No hay rutas configuradas para borrar.")
            return
    keyboard = [[InlineKeyboardButton("✅ Sí, borrar todo", callback_data="clear_confirm")]]
    await update.message.reply_text(
        f"⚠️ ¿Estás seguro de que quieres borrar **todas** las rutas ({count} en total)?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def addlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    if not ACESTREAM_BASE:
        await update.message.reply_text("❌ Error: `URL_BASE_ACESTREAM` no está definida.")
        return

    buttons = []
    if CHANNEL_LIST_URL:
        buttons.append([InlineKeyboardButton("📡 Desde URL configurada", callback_data="addlist_url")])
    buttons.append([InlineKeyboardButton("🔗 Pegar URL", callback_data="addlist_paste_url")])
    buttons.append([InlineKeyboardButton("📝 Pegar JSON", callback_data="addlist_paste_json")])

    await update.message.reply_text(
        "📥 **Importar lista de canales**\n\n¿De dónde quieres cargar los datos?",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )

async def handle_json_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    mode = context.user_data.pop('awaiting', None)
    if not mode:
        return

    try:
        if mode == 'url':
            async with httpx.AsyncClient() as client:
                resp = await client.get(update.message.text, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            count = import_from_json_hashes(data)
        elif mode == 'simple':
            data = json.loads(update.message.text)
            count = import_from_json_simple(data)
        else:
            data = json.loads(update.message.text)
            count = import_from_json_hashes(data)
        await update.message.reply_text(f"✅ Importación completada: **{count}** rutas añadidas/actualizadas.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error al procesar los datos: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'list':
        with SessionLocal() as db:
            links = db.query(Redirect).all()
            if links:
                # Aquí la modificación: Mostramos nombre y URL (usando monoespaciado para que quede limpio)
                text = "🛰 **Rutas actuales:**\n\n"
                text += "\n".join([f"🔹 `{l.name}` ➔ {l.target_url}" for l in links])
            else:
                text = "No hay rutas configuradas."
            
            await query.edit_message_text(text=text, parse_mode='Markdown', disable_web_page_preview=True)

    elif query.data == 'clear_confirm':
        with SessionLocal() as db:
            count = db.query(Redirect).delete()
            db.commit()
        await query.edit_message_text(f"🗑 Se eliminaron {count} redireccionamientos.")

    elif query.data == 'addlist_url':
        await query.edit_message_text("⏳ Descargando lista desde URL...")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(CHANNEL_LIST_URL, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                count = import_from_json_hashes(data)
            await query.edit_message_text(f"✅ Importación completada: **{count}** rutas añadidas/actualizadas.", parse_mode='Markdown')
        except Exception as e:
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

# --- CICLO DE VIDA ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN no configurado.")
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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_json_input))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Registro automático de comandos
    await application.initialize()
    await application.bot.set_my_commands([
        BotCommand("start", "Menú principal"),
        BotCommand("set", "Redirección normal: /set nombre url"),
        BotCommand("setace", "AceStream: /setace nombre id"),
        BotCommand("del", "Borrar ruta: /del nombre"),
        BotCommand("clear", "Borrar todas las rutas"),
        BotCommand("addlist", "Importar lista de canales")
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
def dynamic_redirect(name: str, db: Session = Depends(get_db)):
    link = db.query(Redirect).filter(Redirect.name == name).first()
    if not link: raise HTTPException(status_code=404)
    return RedirectResponse(url=link.target_url, status_code=302)