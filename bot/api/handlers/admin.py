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


def _fmt_money_rub(amount: int | float) -> str:
    try:
        return f"{int(amount):,}".replace(",", " ")
    except Exception:
        return str(amount)


def _allowed_amounts_from_env() -> list[int]:
    amounts: list[int] = []
    for key, val in os.environ.items():
        if key.startswith("LAVA_LINK_") and val:
            tail = key.removeprefix("LAVA_LINK_")
            if tail.isdigit():
                amounts.append(int(tail))
    return sorted(set(amounts))


@admin_only(settings.ADMIN_ID)
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    total, paid, money = payment_service.global_stats()
    leaders = referral_service.top(5)

    ref_lines = [f"{i+1}. <code>{uid}</code> — {cnt}" for i, (uid, cnt) in enumerate(leaders)] or ["-"]
    percent = f"{(paid / total * 100):.1f}%" if total else "0%"

    text = (
        "📊 <b>Общая статистика</b>\n"
        f"• Пользователей всего: <b>{total}</b>\n"
        f"• Оплатили: <b>{paid}</b> ({percent})\n"
        f"• Сумма платежей: <b>{_fmt_money_rub(money)} ₽</b>\n"
        f"• <u>ТОП-5 рефералов</u> (по числу приглашённых):\n" + "\n".join(ref_lines)
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@admin_only(settings.ADMIN_ID)
async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    limit = int(context.args[0]) if context.args else 20
    rows = user_service.list(limit)  
    refs = user_service.referral_counts()

    chats_or_exc = await asyncio.gather(
        *(context.bot.get_chat(r[0]) for r in rows),
        return_exceptions=True,
    )
    users = {}
    for item in chats_or_exc:
        if hasattr(item, "id"):  
            users[item.id] = item
        else:
            logger.debug("get_chat failed for one of users in /list: %r", item)

    data = []
    for tg_id, role, paid, price, parent, inst, joined in rows:
        username = "-"
        c = users.get(tg_id)
        if c and getattr(c, "username", None):
            username = c.username

        data.append((
            tg_id,
            username,
            inst or "-",
            role,
            paid,
            price or "-",
            str(parent) if parent else "-",
            refs.get(tg_id, 0),
            (joined.replace("T", " ")[:19] if isinstance(joined, str) else str(joined)),
        ))

    headers = ["TG_ID", "USER", "INST", "ROLE", "PAID", "PRICE", "PARENT", "REFS", "JOINED"]
    await send_long(context.bot, settings.ADMIN_ID, fmt_table(data, headers))


@admin_only(settings.ADMIN_ID)
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid, amount = int(context.args[0]), int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /price <uid> <amount>")
        return

    if amount <= 0:
        await update.message.reply_text("Сумма должна быть положительным целым числом.")
        return

    allowed = _allowed_amounts_from_env()
    if allowed and amount not in allowed:
        await update.message.reply_text(
            "⚠️ Для этой суммы нет ссылки в .env.\n"
            "Доступные опции: " + ", ".join(f"{x}₽" for x in allowed)
        )
        return

    user_service.set_field(uid, "price_offer", amount)

    lava_link = os.getenv(f"LAVA_LINK_{amount}")
    if not lava_link:
        # Если .env не содержит ссылку — не молчим, подсказываем варианты
        hint = ""
        if allowed:
            hint = "\nДоступные опции: " + ", ".join(f"{x}₽" for x in allowed)
        await update.message.reply_text(f"⚠️ LAVA_LINK_{amount} не найден в .env{hint}")
        return

    """btn = KeyboardButton(
        text=f"💳 Оплатить {amount}₽",
        web_app=WebAppInfo(url=lava_link),
    )
    markup = ReplyKeyboardMarkup([[btn]], resize_keyboard=True, one_time_keyboard=True)"""
    """await context.bot.send_message(
        uid,
        f"Стоимость подписки: {amount} ₽. Нажмите кнопку для оплаты:",
        reply_markup=markup,
    )"""

    # Сообщаем админу и уведомляем пользователя
    await update.message.reply_text(f"Ссылка на {amount} ₽ отправлена пользователю ✅")
    await notify_old_price_ready(context.bot, uid, amount)


"""await update.effective_message.reply_text(
    "Клавиатура скрыта ✅",
    reply_markup=ReplyKeyboardRemove(),
    )"""
