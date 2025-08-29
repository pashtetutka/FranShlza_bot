from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from telegram.error import BadRequest


from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.constants import ParseMode

from bot.config import settings
from bot.decorators import admin_only
from bot.db.reels import create_reel, upsert_asset, list_reels, get_reel, delete_reel, set_reel_active

logger = logging.getLogger(__name__)

ADMIN_ONLY = admin_only(settings.ADMIN_ID)

# Состояния мастера
VIDEO, PREVIEW, CAPTION, CONFIRM = range(4)


def _kb_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="reel:cancel")]])


def _kb_confirm(reel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Сохранить", callback_data=f"reel:save:{reel_id}")],
        [InlineKeyboardButton("↩️ Отмена", callback_data="reel:cancel")],
    ])


def _kb_list_item(reel_id: int, active: bool) -> InlineKeyboardMarkup:
    toggle = "🔴 Деактивировать" if active else "🟢 Активировать"
    toggle_code = "deactivate" if active else "activate"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁️ Предпросмотр", callback_data=f"reel:show:{reel_id}")],
        [
            InlineKeyboardButton(toggle,  callback_data=f"reel:{toggle_code}:{reel_id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"reel:delete:{reel_id}"),
        ],
    ])



# ──────────────────────────────────────────────────────────────────────────────
# Мастер добавления
# ──────────────────────────────────────────────────────────────────────────────

@ADMIN_ONLY
async def reel_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    args = context.args or []
    title = " ".join(args).strip() if args else None

    created_by = update.effective_user.id          # ← только ID, не объект Chat!
    reel_id = create_reel(title, created_by=created_by)

    context.user_data["reel"] = {"id": reel_id, "title": title}
    await update.message.reply_text(
        f"🆕 Создан рилс ID <code>{reel_id}</code>\n"
        f"{'Название: ' + title if title else 'Название можно будет задать позже.'}\n\n"
        f"Шаг 1/3 — пришлите <b>видео рилса</b> (как видео).",
        parse_mode=ParseMode.HTML,
        reply_markup=_kb_cancel(),
    )
    return VIDEO



@ADMIN_ONLY
async def reel_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг 1: принимаем видео, сохраняем ID сообщения и file_id."""
    msg = update.message
    if not msg or not msg.video:
        await msg.reply_text("Это не видео. Пришлите <b>видео</b> рилса.", parse_mode=ParseMode.HTML, reply_markup=_kb_cancel())
        return VIDEO

    reel: Dict[str, Any] = context.user_data.get("reel") or {}
    reel_id = reel.get("id")

    upsert_asset(
        reel_id=reel_id,
        kind="video",
        tg_chat_id=msg.chat_id,
        tg_message_id=msg.message_id,
        tg_file_id=msg.video.file_id,
        tg_file_unique_id=msg.video.file_unique_id,
    )

    await msg.reply_text(
        "✅ Видео сохранено.\n\nШаг 2/3 — пришлите <b>превью</b> (обложку) как фото.",
        parse_mode=ParseMode.HTML,
        reply_markup=_kb_cancel(),
    )
    return PREVIEW


@ADMIN_ONLY
async def reel_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг 2: принимаем фото, сохраняем largest file_id + message_id."""
    msg = update.message
    if not msg or not msg.photo:
        await msg.reply_text("Это не фото. Пришлите <b>превью</b> (обложку) как фото.", parse_mode=ParseMode.HTML, reply_markup=_kb_cancel())
        return PREVIEW

    photo = msg.photo[-1]  # самое крупное
    reel: Dict[str, Any] = context.user_data.get("reel") or {}
    reel_id = reel.get("id")

    upsert_asset(
        reel_id=reel_id,
        kind="preview",
        tg_chat_id=msg.chat_id,
        tg_message_id=msg.message_id,
        tg_file_id=photo.file_id,
        tg_file_unique_id=photo.file_unique_id,
    )

    await msg.reply_text(
        "✅ Превью сохранено.\n\nШаг 3/3 — пришлите <b>описание</b> рилса (текст).",
        parse_mode=ParseMode.HTML,
        reply_markup=_kb_cancel(),
    )
    return CAPTION


@ADMIN_ONLY
async def reel_caption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг 3: принимаем текст-описание, сохраняем и просим подтвердить."""
    msg = update.message
    if not msg or not msg.text:
        await msg.reply_text("Пришлите, пожалуйста, <b>текст</b> — описание рилса.", parse_mode=ParseMode.HTML, reply_markup=_kb_cancel())
        return CAPTION

    reel: Dict[str, Any] = context.user_data.get("reel") or {}
    reel_id = reel.get("id")

    upsert_asset(
        reel_id=reel_id,
        kind="caption",
        tg_chat_id=msg.chat_id,
        tg_message_id=msg.message_id,
        text=msg.text.strip(),
    )

    details = get_reel(reel_id)
    title = details["reel"].get("title") or f"Reel #{reel_id}"
    has_video = "video" in details["assets"]
    has_preview = "preview" in details["assets"]
    has_caption = "caption" in details["assets"]

    await msg.reply_text(
        f"🧾 <b>Проверьте данные</b>\n"
        f"ID: <code>{reel_id}</code>\n"
        f"Название: {title}\n"
        f"Видео: {'✅' if has_video else '❌'}\n"
        f"Превью: {'✅' if has_preview else '❌'}\n"
        f"Описание: {'✅' if has_caption else '❌'}\n\n"
        f"Нажмите «Сохранить», чтобы завершить мастер.",
        parse_mode=ParseMode.HTML,
        reply_markup=_kb_confirm(reel_id),
    )
    return CONFIRM


@ADMIN_ONLY
async def reel_confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка кнопок подтверждения/отмены."""
    q = update.callback_query
    data = q.data or ""
    await q.answer()

    if data == "reel:cancel":
        context.user_data.pop("reel", None)
        await q.message.edit_text("❎ Мастер отменён.")
        return ConversationHandler.END

    if data.startswith("reel:save:"):
        reel_id = int(data.split(":")[2])
        context.user_data.pop("reel", None)
        await q.message.edit_text(f"✅ Рилс сохранён (ID <code>{reel_id}</code>).", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    return ConversationHandler.END


@ADMIN_ONLY
async def reel_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда отмены на любом шаге: /reel_cancel"""
    context.user_data.pop("reel", None)
    await update.message.reply_text("❎ Мастер отменён.")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────────
# Список/управление
# ──────────────────────────────────────────────────────────────────────────────

@ADMIN_ONLY
async def reels_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Список рилсов: /reels [limit]"""
    try:
        limit = int(context.args[0]) if context.args else 10
    except ValueError:
        limit = 10

    rows = list_reels(limit=limit)
    if not rows:
        m = await update.message.reply_text("Пока нет рилсов.")
        # сохраним сводку на будущее, чтобы потом корректно обновлять
        context.chat_data["reels_summary"] = {"message_id": m.message_id, "limit": limit}
        return

    # Сводка (запоминаем message_id, чтобы потом обновлять)
    lines = []
    for r in rows:
        rid = r["id"]
        title = r["title"] or f"Reel #{rid}"
        active = bool(r["is_active"])
        assets = r["assets"]
        lines.append(f"• <b>{title}</b> (ID {rid}) — {'🟢 активен' if active else '🔴 выключен'}, ассетов: {assets}")

    summary = await update.message.reply_text(
        "\n".join(lines) + "\n\nДля управления используйте кнопки под отдельными сообщениями.",
        parse_mode=ParseMode.HTML,
    )
    context.chat_data["reels_summary"] = {"message_id": summary.message_id, "limit": limit}

    # Карточки по одной
    for r in rows:
        rid = r["id"]
        title = r["title"] or f"Reel #{rid}"
        active = bool(r["is_active"])
        text = f"ID <code>{rid}</code> — <b>{title}</b>\nСтатус: {'🟢 активен' if active else '🔴 выключен'}"
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=_kb_list_item(rid, active)
        )


@ADMIN_ONLY
async def reels_manage_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    data = q.data or ""
    await q.answer()

    try:
        _, action, rid_str = data.split(":")
        reel_id = int(rid_str)
    except Exception:
        return

    chat_id = q.message.chat_id

    if action == "activate":
        set_reel_active(reel_id, True)
        await _render_reel_card(q.message, reel_id)
        await _refresh_reels_summary(context, chat_id)

    elif action == "deactivate":
        set_reel_active(reel_id, False)
        await _render_reel_card(q.message, reel_id)
        await _refresh_reels_summary(context, chat_id)

    elif action == "delete":
        delete_reel(reel_id)
        # удалим карточку рилса из чата
        try:
            await q.message.delete()
        except BadRequest:
            pass
        await _refresh_reels_summary(context, chat_id)

    elif action == "show":
        await _send_reel_preview(context.bot, chat_id, reel_id)
        # карточку и сводку не меняем



from bot.domain.services.reel_delivery_service import deliver_reels_daily

@ADMIN_ONLY
async def reels_send_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🚀 Запускаю разовую отправку…")
    await deliver_reels_daily(context.application.bot)
    await update.message.reply_text("✅ Готово.")


from telegram.constants import ParseMode

async def _send_reel_preview(bot, chat_id: int, reel_id: int) -> bool:
    data = get_reel(reel_id)
    if not data:
        await bot.send_message(chat_id, f"⚠️ Рилс ID {reel_id} не найден.")
        return False

    assets = data.get("assets", {})
    preview = assets.get("preview")
    video   = assets.get("video")
    caption = assets.get("caption")

    sent_any = False

    if preview and preview.get("tg_file_id"):
        await bot.send_photo(chat_id=chat_id, photo=preview["tg_file_id"], disable_notification=True)
        sent_any = True

    if video and video.get("tg_file_id"):
        await bot.send_video(chat_id=chat_id, video=video["tg_file_id"], disable_notification=True)
        sent_any = True

    if caption and caption.get("text"):
        await bot.send_message(
            chat_id=chat_id,
            text=caption["text"],
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            disable_notification=True,
        )
        sent_any = True

    if not sent_any:
        await bot.send_message(chat_id, f"⚠️ У рилса ID {reel_id} нет сохранённых ассетов.")
    return sent_any


async def _render_reel_card(message, reel_id: int) -> None:
    details = get_reel(reel_id)
    if not details or not details.get("reel"):
        return
    r = details["reel"]
    title = r.get("title") or f"Reel #{reel_id}"
    active = bool(r.get("is_active"))
    text = (
        f"ID <code>{reel_id}</code> — <b>{title}</b>\n"
        f"Статус: {'🟢 активен' if active else '🔴 выключен'}"
    )
    kb = _kb_list_item(reel_id, active)
    try:
        await message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except BadRequest as e:
        pass


async def _refresh_reels_summary(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    meta = context.chat_data.get("reels_summary")  # {'message_id': int, 'limit': int}
    if not meta:
        return
    msg_id = meta.get("message_id")
    limit = meta.get("limit", 10)

    rows = list_reels(limit=limit)
    if not rows:
        text = "Пока нет рилсов."
    else:
        lines = []
        for r in rows:
            rid = r["id"]
            title = r["title"] or f"Reel #{rid}"
            active = bool(r["is_active"])
            assets = r["assets"]
            lines.append(f"• <b>{title}</b> (ID {rid}) — {'🟢 активен' if active else '🔴 выключен'}, ассетов: {assets}")
        text = "\n".join(lines) + "\n\nДля управления используйте кнопки под отдельными сообщениями."

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except BadRequest:
        m = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
        context.chat_data["reels_summary"] = {"message_id": m.message_id, "limit": limit}
