import logging
from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes
from bot.constants import IMAGE_FILE_IDS
from bot.keyboards import INTRO_KB, MENU_KB
from bot.domain.services import user_service

logger = logging.getLogger(__name__)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    ref_code = context.args[0] if context.args else None

    user_service.register(uid, ref_code)

    media = [InputMediaPhoto(fid) for fid in IMAGE_FILE_IDS]
    try:
        await context.bot.send_media_group(chat_id=uid, media=media)
    except Exception as e:
        logger.warning("Failed to send intro media: %s", e)

    await update.message.reply_text(
        "Когда ознакомитесь с материалами — нажмите кнопку ниже.",
        reply_markup=INTRO_KB
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    text = update.message.text
    if text == "📞 Поддержка":
        context.user_data["awaiting_support"] = True
        await update.message.reply_text("Напишите ваш вопрос для поддержки.")
    elif text == "👥 Реферальная ссылка":
        await update.message.reply_text(
            f"Ваша реферальная ссылка:\nhttps://t.me/{context.bot.username}?start={uid}"
        )
    elif text == "📊 Статистика":
        await update.message.reply_text("📊 Статистика в разработке.")
