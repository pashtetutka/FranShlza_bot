from __future__ import annotations
import aiosqlite
from datetime import date
from typing import Optional


class SubscriptionRepo:

    def __init__(self, db_path: str = "data/bot.sqlite3"):
        self.db_path = db_path

    @classmethod
    async def open(cls, db_path: str = "data/bot.sqlite3") -> SubscriptionRepo:
        self = cls(db_path)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id      INTEGER NOT NULL,
                    email        TEXT NOT NULL,
                    status       TEXT NOT NULL,
                    periodicity  TEXT,
                    started_at   DATE,
                    expired_at   DATE,
                    payment_url  TEXT NOT NULL
                );
                """
            )
            await db.commit()
        return self

    async def create_pending(
        self,
        *,
        user_id: int,
        email: str,
        payment_url: str,
        periodicity: Optional[str] = None,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO subscriptions (
                    user_id, email, status, periodicity, payment_url
                ) VALUES (?, ?, 'pending', ?, ?)
                """,
                (user_id, email, periodicity, payment_url),
            )
            await db.commit()

    async def mark_paid(
        self,
        *,
        user_id: int,
        started_at: date,
        expired_at: Optional[date] = None,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE subscriptions
                   SET status      = 'paid',
                       started_at  = ?,
                       expired_at  = ?
                 WHERE user_id     = ?
                   AND status      = 'pending'
                """,
                (started_at, expired_at, user_id),
            )
            await db.commit()

    async def get_active(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM subscriptions
                 WHERE user_id = ?
                   AND status  = 'paid'
                   AND (expired_at IS NULL OR expired_at >= DATE('now'))
                 LIMIT 1
                """,
                (user_id,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
