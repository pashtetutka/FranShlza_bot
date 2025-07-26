import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.constants import Role, CallbackData, YELLOW_FILE_ID, VIDEO_FILE_ID
from bot.keyboards import MENU_KB, get_payment_confirm_kb
from bot.config import settings
from bot.domain.services import user_service, payment_service

logger = logging.getLogger(__name__)

async def notify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    tg_user = f"@{q.from_user.username}" if q.from_user.username else q.from_user.first_name

    kb = get_payment_confirm_kb(uid)
    await context.bot.send_message(
        settings.ADMIN_ID,
        f"Пользователь {tg_user} нажал «Я оплатил»",
        reply_markup=kb
    )
    await q.message.reply_text("Администратор получит уведомление.")

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    try:
        uid = int(q.data.split("_")[1])
    except (IndexError, ValueError):
        return

    role = user_service.get_role(uid)
    if role == Role.NEW_PENDING:
        user_service.set_role(uid, Role.NEW)
    elif role == Role.OLD_PENDING:
        user_service.set_role(uid, Role.OLD)

    user_row = user_service.get(uid)
    price_offer = user_row[6] if user_row else None
    amount = price_offer if price_offer is not None else settings.PRICE_RUB

    payment_service.store(uid, amount)
    await q.message.reply_text(f"Оплата пользователя {uid} подтверждена.")

    await context.bot.send_photo(chat_id=uid, photo=YELLOW_FILE_ID)
    await context.bot.send_message(
        chat_id=uid,
        text="""Итак, первым делом тебе нужно создать новый профиль в инстаграм - это наш фундамент

Аватар - бери мой жёлтый цвет, который я прикрепил. В дальнейшем, при достижении целей, ты сможешь поменять аватар на свой

Имя профиля - сделай что-то понятное, связанное с нашим контентом (пример, @creatorofmotivation)

Описание - добавь смысловую "упаковку" (пример, заряжайся мотивацией каждый день)

И последнее - надо переключить аккаунт с личного на профессиональный, чтобы мы могли видеть все цифры. Инструкция как это сделать далее, нажми кнопку""",
        reply_markup=MENU_KB,
    )
    await context.bot.send_video(chat_id=uid, video=VIDEO_FILE_ID)
