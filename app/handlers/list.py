from telegram import Update
from telegram.ext import ContextTypes

from ..database import RedirectRepository, SessionLocal
from ..decorators import restricted
from ..helpers import _build_redirect_list_parts, _send_list_parts


@restricted
async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with SessionLocal() as db:
        links = await RedirectRepository(db).all()
        if not links:
            await update.effective_message.reply_text("📭 No hay rutas configuradas.")
            return

    parts = _build_redirect_list_parts(links)

    async def send_first(part):
        await update.effective_message.reply_text(part, parse_mode='Markdown', disable_web_page_preview=True)

    async def send_rest(part):
        await update.effective_message.reply_text(part, parse_mode='Markdown', disable_web_page_preview=True)

    await _send_list_parts(parts, send_first, send_rest)
