import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from bot.decorators import admin_only
from bot.config import settings
from bot.utils import fmt_table, send_long

logger = logging.getLogger(__name__)

@admin_only(settings.ADMIN_ID)
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.bot_data["db"]
    total, paid, money = db.global_stats()
    refcnt = db.referral_counts()
    
    leaders = sorted(refcnt.items(), key=lambda x: x[1], reverse=True)[:5]
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
    db = context.bot_data["db"]
    limit = int(context.args[0]) if context.args else 20
    rows = db.fetch_users(limit)
    refs = db.referral_counts()

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
