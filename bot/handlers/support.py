import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.config import settings
from bot.decorators import admin_only   # тот же декоратор, что и в других хендлерах

logger = logging.getLogger(__name__)
ADMIN_ID = settings.ADMIN_ID           # чтобы не тащить settings во все вызовы


# ---------- сообщение пользователя в поддержку ----------
async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("awaiting_support"):
        return

    user = update.effective_user
    tg_user = f"@{user.username}" if user.username else user.first_name

    await context.bot.send_message(
        ADMIN_ID,
        f"[Support] from {tg_user} (id={user.id}):\n{update.message.text}",
    )

    await context.bot.send_message(ADMIN_ID, f"/reply {user.id} <ответ>")
    await update.message.reply_text(
        "Ваше сообщение отправлено администратору.\n"
        "Ожидайте ответ (не более 2 суток)."
    )
    context.user_data["awaiting_support"] = False


# ---------- ответ администратора пользователю ----------
@admin_only(ADMIN_ID)
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /reply <tg_id> <текст>")
        return

    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Первый аргумент должен быть числовым Telegram‑ID.")
        return

    answer = " ".join(context.args[1:])
    await context.bot.send_message(chat_id=target, text=f"💬 Ответ поддержки:\n{answer}")
    await update.message.reply_text(f"Ответ отправлен пользователю {target}.")
