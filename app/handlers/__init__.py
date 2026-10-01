from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters

from .start import start
from .set import set_cmd, set_acestream
from .list import list_cmd
from .delete import del_cmd, clear_cmd
from .addlist import addlist_cmd, handle_json_input
from .reredirect import reredirect_cmd
from .callbacks import button_handler

COMMAND_HANDLERS = [
    CommandHandler("start", start),
    CommandHandler("set", set_cmd),
    CommandHandler("setace", set_acestream),
    CommandHandler("del", del_cmd),
    CommandHandler("clear", clear_cmd),
    CommandHandler("addlist", addlist_cmd),
    CommandHandler("reredirect", reredirect_cmd),
    CommandHandler("list", list_cmd),
]

MESSAGE_HANDLERS = [
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_json_input),
]

CALLBACK_HANDLERS = [
    CallbackQueryHandler(button_handler),
]

ALL_HANDLERS = COMMAND_HANDLERS + MESSAGE_HANDLERS + CALLBACK_HANDLERS
