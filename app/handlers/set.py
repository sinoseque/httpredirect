from telegram import Update
from telegram.ext import ContextTypes

from ..config import ACESTREAM_BASE, logger
from ..database import RedirectRepository, SessionLocal
from ..decorators import UsageError, _require_args, restricted


@restricted
async def set_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name, url = _require_args(context.args, 2, "/set nombre url")
        if not name.strip():
            await update.effective_message.reply_text("❌ El nombre no puede estar vacío.")
            return
    except UsageError as e:
        await update.effective_message.reply_text(f"❌ {e}")
        return
    try:
        async with SessionLocal() as db:
            await RedirectRepository(db).upsert(name, url)
            await db.commit()
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
        name, ace_id = _require_args(context.args, 2, "/setace nombre id_acestream")
        if not name.strip():
            await update.effective_message.reply_text("❌ El nombre no puede estar vacío.")
            return
        full_url = f"{ACESTREAM_BASE}{ace_id}"
        async with SessionLocal() as db:
            await RedirectRepository(db).upsert(name, full_url)
            await db.commit()
        await update.effective_message.reply_text(f"📺 **AceStream guardado:**\n`{name}` -> `{ace_id}`", parse_mode='Markdown')
    except UsageError as e:
        await update.effective_message.reply_text(f"❌ {e}")
    except Exception as e:
        logger.exception("Error en /setace: %s", e)
        await update.effective_message.reply_text("❌ Error. Uso: `/setace nombre id_acestream`")
