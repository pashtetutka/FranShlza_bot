# bot/main.py
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import logging
import os
import re
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
from bot.api.handlers import trial
from bot.domain.services import user_service, payment_service, referral_service

logger = logging.getLogger(__name__)

def _cbv(x) -> str:
    return getattr(x, "value", x)

def _exact(cb) -> str:
    return rf"^{re.escape(_cbv(cb))}$"

def setup_handlers(app):
    # Команды
    app.add_handler(CommandHandler("start", common.start_handler))
    app.add_handler(CommandHandler(["buy", "pay"], payments.buy))

    # Админ
    for h in [
        CommandHandler("price", admin.price_command),
        CommandHandler("stats", admin.stats_command),
        CommandHandler("list", admin.list_users_command),
        CommandHandler("reply", support.admin_reply),
    ]:
        app.add_handler(h)

    # === CALLBACK — ГРУППА 0 ===
    app.add_handler(CallbackQueryHandler(onboarding.intro_done, pattern=_exact(CallbackData.INTRO_DONE), block=True), group=0)

    # Новичок: сначала шлём (inline trial + inline WebApp оплата), затем твоя логика роли
    app.add_handler(CallbackQueryHandler(trial.offer_after_new_role, pattern=r"(?i)^role_new(?:.*)$", block=False), group=0)
    app.add_handler(CallbackQueryHandler(onboarding.role_choice, pattern=r"(?i)^role_(?:new|old)(?:.*)$", block=False), group=0)

    # Нажатие inline фритрайла
    app.add_handler(CallbackQueryHandler(trial.start_free_trial_cb, pattern=_exact(CallbackData.TRIAL_START), block=True), group=0)

    # Fallback оплаты (если нет FRONTEND_URL)
    app.add_handler(CallbackQueryHandler(trial.pay_now_fallback, pattern=_exact(CallbackData.PAY_NOW), block=True), group=0)

    # === ТЕКСТ — ГРУППА 1 ===
    # Ник Instagram — первым
    insta_regex = r"^(?:@)?[A-Za-z0-9._]{2,30}$"
    app.add_handler(MessageHandler(filters.Regex(insta_regex), onboarding.handle_instagram_nick, block=True), group=1)

    # Меню
    app.add_handler(MessageHandler(filters.Regex(r"^(?:👋\s*)?Хочу к вам$"), onboarding.want_join, block=True), group=1)
    app.add_handler(MessageHandler(filters.Regex(r"^(?:ℹ️\s*)?(?:Подробнее|О проекте|Информация)$"), onboarding.about_project, block=True), group=1)
    app.add_handler(MessageHandler(filters.Regex("^(📞 Поддержка|👥 Реферальная ссылка|📊 Статистика)$"), common.menu_handler, block=True), group=1)

    # Фоллбэк — любые остальные тексты
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, support.support_message, block=True), group=3)

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    application = ApplicationBuilder().token(settings.TOKEN).build()

    # сервисы + FRONTEND_URL для web_app
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
