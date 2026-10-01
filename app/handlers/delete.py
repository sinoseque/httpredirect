from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..config import logger
from ..database import RedirectRepository, SessionLocal
from ..decorators import _require_args, restricted
from ..helpers import _build_delete_page


@restricted
async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('delete_target', None)
    if context.args:
        name = _require_args(context.args, 1, "/del nombre")[0]
        async with SessionLocal() as db:
            if not await RedirectRepository(db).find_by_name(name):
                await update.effective_message.reply_text(f"❓ No encontré `{name}`.")
                return
        keyboard = [
            [InlineKeyboardButton("✅ Sí, borrar", callback_data=f"delete_execute:{name}")],
            [InlineKeyboardButton("❌ No, cancelar", callback_data="delete_cancel_named")]
        ]
        await update.effective_message.reply_text(
            f"⚠️ ¿Estás seguro de que quieres borrar `{name}`?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        async with SessionLocal() as db:
            links = await RedirectRepository(db).all()
            if not links:
                await update.effective_message.reply_text("📭 No hay rutas configuradas para borrar.")
                return
        context.user_data['delete_links'] = [(l.name, l.target_url) for l in links]
        text, reply_markup = _build_delete_page(context.user_data['delete_links'], 0)
        await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')


@restricted
async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with SessionLocal() as db:
        count = await RedirectRepository(db).count()
        if count == 0:
            await update.effective_message.reply_text("📭 No hay rutas configuradas para borrar.")
            return
    keyboard = [[InlineKeyboardButton("✅ Sí, borrar todo", callback_data="clear_confirm")]]
    await update.effective_message.reply_text(
        f"⚠️ ¿Estás seguro de que quieres borrar **todas** las rutas ({count} en total)?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
