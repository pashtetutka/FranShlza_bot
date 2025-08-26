from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from bot.db.connection import get_conn


from bot.config import settings
from bot.decorators import admin_only
from bot.domain.services.admin_service import (
    load_user_card,
    render_user_card,
    exec_action,
)

ADMIN_ONLY = admin_only(settings.ADMIN_ID)


def _confirm_keyboard(uid: int, action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Да, удалить", callback_data=f"adm:{uid}:{action}")],
            [InlineKeyboardButton("Отмена", callback_data=f"adm:{uid}:menu")],
        ]
    )


async def _safe_edit(q, text: str, kb: InlineKeyboardMarkup | None) -> None:
    try:
        await q.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except BadRequest as e:
        if "Message is not modified" in str(e):
            try:
                await q.answer("Актуально ✅", show_alert=False)
            except Exception:
                pass
        else:
            raise


@ADMIN_ONLY
async def whois(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Формат: /whois @username")
        return

    username = context.args[0].lstrip("@")
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT tg_user_id FROM users WHERE LOWER(username)=LOWER(?) LIMIT 1",
            (username,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        await update.message.reply_text("Не найдено.")
        return

    await update.message.reply_text(
        f"ID @{username}: <code>{row['tg_user_id']}</code>", parse_mode="HTML"
    )


@ADMIN_ONLY
async def admin_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Формат: /admin <tg_user_id>")
        return

    uid = int(context.args[0])
    card = load_user_card(uid)
    if not card:
        await update.message.reply_text("Пользователь не найден в БД.")
        return

    text, kb = render_user_card(card)
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")


@ADMIN_ONLY
async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    data = q.data or ""
    await q.answer()

    if not data.startswith("adm:"):
        return

    try:
        _, uid_s, *rest = data.split(":")
        uid = int(uid_s)
    except Exception:
        return

    if not rest:
        return

    if rest[0] == "delete" and rest[1] == "ask":
        await _safe_edit(
            q,
            f"Удалить пользователя <code>{uid}</code> со всеми данными?\n"
            f"Это действие нельзя отменить.",
            _confirm_keyboard(uid, "delete:confirm"),
        )
        return

    if rest[0] == "menu":
        card = load_user_card(uid)
        if not card:
            await _safe_edit(q, "Пользователь не найден.", None)
            return
        text, kb = render_user_card(card)
        await _safe_edit(q, text, kb)
        return

    action = ":".join(rest)
    result_text = await exec_action(context.bot, action, uid)

    card = load_user_card(uid)
    if not card:
        await _safe_edit(q, result_text, None)
        return

    text, kb = render_user_card(card)
    await _safe_edit(q, text + f"\n\n<b>Готово:</b> {result_text}", kb)
