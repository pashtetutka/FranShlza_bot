# bot/api/handlers/pricing.py
from typing import Literal
from os import getenv
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from telegram.ext import ContextTypes, CallbackContext

from bot.db.subscriptions import upsert_user_basic, safe_set_role, is_paid
from bot.api.handlers.trial import TRIAL_TEXT
from bot.constants import CallbackData

def _price_for_role(role: Literal["new","old"]) -> str:
    txt_new = getenv("PRICING_NEW", "Стоимость подписки: 1000Р.\nНажмите кнопку, чтобы перейти к оплате:")
    txt_old = getenv("PRICING_OLD", "Стоимость подписки: Индивидуально.\nНажмите кнопку, чтобы перейти к оплате:")
    return txt_new if role == "new" else txt_old

def _inline_pay_kb(role: Literal["new","old"], frontend_url: str | None) -> InlineKeyboardMarkup:
    caption = getenv("PAY_INLINE_TEXT", "💳 Оплатить 1000Р")
    if frontend_url:
        return InlineKeyboardMarkup([[InlineKeyboardButton(caption, url=f"{frontend_url}?role={role}")]])
    return InlineKeyboardMarkup([[InlineKeyboardButton(caption, callback_data=CallbackData.PAY_NOW.value)]])

def _trial_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(TRIAL_TEXT)]], resize_keyboard=True, one_time_keyboard=False)

async def _send_inline_pay(update_or_ctx, context: ContextTypes.DEFAULT_TYPE, text: str, role: Literal["new","old"]):
    frontend_url = context.application.bot_data.get("FRONTEND_URL")
    kb = _inline_pay_kb(role, frontend_url)
    if hasattr(update_or_ctx, "callback_query") and update_or_ctx.callback_query:
        await update_or_ctx.callback_query.message.reply_text(text, reply_markup=kb)
    else:
        chat_id = update_or_ctx.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)

async def _trial_job(context: CallbackContext):
    """Джоб, который отправляет второе сообщение уже вне контекста коллбэка."""
    data = context.job.data or {}
    chat_id = data.get("chat_id")
    hint = getenv("TRIAL_HINT_TEXT", "Или начни бесплатно на 2 месяца — кнопка ниже 👇")
    if chat_id:
        await context.bot.send_message(chat_id=chat_id, text=hint, reply_markup=_trial_reply_kb())

# === 1) Коллбэк: выбор роли (inline) ===
async def show_after_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    upsert_user_basic(user.id, user.username)

    data = (q.data or "").lower()
    role: Literal["new","old"] = "new" if data.startswith("role_new") else "old"
    safe_set_role(user.id, role)

    # 1) Сообщение с inline-оплатой
    await _send_inline_pay(update, context, _price_for_role(role), role)

    # 2) Через 200 мс — отдельное сообщение с ReplyKeyboard фритрайла (если не платный)
    if not is_paid(user.id):
        context.job_queue.run_once(_trial_job, when=0.2, data={"chat_id": user.id})

# === 2) Роль пришла текстом (ReplyKeyboard) — делаем то же самое ===
async def show_after_role_text(update: Update, context: ContextTypes.DEFAULT_TYPE, role: Literal["new","old"]):
    user = update.effective_user
    upsert_user_basic(user.id, user.username)
    safe_set_role(user.id, role)

    await _send_inline_pay(update, context, _price_for_role(role), role)
    if not is_paid(user.id):
        context.job_queue.run_once(_trial_job, when=0.2, data={"chat_id": user.id})

# === 3) Fallback для inline-оплаты, если нет FRONTEND_URL ===
async def pay_now_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text("Для оплаты отправь команду /buy (или /pay).")
