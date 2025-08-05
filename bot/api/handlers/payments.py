from __future__ import annotations

import os
from telegram import (
    Update,
    WebAppInfo,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import ContextTypes, CommandHandler, Application, filters, MessageHandler

__all__ = ["setup"]

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    frontend_url = (
        context.bot_data.get("FRONTEND_URL")
        or os.getenv("FRONTEND_URL")
    )
    if not frontend_url:
        await update.message.reply_text(
            "⚠️ Форма оплаты временно недоступна. Попробуйте позже."
        )
        return

    button = KeyboardButton(
        text="💳 Оформить подписку",
        web_app=WebAppInfo(url=frontend_url),
    )
    reply_markup = ReplyKeyboardMarkup(
        [[button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "Нажмите кнопку, чтобы открыть форму оплаты:",
        reply_markup=reply_markup,
    )


async def open_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data.get("lava_link")
    if not url:
        return
    await update.message.reply_text("Открываю форму оплаты…")
    await update.effective_chat.send_message(
        "🔗", 
        disable_web_page_preview=True,
        reply_markup=None,
        reply_to_message_id=update.message.message_id,
    )
    await update.message.reply_text(url)

def setup(app: Application) -> None:
    app.add_handler(CommandHandler(["buy", "pay"], buy))
    app.add_handler(MessageHandler(
        filters.Regex("💳 Оформить подписку"),
        open_payment
    ))
   
