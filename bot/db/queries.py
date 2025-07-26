from typing import Optional, List, Dict, Tuple
import sqlite3
import logging
from datetime import datetime
from bot.constants import Role

logger = logging.getLogger(__name__)

# SQL Queries
SQL_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users(
    tg_id       INTEGER PRIMARY KEY,
    ref_code    TEXT,
    referrer_id INTEGER,
    wallet      TEXT,
    role        TEXT DEFAULT 'unregistered',
    inst_nick   TEXT,
    price_offer INTEGER,
    paid        INTEGER DEFAULT 0,
    subs_ok     INTEGER DEFAULT 0,
    joined_at   TEXT
);
CREATE TABLE IF NOT EXISTS payments(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id       INTEGER,
    amount      INTEGER,
    paid_at     TEXT
);
"""

class DBHelper:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def init_db(self) -> None:
        """Initialize database schema."""
        try:
            with sqlite3.connect(self.db_path) as con:
                con.executescript(SQL_CREATE_TABLES)
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def upsert_user(self, tg_id: int, ref_code: Optional[str] = None) -> None:
        """Create new user or ignore if exists."""
        try:
            with sqlite3.connect(self.db_path) as con:
                con.execute(
                    """INSERT OR IGNORE INTO users
                       (tg_id, ref_code, referrer_id, role, joined_at)
                       VALUES(?, ?, ?, ?, ?)""",
                    (
                        tg_id,
                        ref_code,
                        int(ref_code) if ref_code and ref_code.isdigit() else None,
                        Role.UNREGISTERED,
                        datetime.utcnow().isoformat()
                    )
                )
                con.commit()
        except sqlite3.Error as e:
            logger.error(f"Error upserting user {tg_id}: {e}")

    def update_user_role(self, tg_id: int, new_role: Role) -> None:
        """Update user's role."""
        try:
            with sqlite3.connect(self.db_path) as con:
                con.execute(
                    "UPDATE users SET role = ? WHERE tg_id = ?",
                    (new_role.value, tg_id)
                )
                con.commit()
        except sqlite3.Error as e:
            logger.error(f"Error updating role for user {tg_id}: {e}")

    def get_user_role(self, tg_id: int) -> Optional[Role]:
        """Get user's current role."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.execute(
                    "SELECT role FROM users WHERE tg_id = ?",
                    (tg_id,)
                )
                if row := cur.fetchone():
                    return Role(row[0])
        except sqlite3.Error as e:
            logger.error(f"Error getting role for user {tg_id}: {e}")
        return None

    def set_user_field(self, tg_id: int, field: str, value) -> None:
        """Generic field updater for users table."""
        try:
            with sqlite3.connect(self.db_path) as con:
                con.execute(f"UPDATE users SET {field} = ? WHERE tg_id = ?", (value, tg_id))
                con.commit()
        except sqlite3.Error as e:
            logger.error(f"Error setting field {field} for user {tg_id}: {e}")

    def get_user(self, tg_id: int) -> Optional[Tuple]:
        """Return full users row or None."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
                return cur.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error fetching user {tg_id}: {e}")
        return None

    def fetch_users(self, limit: int = 20, offset: int = 0) -> List[Tuple]:
        """List latest users with key fields."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.execute(
                    """SELECT tg_id, role, paid, price_offer,
                              referrer_id, inst_nick, joined_at
                       FROM users
                       ORDER BY joined_at DESC
                       LIMIT ? OFFSET ?""",
                    (limit, offset),
                )
                return cur.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error fetching users list: {e}")
        return []

    def fetch_user_detail(self, tg_id: int) -> Optional[Tuple]:
        """Get all columns for one user."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
                return cur.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error fetching details for user {tg_id}: {e}")
        return None

    def fetch_referrals(self, tg_id: int) -> List[int]:
        """Return list of tg_id who have this user as referrer."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.execute("SELECT tg_id FROM users WHERE referrer_id = ?", (tg_id,))
                return [r[0] for r in cur.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching referrals for {tg_id}: {e}")
        return []

    def store_payment(self, tg_id: int, amount: int) -> None:
        """Record a payment for analytics and referral split."""
        try:
            with sqlite3.connect(self.db_path) as con:
                con.execute(
                    "INSERT INTO payments(tg_id, amount, paid_at) VALUES (?, ?, ?)",
                    (tg_id, amount, datetime.utcnow().isoformat()),
                )
                con.commit()
        except sqlite3.Error as e:
            logger.error(f"Error storing payment for {tg_id}: {e}")

    def global_stats(self) -> Tuple[int,int,int]:
        """Return (total_users, paid_users, total_amount_rub)."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("SELECT COUNT(*) FROM users"); total = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM users WHERE paid=1"); paid = cur.fetchone()[0]
                cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments"); total_rub = cur.fetchone()[0]
                return total, paid, total_rub
        except sqlite3.Error as e:
            logger.error(f"Error computing global stats: {e}")
        return 0,0,0

    def referral_counts(self) -> Dict[int,int]:
        """Return dict {referrer_id: count_of_referrals} for all users."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.execute(
                    "SELECT referrer_id, COUNT(*) FROM users "
                    "WHERE referrer_id IS NOT NULL GROUP BY referrer_id"
                )
                return {uid: cnt for uid, cnt in cur.fetchall()}
        except sqlite3.Error as e:
            logger.error(f"Error computing referral counts: {e}")
        return {}
