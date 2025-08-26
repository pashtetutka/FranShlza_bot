from __future__ import annotations

from bot.db.connection import get_conn
from contextlib import closing
from typing import Optional, Literal

import sqlite3

def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,)).fetchone()
    return row is not None

def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}

def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl_sql: str) -> None:
    if column not in _columns(conn, table):
        conn.execute(ddl_sql)

def _rebuild_table_user_id_to_tg_user_id(conn: sqlite3.Connection, table: str, create_sql: str, insert_sql: str) -> None:
    """Общая миграция: переименовать user_id -> tg_user_id через перестройку таблицы."""
    conn.execute("PRAGMA foreign_keys=OFF;")
    try:
        conn.execute("BEGIN;")
        conn.execute(f"ALTER TABLE {table} RENAME TO {table}_old;")
        conn.execute(create_sql)
        conn.execute(insert_sql)
        conn.execute(f"DROP TABLE {table}_old;")
        conn.execute("COMMIT;")
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON;")

def _ensure_users_schema(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "users"):
        conn.execute("""
            CREATE TABLE users (
              tg_user_id  INTEGER PRIMARY KEY,
              username    TEXT,
              role        TEXT,
              created_at  TEXT DEFAULT (datetime('now')),
              updated_at  TEXT DEFAULT (datetime('now')),
              last_seen   TEXT DEFAULT (datetime('now'))
            );
        """)
    else:
        cols = _columns(conn, "users")
        if "tg_user_id" not in cols and "user_id" in cols:
            _rebuild_table_user_id_to_tg_user_id(
                conn,
                "users",
                create_sql="""
                    CREATE TABLE users (
                      tg_user_id  INTEGER PRIMARY KEY,
                      username    TEXT,
                      role        TEXT,
                      created_at  TEXT DEFAULT (datetime('now')),
                      updated_at  TEXT DEFAULT (datetime('now')),
                      last_seen   TEXT DEFAULT (datetime('now'))
                    );
                """,
                insert_sql="""
                    INSERT INTO users (tg_user_id, username, role, created_at, updated_at, last_seen)
                    SELECT user_id, username, role, created_at, updated_at, COALESCE(last_seen, datetime('now'))
                    FROM users_old;
                """,
            )
        _ensure_column(conn, "users", "last_seen",
                       "ALTER TABLE users ADD COLUMN last_seen TEXT DEFAULT (datetime('now'));")

def _ensure_free_trials_schema(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "free_trials"):
        conn.execute("""
            CREATE TABLE free_trials (
              tg_user_id        INTEGER PRIMARY KEY,
              started_at        TEXT NOT NULL DEFAULT (datetime('now')),
              trial_expires_at  TEXT NOT NULL,
              status            TEXT NOT NULL DEFAULT 'ACTIVE'
            );
        """)
    else:
        cols = _columns(conn, "free_trials")
        if "tg_user_id" not in cols and "user_id" in cols:
            _rebuild_table_user_id_to_tg_user_id(
                conn,
                "free_trials",
                create_sql="""
                    CREATE TABLE free_trials (
                      tg_user_id        INTEGER PRIMARY KEY,
                      started_at        TEXT NOT NULL DEFAULT (datetime('now')),
                      trial_expires_at  TEXT NOT NULL,
                      status            TEXT NOT NULL DEFAULT 'ACTIVE'
                    );
                """,
                insert_sql="""
                    INSERT INTO free_trials (tg_user_id, started_at, trial_expires_at, status)
                    SELECT user_id, started_at, trial_expires_at, status
                    FROM free_trials_old;
                """,
            )

def _ensure_subscriptions_schema(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "subscriptions"):
        conn.execute("""
            CREATE TABLE subscriptions (
              tg_user_id  INTEGER PRIMARY KEY,
              status      TEXT NOT NULL DEFAULT 'NONE',
              paid_until  TEXT
            );
        """)
    else:
        cols = _columns(conn, "subscriptions")
        if "tg_user_id" not in cols and "user_id" in cols:
            _rebuild_table_user_id_to_tg_user_id(
                conn,
                "subscriptions",
                create_sql="""
                    CREATE TABLE subscriptions (
                      tg_user_id  INTEGER PRIMARY KEY,
                      status      TEXT NOT NULL DEFAULT 'NONE',
                      paid_until  TEXT
                    );
                """,
                insert_sql="""
                    INSERT INTO subscriptions (tg_user_id, status, paid_until)
                    SELECT user_id, status, paid_until
                    FROM subscriptions_old;
                """,
            )

def init_db() -> None:
    conn = get_conn()
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        _ensure_users_schema(conn)
        _ensure_free_trials_schema(conn)
        _ensure_subscriptions_schema(conn)
        conn.commit()
    finally:
        conn.close()

_DB_READY = False
def ensure_db():
    global _DB_READY
    if not _DB_READY:
        init_db()
        _DB_READY = True

def upsert_user_basic(tg_user_id: int, username: str | None):
    ensure_db()
    conn = get_conn()
    sql = """
        INSERT INTO users (tg_user_id, username, last_seen)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(tg_user_id) DO UPDATE SET
          username = excluded.username,
          last_seen = datetime('now'),
          updated_at = datetime('now')
    """
    try:
        with conn:
            conn.execute(sql, (tg_user_id, username))
    finally:
        conn.close()

def is_paid(tg_user_id: int) -> bool:
    """True, если подписка ACTIVE и ещё не истёкла."""
    ensure_db()
    conn = get_conn()
    query = """
        SELECT 1
        FROM subscriptions
        WHERE tg_user_id = ?
          AND UPPER(COALESCE(status,'NONE')) = 'ACTIVE'
          AND (paid_until IS NULL OR paid_until >= datetime('now'))
        LIMIT 1
    """
    try:
        row = conn.execute(query, (tg_user_id,)).fetchone()
        return row is not None
    except sqlite3.OperationalError as e:
        if "no such column: tg_user_id" in str(e):
            conn.close()
            init_db() 
            conn = get_conn()
            row = conn.execute(query, (tg_user_id,)).fetchone()
            return row is not None
        raise
    finally:
        conn.close()

def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table});")
    return any(row[1] == column for row in cur.fetchall())

def init_subscription_schema():
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

def safe_set_role(user_id: int, role: Literal["new","old"]):
    with closing(get_conn()) as conn, conn:
        conn.execute("""
        INSERT INTO users(tg_user_id, role) VALUES(?, ?)
        ON CONFLICT(tg_user_id) DO UPDATE SET role = COALESCE(role, excluded.role)
        """, (user_id, role))

def get_role(user_id: int) -> Optional[str]:
    with closing(get_conn()) as conn, conn:
        row = conn.execute("SELECT role FROM users WHERE tg_user_id=?", (user_id,)).fetchone()
        return row[0] if row else None


def ever_had_trial(user_id: int) -> bool:
    info = get_trial_info(user_id)
    return bool(info and info["trial_started_at"])
def get_trial_info(tg_user_id: int) -> dict | None:
    ensure_db()
    conn = get_conn()
    try:
        row = conn.execute("""
            SELECT
              ft.started_at,
              ft.trial_expires_at,
              ft.status AS trial_status,
              (
                SELECT s.status
                FROM subscriptions s
                WHERE s.tg_user_id = ft.tg_user_id
                LIMIT 1
              ) AS subscription_status
            FROM free_trials ft
            WHERE ft.tg_user_id = ?
            LIMIT 1
        """, (tg_user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def has_active_trial(tg_user_id: int) -> bool:
    ensure_db()
    conn = get_conn()
    try:
        row = conn.execute("""
            SELECT 1
            FROM free_trials
            WHERE tg_user_id = ?
              AND UPPER(COALESCE(status,'NONE')) = 'ACTIVE'
              AND datetime(trial_expires_at) >= datetime('now')
            LIMIT 1
        """, (tg_user_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def start_free_trial(tg_user_id: int, months: int = 2) -> str:
    ensure_db()
    conn = get_conn()
    try:
        with conn:
            row = conn.execute("""
                SELECT status, trial_expires_at
                FROM free_trials
                WHERE tg_user_id = ?
                LIMIT 1
            """, (tg_user_id,)).fetchone()

            if row:
                st = (row["status"] or "NONE").upper()
                not_expired = conn.execute(
                    "SELECT 1 WHERE datetime(?) >= datetime('now')",
                    (row["trial_expires_at"],)
                ).fetchone() is not None

                if st == "ACTIVE" and not_expired:
                    return "ACTIVE_ALREADY"

                return "ALREADY_USED"

            conn.execute("""
                INSERT INTO free_trials (tg_user_id, started_at, trial_expires_at, status)
                VALUES (
                    ?, datetime('now'), datetime('now', ?), 'ACTIVE'
                )
            """, (tg_user_id, f'+{months} months'))
            return "STARTED"
    finally:
        conn.close()

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
