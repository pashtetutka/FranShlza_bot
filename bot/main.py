from pathlib import Path
from dotenv import load_dotenv, find_dotenv
load_dotenv( find_dotenv())

import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.config import settings
from bot.constants import CallbackData
from bot.api.handlers import common, onboarding, payments, admin, support
from bot.domain.services import user_service, payment_service, referral_service

logger = logging.getLogger(__name__)

def setup_handlers(app):
    app.add_handler(CommandHandler("start", common.start_handler))

    admin_handlers = [
        CommandHandler("price", admin.price_command),
        CommandHandler("stats", admin.stats_command),
        CommandHandler("list", admin.list_users_command),
        CommandHandler("reply", support.admin_reply)
    ]
    for h in admin_handlers:
        app.add_handler(h)

    app.add_handler(CallbackQueryHandler(onboarding.intro_done, pattern=f"^{CallbackData.INTRO_DONE}$"))
 
    app.add_handler(CallbackQueryHandler(onboarding.role_choice, pattern=r"^role_(new|old)$",))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding.handle_instagram_nick), group=0)

    app.add_handler(CommandHandler(["buy", "pay"], payments.buy))

    menu_handlers = [
            MessageHandler(filters.Regex("^ℹ️"), onboarding.about_project),
            MessageHandler(filters.Regex("^👋 Хочу к вам$"), onboarding.want_join),
            MessageHandler(filters.Regex("^(📞 Поддержка|👥 Реферальная ссылка|📊 Статистика)$"),
                        common.menu_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, support.support_message)
        ]
    for h in menu_handlers:
            app.add_handler(h, group=1)

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    application = ApplicationBuilder().token(settings.TOKEN).build()

    application.bot_data.update(
        user_service=user_service,
        payment_service=payment_service,
        referral_service=referral_service,
    )

    from os import getenv
    if getenv("FRONTEND_URL"):
        application.bot_data["FRONTEND_URL"] = getenv("FRONTEND_URL")

    setup_handlers(application)

    logger.info("Bot started and polling…")
    application.run_polling()


if __name__ == "__main__":
    main()
