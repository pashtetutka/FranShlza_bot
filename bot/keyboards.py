from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from .constants import CallbackData

INTRO_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("Ознакомился ✅", callback_data=CallbackData.INTRO_DONE)]
])

CHOICE_KB = InlineKeyboardMarkup([[
    InlineKeyboardButton("👋 Хочу к вам", callback_data=CallbackData.WANT_JOIN),
    InlineKeyboardButton("ℹ️ Подробнее", callback_data=CallbackData.ABOUT),
]])

ROLE_KB = InlineKeyboardMarkup([[
    InlineKeyboardButton("Новичок", callback_data=CallbackData.ROLE_NEW),
    InlineKeyboardButton("Старичок", callback_data=CallbackData.ROLE_OLD),
]])

PAY_NOTIFY = InlineKeyboardMarkup([
    [InlineKeyboardButton("Я оплатил", callback_data=CallbackData.NOTIFY_PAYMENT)]
])

def get_payment_confirm_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "Да, он оплатил",
            callback_data=CallbackData.CONFIRM_PAYMENT.format(user_id=uid)
        )
    ]])

MENU_KB = ReplyKeyboardMarkup([[
    "📞 Поддержка",
    "👥 Реферальная ссылка",
    "📊 Статистика"
]], resize_keyboard=True)
