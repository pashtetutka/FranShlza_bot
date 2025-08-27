# bot/db/reels.py
from __future__ import annotations

import sqlite3
from typing import Optional, Dict, Any, List, Tuple
from bot.db.connection import get_conn


def ensure_reels_schema() -> None:
    """Создаёт таблицы для рилсов (если их ещё нет)."""
    conn = get_conn()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reels (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT,
                    is_active   INTEGER NOT NULL DEFAULT 1,
                    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                    created_by  INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reel_assets (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    reel_id           INTEGER NOT NULL,
                    kind              TEXT NOT NULL CHECK (kind IN ('video','preview','caption')),
                    tg_chat_id        INTEGER,
                    tg_message_id     INTEGER,
                    tg_file_id        TEXT,
                    tg_file_unique_id TEXT,
                    text              TEXT,
                    added_at          TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (reel_id) REFERENCES reels(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_reel_assets ON reel_assets(reel_id, kind)")
            # История доставок (кому какой рилс уже отправили)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reel_deliveries (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_user_id        INTEGER NOT NULL,
                    reel_id           INTEGER NOT NULL,
                    sent_at           TEXT NOT NULL DEFAULT (datetime('now')),
                    video_message_id  INTEGER,
                    caption_message_id INTEGER,
                    UNIQUE(tg_user_id, reel_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS ix_reel_deliveries_user ON reel_deliveries(tg_user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_reel_deliveries_reel ON reel_deliveries(reel_id)")
    finally:
        conn.close()


def create_reel(title: Optional[str], created_by: int) -> int:
    ensure_reels_schema()
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO reels(title, created_by) VALUES(?, ?)",
                (title, created_by),
            )
            return int(cur.lastrowid)
    finally:
        conn.close()


def upsert_asset(
    reel_id: int,
    kind: str,
    tg_chat_id: Optional[int] = None,
    tg_message_id: Optional[int] = None,
    tg_file_id: Optional[str] = None,
    tg_file_unique_id: Optional[str] = None,
    text: Optional[str] = None,
) -> None:
    ensure_reels_schema()
    conn = get_conn()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO reel_assets (reel_id, kind, tg_chat_id, tg_message_id, tg_file_id, tg_file_unique_id, text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(reel_id, kind) DO UPDATE SET
                    tg_chat_id        = excluded.tg_chat_id,
                    tg_message_id     = excluded.tg_message_id,
                    tg_file_id        = excluded.tg_file_id,
                    tg_file_unique_id = excluded.tg_file_unique_id,
                    text              = excluded.text,
                    added_at          = datetime('now')
                """,
                (reel_id, kind, tg_chat_id, tg_message_id, tg_file_id, tg_file_unique_id, text),
            )
    finally:
        conn.close()


def list_reels(limit: int = 20, offset: int = 0) -> List[sqlite3.Row]:
    ensure_reels_schema()
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT r.id, r.title, r.is_active, r.created_at,
                   (SELECT COUNT(*) FROM reel_assets a WHERE a.reel_id=r.id) AS assets
            FROM reels r
            ORDER BY r.id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return cur.fetchall()
    finally:
        conn.close()


def get_reel(reel_id: int) -> Dict[str, Any] | None:
    ensure_reels_schema()
    conn = get_conn()
    try:
        reel = conn.execute("SELECT * FROM reels WHERE id=?", (reel_id,)).fetchone()
        if not reel:
            return None
        assets = conn.execute(
            "SELECT kind, tg_chat_id, tg_message_id, tg_file_id, tg_file_unique_id, text FROM reel_assets WHERE reel_id=?",
            (reel_id,),
        ).fetchall()
        return {
            "reel": dict(reel),
            "assets": {row["kind"]: dict(row) for row in assets},
        }
    finally:
        conn.close()


def set_reel_active(reel_id: int, active: bool) -> None:
    ensure_reels_schema()
    conn = get_conn()
    try:
        with conn:
            conn.execute("UPDATE reels SET is_active=? WHERE id=?", (1 if active else 0, reel_id))
    finally:
        conn.close()


def delete_reel(reel_id: int) -> None:
    ensure_reels_schema()
    conn = get_conn()
    try:
        with conn:
            conn.execute("DELETE FROM reels WHERE id=?", (reel_id,))
    finally:
        conn.close()


def pick_next_reel_id_for_user(tg_user_id: int) -> Optional[int]:
    ensure_reels_schema()
    conn = get_conn()
    try:
        row = conn.execute(
            """
            SELECT r.id
            FROM reels r
            LEFT JOIN reel_deliveries d
              ON d.reel_id = r.id AND d.tg_user_id = ?
            WHERE r.is_active = 1
              AND d.id IS NULL
            ORDER BY RANDOM()
            LIMIT 1
            """,
            (tg_user_id,),
        ).fetchone()
        return int(row[0]) if row else None
    finally:
        conn.close()



def mark_reel_delivered(tg_user_id: int, reel_id: int, video_msg_id: Optional[int], caption_msg_id: Optional[int]) -> None:
    ensure_reels_schema()
    conn = get_conn()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO reel_deliveries (tg_user_id, reel_id, video_message_id, caption_message_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tg_user_id, reel_id) DO NOTHING
                """,
                (tg_user_id, reel_id, video_msg_id, caption_msg_id),
            )
    finally:
        conn.close()

def reset_user_reel_progress(tg_user_id: int) -> int:
    ensure_reels_schema()
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                """
                DELETE FROM reel_deliveries
                 WHERE tg_user_id = ?
                   AND reel_id IN (SELECT id FROM reels WHERE is_active = 1)
                """,
                (tg_user_id,),
            )
            return cur.rowcount if cur.rowcount is not None else 0
    finally:
        conn.close()

def any_active_reels() -> bool:
    ensure_reels_schema()
    conn = get_conn()
    try:
        row = conn.execute("SELECT 1 FROM reels WHERE is_active = 1 LIMIT 1").fetchone()
        return bool(row)
    finally:
        conn.close()
