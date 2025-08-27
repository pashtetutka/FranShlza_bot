from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not chat:
        return
    await update.message.reply_text(
        f"Chat ID: <code>{chat.id}</code>\nType: <b>{chat.type}</b>",
        parse_mode=ParseMode.HTML,
    )

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    username = f"@{user.username}" if user.username else "—"
    await update.message.reply_text(
        f"Your user ID: <code>{user.id}</code>\nUsername: <b>{username}</b>",
        parse_mode=ParseMode.HTML,
    )
