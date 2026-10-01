from telegram import Update
from telegram.ext import ContextTypes

from ..config import REDIRECT_NAME, logger
from ..database import RedirectRepository, SessionLocal
from ..decorators import restricted
from ..helpers import _build_reredirect_page


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

    async with SessionLocal() as db:
        links = await RedirectRepository(db).all()
        links = [l for l in links if l.name != REDIRECT_NAME]
        if not links:
            await update.effective_message.reply_text("📭 No hay otras rutas configuradas para apuntar.")
            return

    context.user_data['reredirect_links'] = [(l.name, l.target_url) for l in links]
    text, reply_markup = _build_reredirect_page(context.user_data['reredirect_links'], 0)
    await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
