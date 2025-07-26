import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.constants import Role, CallbackData, BAD_PREFIXES, ABOUT_CHAT_ID, ABOUT_MESSAGE_ID
from bot.keyboards import CHOICE_KB, PAY_NOTIFY, ROLE_KB
from bot.config import settings
from bot.domain.services import user_service

logger = logging.getLogger(__name__)

async def intro_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "Мы рады, что вы уделили нам время! Что дальше?",
        reply_markup=CHOICE_KB
    )

async def about_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.copy_message(
        chat_id=update.effective_chat.id,
        from_chat_id=ABOUT_CHAT_ID,
        message_id=ABOUT_MESSAGE_ID
    )

async def want_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Вы уже ведёте мотивационный блог или только начинаете?",
        reply_markup=ROLE_KB,
    )

async def role_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == CallbackData.ROLE_NEW:
        user_service.set_role(uid, Role.NEW_PENDING)
        await q.message.reply_text(
            f"Переведите {settings.PRICE_RUB}₽ на карту {settings.CARD_NUMBER}",
            reply_markup=PAY_NOTIFY
        )
    elif q.data == CallbackData.ROLE_OLD:
        user_service.set_role(uid, Role.OLD_PENDING)
        context.user_data["awaiting_inst_nick"] = True
        await q.message.reply_text("Введите ваш Instagram-ник:")

async def handle_instagram_nick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("awaiting_inst_nick"):
        return
    if any(update.message.text.startswith(p) for p in BAD_PREFIXES):
        return

    uid = update.effective_user.id
    inst_nick = update.message.text.strip().lstrip("@")
    user_service.set_field(uid, "inst_nick", inst_nick)
    context.user_data["awaiting_inst_nick"] = False

    tg_user = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
    await context.bot.send_message(
        settings.ADMIN_ID,
        f"Старичок Instagram: @{inst_nick}\nTelegram: {tg_user}\nuid: {uid}"
    )
    await context.bot.send_message(settings.ADMIN_ID, f"/price {uid} 1000")
    await update.message.reply_text(
        "Ваш аккаунт на модерации. Ожидайте индивидуальную цену.📩"
    )
