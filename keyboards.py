from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

INTRO_KB = InlineKeyboardMarkup(
    [[InlineKeyboardButton("Ознакомился ✅", callback_data="intro_done")]]
)

CHOICE_KB = ReplyKeyboardMarkup(
    [["👋 Хочу к вам", "ℹ️ Подробнее"]], 
    resize_keyboard=True
)

ROLE_KB = InlineKeyboardMarkup([[
    InlineKeyboardButton("Новичок", callback_data="role_new"),
    InlineKeyboardButton("Старичок", callback_data="role_old"),
]])

PAY_NOTIFY = InlineKeyboardMarkup(
    [[InlineKeyboardButton("Я оплатил", callback_data="notify_payment")]]
)

MENU_KB = ReplyKeyboardMarkup([[
    "📞 Поддержка", 
    "👥 Реферальная ссылка", 
    "📊 Статистика"
]], resize_keyboard=True)
