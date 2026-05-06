import os
import asyncio
import logging
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import Column, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# --- CONFIGURACIÓN DE LOGS ---
# Lee el nivel de log de la variable de entorno, por defecto WARNING
log_level_str = os.getenv("LOG_LEVEL", "WARNING").upper()
# Mapeo simple para asegurar que el string sea un nivel válido
log_level = getattr(logging, log_level_str, logging.WARNING)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("httpredirect")

# --- CONFIGURACIÓN DE ENTORNO ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
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

# --- LÓGICA DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID:
        await update.message.reply_text("❌ No autorizado.")
        return

    keyboard = [
        [InlineKeyboardButton("📋 Listar", callback_data='list')],
        [InlineKeyboardButton("❓ Ayuda", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛠 **httpredirect Bot**\nUsa `/set nombre url` para crear una ruta:", 
                                   reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ALLOWED_ID: return

    await query.answer()
    db = SessionLocal()
    
    if query.data == 'list':
        links = db.query(Redirect).all()
        text = "🛰 **Redirecciones:**\n\n" + "\n".join([f"🔹 `{l.name}` -> {l.target_url}" for l in links]) if links else "Vacío."
        await query.edit_message_text(text=text, parse_mode='Markdown')
    
    elif query.data == 'help':
        await query.edit_message_text(text="`/set <nombre> <url>`\n`/del <nombre>`", parse_mode='Markdown')
    db.close()

async def set_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    try:
        name, url = context.args[0], context.args[1]
        db = SessionLocal()
        link = db.query(Redirect).filter(Redirect.name == name).first()
        if link: link.target_url = url
        else: db.add(Redirect(name=name, target_url=url))
        db.commit()
        db.close()
        await update.message.reply_text(f"✅ `{name}` -> `{url}`")
    except:
        await update.message.reply_text("❌ Error. Usa: `/set nombre url`")

async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    try:
        name = context.args[0]
        db = SessionLocal()
        link = db.query(Redirect).filter(Redirect.name == name).first()
        if link:
            db.delete(link)
            db.commit()
            await update.message.reply_text(f"🗑 `{name}` eliminado.")
        db.close()
    except: pass

# --- FASTAPI ---
app = FastAPI(title="httpredirect API")

@app.on_event("startup")
async def startup_event():
    if not TOKEN: return
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set", set_cmd))
    application.add_handler(CommandHandler("del", del_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))

    asyncio.create_task(application.initialize())
    asyncio.create_task(application.start())
    asyncio.create_task(application.updater.start_polling())
    logger.info("httpredirect bot online.")

@app.get("/r/{name}")
def dynamic_redirect(name: str, db: Session = Depends(get_db)):
    link = db.query(Redirect).filter(Redirect.name == name).first()
    if not link: raise HTTPException(status_code=404)
    return RedirectResponse(url=link.target_url, status_code=302)

@app.get("/list")
def list_redirects(db: Session = Depends(get_db)):
    return db.query(Redirect).all()

@app.post("/set")
def api_set(name: str, url: str, db: Session = Depends(get_db)):
    link = db.query(Redirect).filter(Redirect.name == name).first()
    if link: link.target_url = url
    else: db.add(Redirect(name=name, target_url=url))
    db.commit()
    return {"status": "ok"}

@app.delete("/delete/{name}")
def api_delete(name: str, db: Session = Depends(get_db)):
    link = db.query(Redirect).filter(Redirect.name == name).first()
    if link:
        db.delete(link)
        db.commit()
    return {"status": "deleted"}