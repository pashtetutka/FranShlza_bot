import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def init_db(self) -> None:
        """Initialize database schema"""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS users(
                        tg_id       INTEGER PRIMARY KEY,
                        ref_code    TEXT,
                        referrer_id INTEGER,
                        wallet      TEXT,
                        role        TEXT,
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
                )
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def execute(self, query: str, params: tuple = ()) -> Optional[sqlite3.Cursor]:
        """Execute SQL query with error handling"""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                return cur.execute(query, params)
        except sqlite3.Error as e:
            logger.error(f"Database error in query {query}: {e}")
            return None

    def upsert_user(self, tg_id: int, ref_code: Optional[str]) -> None:
        """Insert or update user record."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute(
                    """INSERT OR IGNORE INTO users(tg_id,ref_code,joined_at,referrer_id) 
                       VALUES(?,?,?,?)""",
                    (tg_id, ref_code, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                     int(ref_code) if ref_code and ref_code.isdigit() else None)
                )
        except sqlite3.Error as e:
            logger.error(f"Error upserting user: {e}")

    def set_user_field(self, tg_id: int, field: str, value) -> None:
        """Update single user field."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute(f"UPDATE users SET {field}=? WHERE tg_id=?", (value, tg_id))
        except sqlite3.Error as e:
            logger.error(f"Error setting user field: {e}")

    def get_user(self, tg_id: int) -> Optional[tuple]:
        """Get user record."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute(
                    """SELECT role,paid,subs_ok,price_offer,referrer_id,inst_nick 
                       FROM users WHERE tg_id=?""", (tg_id,)
                )
                return cur.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error getting user: {e}")
            return None

    def store_payment(self, tg_id: int, amount: int) -> None:
        """Record payment."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute(
                    "INSERT INTO payments(tg_id,amount,paid_at) VALUES(?,?,?)",
                    (tg_id, amount, datetime.utcnow().isoformat())
                )
        except sqlite3.Error as e:
            logger.error(f"Error storing payment: {e}")

    def fetch_users(self, limit: int = 20, offset: int = 0) -> List[tuple]:
        """Get paginated user list."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute(
                    """SELECT tg_id,role,paid,price_offer,referrer_id,inst_nick,joined_at
                       FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?""",
                    (limit, offset)
                )
                return cur.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error fetching users: {e}")
            return []

    def fetch_user_detail(self, tg_id: int) -> Optional[tuple]:
        """Get detailed user info."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
                return cur.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error fetching user detail: {e}")
            return None

    def fetch_referrals(self, tg_id: int) -> List[int]:
        """Get user's referrals."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("SELECT tg_id FROM users WHERE referrer_id=?", (tg_id,))
                return [r[0] for r in cur.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching referrals: {e}")
            return []

    def global_stats(self) -> Tuple[int, int, int]:
        """Get global statistics."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM users WHERE paid=1")
                paid_users = cur.fetchone()[0]
                cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments")
                total_rub = cur.fetchone()[0]
                return total_users, paid_users, total_rub
        except sqlite3.Error as e:
            logger.error(f"Error getting global stats: {e}")
            return 0, 0, 0

    def referral_counts(self) -> Dict[int, int]:
        """Get referral counts for all users."""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute(
                    """SELECT referrer_id, COUNT(*) 
                       FROM users WHERE referrer_id IS NOT NULL 
                       GROUP BY referrer_id"""
                )
                return dict(cur.fetchall())
        except sqlite3.Error as e:
            logger.error(f"Error getting referral counts: {e}")
            return {}
