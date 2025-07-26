import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from bot.config import settings
from bot.constants import CallbackData
from bot.db import DBHelper
from bot.handlers import common, onboarding, payments, admin, support

logger = logging.getLogger(__name__)

def setup_handlers(app):
    # User commands
    app.add_handler(CommandHandler("start", common.start_handler))
    
    # Admin commands
    admin_handlers = [
        CommandHandler("price", admin.price_command),
        CommandHandler("stats", admin.stats_command),
        CommandHandler("list", admin.list_users_command),
        CommandHandler("reply", support.admin_reply)
    ]
    for handler in admin_handlers:
        app.add_handler(handler)
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(onboarding.intro_done, pattern=f"^{CallbackData.INTRO_DONE}$"))
    app.add_handler(CallbackQueryHandler(onboarding.role_choice, pattern="^role_"))
    app.add_handler(CallbackQueryHandler(payments.notify_payment, pattern=f"^{CallbackData.NOTIFY_PAYMENT}$"))
    app.add_handler(CallbackQueryHandler(payments.confirm_payment, pattern="^confirm_\\d+$"))

    # Message handlers
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        onboarding.handle_instagram_nick
    ), group=0)

    menu_handlers = [
        MessageHandler(filters.Regex("^ℹ️"), onboarding.about_project),  # Add about_project handler
        MessageHandler(filters.Regex("^👋 Хочу к вам$"), onboarding.want_join),  # Fix pattern and handler
        MessageHandler(
            filters.Regex("^(📞 Поддержка|👥 Реферальная ссылка|📊 Статистика)$"),
            common.menu_handler
        ),
        MessageHandler(filters.TEXT & ~filters.COMMAND, support.support_message)
    ]
    for handler in menu_handlers:
        app.add_handler(handler, group=1)

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    # Initialize bot
    app = ApplicationBuilder().token(settings.TOKEN).build()
    
    # Initialize database
    db = DBHelper(settings.DB_PATH)
    app.bot_data["db"] = db
    
    # Setup handlers
    setup_handlers(app)
    
    # Start polling
    logger.info("Bot started and polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
