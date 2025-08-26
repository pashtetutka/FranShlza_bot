from os import getenv
from typing import Optional
from datetime import datetime, date
from telegram import (
    Update,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo,
)
from bot.domain.services.onboarding_service import send_instruction_package
from telegram.ext import ContextTypes
from bot.constants import CallbackData
from bot.db.subscriptions import (
    upsert_user_basic, safe_set_role, is_paid,
    start_free_trial, get_trial_info, get_role,
)

TRIAL_MSG_NEW     = getenv("TRIAL_MSG_NEW",  "🎁 Для новых пользователей доступен фритрайл на 2 месяца. Нажми кнопку ниже:")
TRIAL_BTN_TEXT    = getenv("TRIAL_BTN_TEXT", "🎁 Хочу бесплатно")
PAY_MSG_NEW       = getenv("PAY_MSG_NEW",    "💳 Либо сразу оформи подписку и начни получать рилсы без ограничений:")
PAY_TEXT_DEFAULT  = getenv("PAY_BUTTON_TEXT","💳 Оплатить 1000Р")
PAY_MSG_OLD       = getenv("PAY_MSG_OLD",    "💳 Ваша индивидуальная цена готова. Оформите подписку:")

def _trial_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(TRIAL_BTN_TEXT, callback_data=CallbackData.TRIAL_START.value)]]
    )

def _build_frontend_url(frontend_url: str, role: str, amount: Optional[int]) -> str:
    base = frontend_url.rstrip("/")
    qs = f"?role={role}"
    if amount is not None:
        qs += f"&amount={amount}"
    return f"{base}{qs}"

def _pay_inline_kb(caption: str, role: str, amount: Optional[int], frontend_url: Optional[str]) -> InlineKeyboardMarkup:

    if frontend_url:
        url = _build_frontend_url(frontend_url, role, amount)
        btn = InlineKeyboardButton(caption, web_app=WebAppInfo(url=url))
    else:
        btn = InlineKeyboardButton(caption, callback_data=CallbackData.PAY_NOW.value)
    return InlineKeyboardMarkup([[btn]])

async def offer_after_new_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    chat_id = user.id

    upsert_user_basic(user.id, user.username)
    safe_set_role(user.id, "new")

    if is_paid(user.id):
        return

    await context.bot.send_message(chat_id=chat_id, text=TRIAL_MSG_NEW, reply_markup=_trial_kb())

    fe = context.application.bot_data.get("FRONTEND_URL")
    await context.bot.send_message(
        chat_id=chat_id,
        text=PAY_MSG_NEW,
        reply_markup=_pay_inline_kb(PAY_TEXT_DEFAULT, role="new", amount=None, frontend_url=fe),
    )

async def notify_old_price_ready(bot, user_id: int, amount_rub: int, frontend_url: Optional[str] = None):

    await bot.send_message(
        chat_id=user_id,
        text="🎁 Доступен фритрайл на 2 месяца. Нажмите кнопку ниже:",
        reply_markup=_trial_kb(),
    )

    if not frontend_url:
        app = getattr(bot, "application", None)
        if app:
            frontend_url = app.bot_data.get("FRONTEND_URL")
    if not frontend_url:
        frontend_url = getenv("FRONTEND_URL")

    caption = f"Оплатить {amount_rub}Р"
    kb = _pay_inline_kb(caption, role="old", amount=amount_rub, frontend_url=frontend_url)
    await bot.send_message(
        chat_id=user_id,
        text=PAY_MSG_OLD,
        reply_markup=kb,
    )

from datetime import datetime

async def start_free_trial_cb(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    q = update.callback_query
    await q.answer()
    user = q.from_user
    upsert_user_basic(user.id, user.username)

    if is_paid(user.id):
        await q.message.reply_text("У тебя уже активная оплаченная подписка — фритрайл не нужен ✅")
        return

    try:
        result = start_free_trial(user.id, months=2)
    except TypeError:
        result = start_free_trial(user.id)

    if result == "STARTED":
        await q.message.reply_text(
            "Фритрайл активирован на 2 месяца 🎉\n"
            "Каждый день пришлю 1 рилс + описание. Можно перейти на платный план в любой момент."
        )
        info = get_trial_info(user.id)
        if info and info.get("trial_expires_at"):
            dt = datetime.fromisoformat(info["trial_expires_at"].replace("Z", "+00:00"))
            await q.message.reply_text(f"Дата окончания: {dt.strftime('%d.%m.%Y')}")
            await send_instruction_package(context.bot, user.id)

    elif result == "PAID_ALREADY":
        await q.message.reply_text("У тебя уже активная оплаченная подписка ✅")
    elif result == "ACTIVE_ALREADY":
        info = get_trial_info(user.id)
        extra = ""
        if info and info.get("trial_expires_at"):
            dt = datetime.fromisoformat(info["trial_expires_at"].replace("Z", "+00:00"))
            extra = f"\nАктивен до: {dt.strftime('%d.%m.%Y')}"
        await q.message.reply_text("Фритрайл уже активен ✅" + extra)
    elif result == "ALREADY_USED":
        await q.message.reply_text("Фритрайл уже был использован ранее. Продолжить можно по платной подписке.")


async def pay_now_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text("Для оплаты отправь команду /buy (или /pay).")

async def maybe_offer_on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_paid(user.id):
        return
    role = get_role(user.id)
    if role not in ("new", "old"):
        return
    fe = context.application.bot_data.get("FRONTEND_URL")
    caption = PAY_TEXT_DEFAULT if role == "new" else "Оплатить 1000Р"
    await update.message.reply_text(
        "Выберите вариант:",
        reply_markup=_pay_inline_kb(caption, role=role, amount=None, frontend_url=fe),
    )
