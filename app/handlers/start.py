from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..decorators import restricted


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
