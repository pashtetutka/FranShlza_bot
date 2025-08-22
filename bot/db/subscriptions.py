# bot/db/subscriptions.py
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

DB_PATH = "bot.db"  # поправь, если у тебя другой путь

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table});")
    return any(row[1] == column for row in cur.fetchall())

def init_subscription_schema():
    """Добавляет недостающие столбцы в users. Безопасно гонять на старте."""
    with closing(get_conn()) as conn, conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_user_id INTEGER PRIMARY KEY,
            username   TEXT,
            is_paid    INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            last_seen  TEXT
        );
        """)
        alters = []
        for name, ddl in [
            ("role", "ALTER TABLE users ADD COLUMN role TEXT;"),
            ("subscription_status", "ALTER TABLE users ADD COLUMN subscription_status TEXT;"),
            ("plan", "ALTER TABLE users ADD COLUMN plan TEXT;"),
            ("trial_started_at", "ALTER TABLE users ADD COLUMN trial_started_at TEXT;"),
            ("trial_expires_at", "ALTER TABLE users ADD COLUMN trial_expires_at TEXT;"),
            ("trial_offer_shown", "ALTER TABLE users ADD COLUMN trial_offer_shown INTEGER DEFAULT 0;"),
        ]:
            if not _column_exists(conn, "users", name):
                alters.append(ddl)
        for sql in alters:
            conn.execute(sql)

def upsert_user_basic(user_id: int, username: Optional[str]):
    with closing(get_conn()) as conn, conn:
        conn.execute("""
        INSERT INTO users(tg_user_id, username, last_seen)
        VALUES(?, ?, datetime('now'))
        ON CONFLICT(tg_user_id) DO UPDATE SET
            username=excluded.username,
            last_seen=datetime('now')
        """, (user_id, username))

def safe_set_role(user_id: int, role: Literal["new","old"]):
    """Сохраняем роль только если ещё не была установлена (не перезатираем)."""
    with closing(get_conn()) as conn, conn:
        conn.execute("""
        INSERT INTO users(tg_user_id, role) VALUES(?, ?)
        ON CONFLICT(tg_user_id) DO UPDATE SET role = COALESCE(role, excluded.role)
        """, (user_id, role))

def get_role(user_id: int) -> Optional[str]:
    with closing(get_conn()) as conn, conn:
        row = conn.execute("SELECT role FROM users WHERE tg_user_id=?", (user_id,)).fetchone()
        return row[0] if row else None

def is_paid(user_id: int) -> bool:
    with closing(get_conn()) as conn, conn:
        row = conn.execute("""
            SELECT COALESCE(is_paid,0),
                   CASE WHEN subscription_status='PAID' THEN 1 ELSE 0 END
            FROM users WHERE tg_user_id=?
        """, (user_id,)).fetchone()
        if not row: return False
        return bool(row[0]) or bool(row[1])

def get_trial_info(user_id: int):
    with closing(get_conn()) as conn, conn:
        row = conn.execute("""
            SELECT subscription_status, plan, trial_started_at, trial_expires_at
            FROM users WHERE tg_user_id=?
        """, (user_id,)).fetchone()
        if not row: return None
        status, plan, ts, te = row
        return {"status": status, "plan": plan, "trial_started_at": ts, "trial_expires_at": te}

def has_active_trial(user_id: int) -> bool:
    info = get_trial_info(user_id)
    if not info: return False
    if info["status"] != "TRIAL" or not info["trial_expires_at"]:
        return False
    try:
        expires = datetime.fromisoformat(info["trial_expires_at"])
    except Exception:
        return False
    return expires.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)

def ever_had_trial(user_id: int) -> bool:
    info = get_trial_info(user_id)
    return bool(info and info["trial_started_at"])

def start_free_trial(user_id: int, months: int = 2) -> str:
    """
    Пытаемся запустить триал.
    Возвращает: 'PAID_ALREADY' | 'ACTIVE_ALREADY' | 'ALREADY_USED' | 'STARTED'
    """
    if is_paid(user_id):
        return "PAID_ALREADY"
    if has_active_trial(user_id):
        return "ACTIVE_ALREADY"
    if ever_had_trial(user_id):
        return "ALREADY_USED"

    now = datetime.now(timezone.utc)
    # точные 60 дней — как в ТЗ
    expires = now + timedelta(days=60)
    with closing(get_conn()) as conn, conn:
        conn.execute("""
            INSERT INTO users(tg_user_id, subscription_status, plan, trial_started_at, trial_expires_at)
            VALUES(?, 'TRIAL', 'FREE_TRIAL_2M', ?, ?)
            ON CONFLICT(tg_user_id) DO UPDATE SET
                subscription_status='TRIAL',
                plan='FREE_TRIAL_2M',
                trial_started_at=?,
                trial_expires_at=?
        """, (user_id, now.isoformat(), expires.isoformat(),
              now.isoformat(), expires.isoformat()))
    return "STARTED"

def is_trial_offer_shown(user_id: int) -> bool:
    with closing(get_conn()) as conn, conn:
        row = conn.execute("SELECT COALESCE(trial_offer_shown,0) FROM users WHERE tg_user_id=?",
                           (user_id,)).fetchone()
        return bool(row and row[0])

def mark_trial_offer_shown(user_id: int):
    with closing(get_conn()) as conn, conn:
        conn.execute("""
        INSERT INTO users(tg_user_id, trial_offer_shown) VALUES(?, 1)
        ON CONFLICT(tg_user_id) DO UPDATE SET trial_offer_shown=1
        """, (user_id,))
