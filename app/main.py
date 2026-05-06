import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import Column, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# --- CONFIGURACIÓN ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.WARNING))
logger = logging.getLogger("httpredirect")

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

# --- HANDLERS DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    keyboard = [[InlineKeyboardButton("📋 Listar", callback_data='list')]]
    await update.message.reply_text("🚀 **Redirect Bot listo.**\n`/set nombre url`", 
                                   reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def set_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_ID: return
    try:
        name, url = context.args[0], context.args[1]
        with SessionLocal() as db:
            link = db.query(Redirect).filter(Redirect.name == name).first()
            if link: link.target_url = url
            else: db.add(Redirect(name=name, target_url=url))
            db.commit()
        await update.message.reply_text(f"✅ `{name}` -> `{url}`")
    except:
        await update.message.reply_text("❌ Usa: `/set nombre url`")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'list':
        with SessionLocal() as db:
            links = db.query(Redirect).all()
            text = "\n".join([f"🔹 `{l.name}` -> {l.target_url}" for l in links]) if links else "Vacío."
            await query.edit_message_text(text=f"🛰 **Enlaces:**\n{text}", parse_mode='Markdown')

# --- CICLO DE VIDA (LIFESPAN) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configuración inicial del Bot
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set", set_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Arrancamos el bot correctamente
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot de Telegram iniciado.")
    
    yield  # Aquí es donde corre FastAPI
    
    # Al cerrar la app, apagamos el bot limpiamente
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