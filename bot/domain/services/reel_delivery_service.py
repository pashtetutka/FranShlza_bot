from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from bot.db.connection import get_conn
from bot.db.reels import (
    pick_next_reel_id_for_user,
    get_reel,
    mark_reel_delivered,
    ensure_reels_schema,
    reset_user_reel_progress,
    any_active_reels,
)

logger = logging.getLogger(__name__)


def get_eligible_users() -> List[int]:
    ensure_reels_schema()
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT u.tg_user_id
            FROM users u
            LEFT JOIN subscriptions s ON s.tg_user_id = u.tg_user_id
            LEFT JOIN free_trials  t ON t.tg_user_id = u.tg_user_id
            WHERE
              (
                UPPER(COALESCE(s.status,'NONE')) = 'ACTIVE'
                AND (s.paid_until IS NULL OR s.paid_until >= datetime('now'))
              )
              OR
              (
                UPPER(COALESCE(t.status,'')) = 'ACTIVE'
                AND (t.trial_expires_at IS NOT NULL AND t.trial_expires_at >= datetime('now'))
              )
            """
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


async def deliver_reel_to_user(bot: Bot, tg_user_id: int) -> bool:

    # 1) Пытаемся взять следующий «неполученный» активный рилс
    reel_id = pick_next_reel_id_for_user(tg_user_id)

    # 2) Если нечего слать — сбрасываем прогресс по активным и пробуем ещё раз
    if not reel_id:
        deleted = reset_user_reel_progress(tg_user_id)
        logger.info("reels: reset progress for user=%s, deleted=%s", tg_user_id, deleted)
        reel_id = pick_next_reel_id_for_user(tg_user_id)
        if not reel_id:
            if not any_active_reels():
                logger.info("reels: no active reels at all; user=%s", tg_user_id)
            return False

    data = get_reel(reel_id)
    if not data:
        logger.warning("reel %s not found while delivering to %s", reel_id, tg_user_id)
        return False

    assets = data["assets"]
    video = assets.get("video")
    preview = assets.get("preview")
    caption = assets.get("caption")

    if not video or not video.get("tg_file_id"):
        logger.warning("reel %s has no video asset; skip", reel_id)
        return False

    preview_msg_id = None
    video_msg_id = None
    caption_msg_id = None

    try:
        # 0) Превью (если есть)
        if preview and preview.get("tg_file_id"):
            sent_preview = await bot.send_photo(
                chat_id=tg_user_id,
                photo=preview["tg_file_id"],
                disable_notification=True,
            )
            preview_msg_id = sent_preview.message_id

        # 1) Видео
        sent_video = await bot.send_video(
            chat_id=tg_user_id,
            video=video["tg_file_id"],
            disable_notification=True,
        )
        video_msg_id = sent_video.message_id

        # 2) Описание (если есть)
        if caption and caption.get("text"):
            sent_text = await bot.send_message(
                chat_id=tg_user_id,
                text=caption["text"],
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                disable_notification=True,
            )
            caption_msg_id = sent_text.message_id

        # Зафиксируем доставку
        mark_reel_delivered(tg_user_id, reel_id, video_msg_id, caption_msg_id)
        return True

    except TelegramError as e:
        logger.error("deliver reel to %s failed: %s", tg_user_id, e)
        return False



async def deliver_reels_daily(bot: Bot) -> None:
    users = get_eligible_users()
    if not users:
        logger.info("reels daily: eligible users = 0")
        return

    sent = 0
    for uid in users:
        try:
            ok = await deliver_reel_to_user(bot, uid)
            if ok:
                sent += 1
        except Exception as e:
            logger.exception("reels daily: user %s: %s", uid, e)
        await asyncio.sleep(0.05)  # лёгкая рассинхронизация

    logger.info("reels daily: processed users=%s, sent=%s", len(users), sent)
