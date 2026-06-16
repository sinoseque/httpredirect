import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import Column, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# --- CONFIGURACIÓN ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("httpredirect")

TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
ACESTREAM_BASE = os.getenv("URL_BASE_ACESTREAM", "")
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
        "🔹 `/clear` -> Eliminar **todas** las rutas"
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
    application.add_handler(CallbackQueryHandler(button_handler))

    # Registro automático de comandos
    await application.initialize()
    await application.bot.set_my_commands([
        BotCommand("start", "Menú principal"),
        BotCommand("set", "Redirección normal: /set nombre url"),
        BotCommand("setace", "AceStream: /setace nombre id"),
        BotCommand("del", "Borrar ruta: /del nombre"),
        BotCommand("clear", "Borrar todas las rutas")
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