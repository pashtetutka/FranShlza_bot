from __future__ import annotations
from bot.keyboards import CHOICE_KB, ROLE_KB, MENU_KB

import os
import logging
from telegram.constants import ParseMode
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import ContextTypes
from telegram import Update

from bot.db.subscriptions import safe_set_role, upsert_user_basic
from bot.constants import Role, CallbackData, ABOUT_CHAT_ID, ABOUT_MESSAGE_ID
from bot.domain.services import user_service
from bot.config import settings

logger = logging.getLogger(__name__)


async def intro_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    q = update.callback_query
    await q.answer()

    await update.callback_query.message.reply_text(
        "Мы рады, что вы уделили нам время! Что дальше?",
        reply_markup=CHOICE_KB
    )

async def about_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()

    chat_id = q.message.chat_id

    try:
        await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=ABOUT_CHAT_ID,
            message_id=ABOUT_MESSAGE_ID,
        )
    except Exception as e:
        logger.exception("about_project: copy_message failed: %s", e)

    cta_text = (
        "<b>Готовы присоедениться?</b>\n\n"
        "Тогда ждем вас в нашем сообществе. Если остались вопросы — «Поддержка»."
    )
    cta_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Хочу к вам", callback_data=CallbackData.WANT_JOIN.value)],
        [InlineKeyboardButton("📞 Поддержка", callback_data="support:start")],
    ])
    await context.bot.send_message(chat_id=chat_id, text=cta_text, parse_mode=ParseMode.HTML, reply_markup=cta_kb)

async def want_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    q = update.callback_query
    await q.answer()

    await update.callback_query.message.reply_text(
        "Вы уже ведёте мотивационный блог или только начинаете?",
        reply_markup=ROLE_KB,
    )

async def role_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    user = q.from_user
    upsert_user_basic(user.id, user.username)

    data = (q.data or "").lower()
    role = "new" if "role_new" in data else "old"
    safe_set_role(user.id, role)

    uid = q.from_user.id
    is_new = q.data.endswith("new")

    if is_new:
        user_service.set_role(uid, Role.NEW_PENDING)
    else:
        user_service.set_role(uid, Role.OLD_PENDING)
        await q.message.reply_text("Отлично! Пришлите, пожалуйста, ваш ник Instagram")


async def handle_instagram_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    role = user_service.get_role(uid)
    if role != Role.OLD_PENDING:
        return  

    nickname = update.message.text.strip().lstrip("@")
    if " " in nickname or len(nickname) < 2:
        return

    user_service.set_field(uid, "inst_nick", nickname)
    await _ask_admin_to_check(uid, nickname, context)
    user_service.set_role(uid, Role.OLD_PENDING)


async def _send_payment_link(
    uid: int,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    is_new: bool,
):
    amount = _get_amount(uid, default_key="PRICE_RUB")
    lava_link = _get_lava_link(amount)
    if not lava_link:
        await context.bot.send_message(uid, "⚠️ Платёжная ссылка не настроена.")
        return

    button = KeyboardButton(
        text=f"💳 Оформить за {amount}₽",
        web_app=WebAppInfo(url=lava_link), 
    )
    markup = ReplyKeyboardMarkup(
        [[button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    txt = (
        f"Стоимость подписки: {amount} ₽.\n"
        "Нажмите кнопку, чтобы перейти к оплате:"
    )
    await context.bot.send_message(uid, txt, reply_markup=markup)


async def _ask_admin_to_check(uid: int, nick: str, context):
    await context.bot.send_message(settings.ADMIN_ID,f"👤 Пользователь {uid} на модерации.\n")
    await context.bot.send_message(settings.ADMIN_ID,f"IG: @{nick}")
    await context.bot.send_message(settings.ADMIN_ID,f"/price {uid} <amount>\n")
    await context.bot.send_message(
        uid,
        "Ваш ник отправлен администратору на проверку. "
        "После одобрения вы получите ссылку для оплаты.",
    )

def _get_amount(uid: int, default_key: str) -> int:
    row = user_service.get(uid)
    return int(row[6]) if row and row[6] else int(os.getenv(default_key, 1000))


def _get_lava_link(amount: int) -> str | None:
    return os.getenv(f"LAVA_LINK_{amount}")

"""
def setup(application):
    from telegram.ext import (
        CallbackQueryHandler,
        MessageHandler,
        filters,
    )

    application.add_handler(
        CallbackQueryHandler(role_choice, pattern=r"^role_(new|old)$")
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram_nick),
        group=0,
    )"""