from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from .constants import CallbackData

INTRO_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("Ознакомился ✅", callback_data=CallbackData.INTRO_DONE)]
])

CHOICE_KB = ReplyKeyboardMarkup(
    [["👋 Хочу к вам", "ℹ️ Подробнее"]], 
    resize_keyboard=True
)

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
