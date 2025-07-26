from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

def admin_only(admin_id: int):
    def decorator(func):
        @wraps(func)
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if update.effective_user.id != admin_id:
                return
            return await func(update, context, *args, **kwargs)
        return wrapped
    return decorator
