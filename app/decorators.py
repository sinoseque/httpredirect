from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from .config import ALLOWED_ID


def restricted(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user is None or update.effective_user.id != ALLOWED_ID:
            if update.callback_query:
                await update.callback_query.answer("⛔ No autorizado.", show_alert=True)
            else:
                await update.effective_message.reply_text("⛔ No autorizado.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


class UsageError(Exception):
    """Se lanza cuando un comando recibe argumentos inválidos o incompletos."""


def _require_args(args, count: int, usage: str) -> list:
    """Devuelve los `count` primeros argumentos o lanza `UsageError`."""
    if len(args) < count:
        raise UsageError(f"Uso: {usage}")
    return list(args[:count])
