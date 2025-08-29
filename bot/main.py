from pathlib import Path
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


import pytz
from datetime import time as dtime
from bot.domain.services.reel_delivery_service import deliver_reels_daily
from bot.api.handlers.reels_admin import reels_send_now
from bot.api.handlers.util_tools import chatid, whoami


import logging
import os
import re
from bot.db.subscriptions import init_db
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler, 
    filters,
)

from bot.api.handlers.reels_admin import (
    reel_new, reel_video, reel_preview, reel_caption, reel_confirm_cb, reel_cancel_command,
    reels_list, reels_manage_cb,
    VIDEO, PREVIEW, CAPTION, CONFIRM,   # ← импортируй константы состояний
)
from bot.config import settings
from bot.constants import CallbackData
from telegram.ext import ContextTypes
from bot.api.handlers import admin_panel, common, onboarding, payments, admin, support
from bot.api.handlers.admin_panel import whois, admin_open, admin_callbacks

from bot.api.handlers import trial
from bot.domain.services import user_service, payment_service, referral_service

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Amsterdam")
HOUR = int(os.getenv("REELS_SEND_HOUR", "10"))


async def _reels_daily_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await deliver_reels_daily(context.application.bot)

def _cbv(x) -> str:
    return getattr(x, "value", x)

def _exact(cb) -> str:
    return rf"^{re.escape(_cbv(cb))}$"

def setup_handlers(app):
        
    app.add_handler(CommandHandler("start", common.start_handler))

    for h in [
        CommandHandler("price", admin.price_command),
        CommandHandler("stats", admin.stats_command),
        CommandHandler("list", admin.list_users_command),
        CommandHandler("reply", support.admin_reply),
        CommandHandler("whois", whois),
        CommandHandler("admin", admin_open),
     ]:
        app.add_handler(h)


    app.add_handler(CommandHandler("reels_send_now", reels_send_now))

    app.add_handler(CallbackQueryHandler(admin_callbacks, pattern=r"^adm:"))
    app.add_handler(CallbackQueryHandler(onboarding.intro_done, pattern=_exact(CallbackData.INTRO_DONE), block=True), group=0)
    app.add_handler(CallbackQueryHandler(onboarding.want_join, pattern=_exact(CallbackData.WANT_JOIN), block=True), group=0)
    app.add_handler(CallbackQueryHandler(onboarding.about_project, pattern=_exact(CallbackData.ABOUT), block=True), group=0)

    app.add_handler(CallbackQueryHandler(trial.offer_after_new_role, pattern=r"(?i)^role_new(?:.*)$", block=False), group=0)
    app.add_handler(CallbackQueryHandler(onboarding.role_choice, pattern=r"(?i)^role_(?:new|old)(?:.*)$", block=False), group=0)

    app.add_handler(CallbackQueryHandler(trial.start_free_trial_cb, pattern=_exact(CallbackData.TRIAL_START), block=True), group=0)

    app.add_handler(CallbackQueryHandler(trial.pay_now_fallback, pattern=_exact(CallbackData.PAY_NOW), block=True), group=0)

    insta_regex = r"^(?:@)?[A-Za-z0-9._]{2,30}$"
    app.add_handler(MessageHandler(filters.Regex(insta_regex), onboarding.handle_instagram_nick, block=True), group=1)

    app.add_handler(MessageHandler(filters.Regex("^(📞 Поддержка|👥 Реферальная ссылка|📊 Статистика)$"), common.menu_handler, block=True), group=1)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, support.support_message, block=True), group=1)

    app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("reel_new", reel_new)],
    states={
        VIDEO:   [MessageHandler(filters.VIDEO, reel_video),   CallbackQueryHandler(reel_confirm_cb, pattern=r"^reel:(?:cancel|save:)")],
        PREVIEW: [MessageHandler(filters.PHOTO, reel_preview), CallbackQueryHandler(reel_confirm_cb, pattern=r"^reel:(?:cancel|save:)")],
        CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, reel_caption), CallbackQueryHandler(reel_confirm_cb, pattern=r"^reel:(?:cancel|save:)")],
        CONFIRM: [CallbackQueryHandler(reel_confirm_cb, pattern=r"^reel:(?:cancel|save:)")],
    },
    fallbacks=[CommandHandler("reel_cancel", reel_cancel_command)],
    allow_reentry=True,
    #per_message=True,   
    ))


    #app.add_handler(CommandHandler("chatid", chatid))
    #app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("reels", reels_list))
    app.add_handler(CallbackQueryHandler(reels_manage_cb, pattern=r"^reel:(?:activate|deactivate|delete|show):"))

    app.job_queue.run_daily(
    callback=_reels_daily_job,
    time=dtime(hour=HOUR, minute=0, tzinfo=TZ),
    name="reels_daily",
)

def main() -> None:
    init_db()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    application = ApplicationBuilder().token(settings.TOKEN).build()

    application.bot_data.update(
        user_service=user_service,
        payment_service=payment_service,
        referral_service=referral_service,
    )
    fe = os.getenv("FRONTEND_URL")
    if fe:
        application.bot_data["FRONTEND_URL"] = fe

    setup_handlers(application)

    logger.info("Bot started and polling…")
    application.run_polling()

if __name__ == "__main__":
    main()
