import logging, asyncio
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from bot.api.handlers.trial import notify_old_price_ready
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from bot.decorators import admin_only
from bot.config import settings
from bot.utils import fmt_table, send_long
from bot.domain.services import user_service, payment_service, referral_service
import os 

logger = logging.getLogger(__name__)

@admin_only(settings.ADMIN_ID)
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    total, paid, money = payment_service.global_stats()
    leaders = referral_service.top(5)
    ref_lines = [f"{i+1}. <code>{uid}</code> — {cnt}" for i, (uid, cnt) in enumerate(leaders)] or ["-"]
    percent = f"{paid/total*100:.1f}%" if total else "0%"

    text = (
        "📊 <b>Общая статистика</b>\n"
        f"• Пользователей всего: <b>{total}</b>\n"
        f"• Оплатили: <b>{paid}</b> ({percent})\n"
        f"• Сумма платежей: <b>{money} ₽</b>\n"
        f"• <u>ТОП-5 рефералов</u> (по числу приглашённых):\n" + "\n".join(ref_lines)
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

@admin_only(settings.ADMIN_ID)
async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    limit = int(context.args[0]) if context.args else 20
    rows = user_service.list(limit)
    refs = user_service.referral_counts()

    chats = await asyncio.gather(*(context.bot.get_chat(r[0]) for r in rows))
    users = {c.id: c for c in chats}

    data = [(
        tg_id,
        users[tg_id].username or "-",
        inst or "-",
        role,
        paid,
        price or "-",
        str(parent) if parent else "-",
        refs.get(tg_id, 0),
        joined.replace("T", " ")[:19]
    ) for tg_id, role, paid, price, parent, inst, joined in rows]

    headers = ["TG_ID", "USER", "INST", "ROLE", "PAID", "PRICE", "PARENT", "REFS", "JOINED"]
    await send_long(context.bot, settings.ADMIN_ID, fmt_table(data, headers))

@admin_only(settings.ADMIN_ID)
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid, amount = int(context.args[0]), int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /price <uid> <amount>")
        return

    user_service.set_field(uid, "price_offer", amount)

    lava_link = os.getenv(f"LAVA_LINK_{amount}")
    if not lava_link:
        await update.message.reply_text(f"⚠️ LAVA_LINK_{amount} не найден в .env")
        return

    btn = KeyboardButton(
        text=f"💳 Оплатить {amount}₽",
        web_app=WebAppInfo(url=lava_link),
    )
    markup = ReplyKeyboardMarkup([[btn]], resize_keyboard=True, one_time_keyboard=True)
    await context.bot.send_message(
        uid,
        f"Стоимость подписки: {amount} ₽. Нажмите кнопку для оплаты:",
        reply_markup=markup,
    )
    await update.message.reply_text("Ссылка отправлена пользователю ✅")
    await notify_old_price_ready(context.bot, uid, amount)
