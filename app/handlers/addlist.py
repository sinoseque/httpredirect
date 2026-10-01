import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..config import ACESTREAM_BASE, CHANNEL_LIST_URL, logger
from ..decorators import restricted
from ..helpers import _fetch_json, import_from_json_hashes, import_from_json_simple


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

    if mode not in ('url', 'simple'):
        return

    try:
        if mode == 'url':
            data = await _fetch_json(update.effective_message.text)
            count = await import_from_json_hashes(data)
        else:
            data = json.loads(update.effective_message.text)
            count = await import_from_json_simple(data)

        if count == 0:
            await update.effective_message.reply_text(
                "⚠️ No se importó ninguna ruta: revisa que la URL o el JSON tengan el formato correcto.",
                parse_mode='Markdown',
            )
            return

        await update.effective_message.reply_text(
            f"✅ Importación completada: **{count}** rutas añadidas/actualizadas.",
            parse_mode='Markdown',
        )
    except Exception as e:
        logger.exception("Error al procesar entrada JSON: %s", e)
        await update.effective_message.reply_text(f"❌ Error al procesar los datos: {e}")
