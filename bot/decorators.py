from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

def admin_only(admin_id: int):
    def decorator(func):
        @wraps(func)
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            chat = update.effective_chat
            if not chat or chat.id != admin_id:
                return 
            return await func(update, context, *args, **kwargs)
        return wrapped
    return decorator
