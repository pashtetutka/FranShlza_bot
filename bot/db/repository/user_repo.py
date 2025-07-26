import logging, sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Dict
from bot.constants import Role
from bot.db.session import get_conn

logger = logging.getLogger(__name__)

class UserRepository:
    def upsert(self, tg_id: int, ref_code: Optional[str] = None) -> None:
        try:
            with get_conn() as con:
                con.execute(
                    "INSERT OR IGNORE INTO users(tg_id, ref_code, referrer_id, role, joined_at)"
                    " VALUES(?, ?, ?, ?, ?)",
                    (
                        tg_id,
                        ref_code,
                        int(ref_code) if ref_code and ref_code.isdigit() else None,
                        Role.UNREGISTERED,
                        datetime.utcnow().isoformat(),
                    ),
                )
        except sqlite3.Error as e:
            logger.error("upsert user %s %s", tg_id, e)

    def update_role(self, tg_id: int, new_role: Role) -> None:
        try:
            with get_conn() as con:
                con.execute("UPDATE users SET role = ? WHERE tg_id = ?", (new_role.value, tg_id))
        except sqlite3.Error as e:
            logger.error("update role %s %s", tg_id, e)

    def get_role(self, tg_id: int) -> Optional[Role]:
        try:
            with get_conn() as con:
                cur = con.execute("SELECT role FROM users WHERE tg_id = ?", (tg_id,))
                if row := cur.fetchone():
                    return Role(row[0])
        except sqlite3.Error as e:
            logger.error("get role %s %s", tg_id, e)
        return None

    def set_field(self, tg_id: int, field: str, value) -> None:
        try:
            with get_conn() as con:
                con.execute(f"UPDATE users SET {field} = ? WHERE tg_id = ?", (value, tg_id))
        except sqlite3.Error as e:
            logger.error("set field %s %s", field, e)

    def get(self, tg_id: int) -> Optional[Tuple]:
        try:
            with get_conn() as con:
                cur = con.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
                return cur.fetchone()
        except sqlite3.Error as e:
            logger.error("get user %s %s", tg_id, e)
        return None

    def list(self, limit: int = 20, offset: int = 0) -> List[Tuple]:
        try:
            with get_conn() as con:
                cur = con.execute(
                    "SELECT tg_id, role, paid, price_offer, referrer_id, inst_nick, joined_at "
                    "FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
                return cur.fetchall()
        except sqlite3.Error as e:
            logger.error("list users %s", e)
        return []

    def referrals(self, tg_id: int) -> List[int]:
        try:
            with get_conn() as con:
                cur = con.execute("SELECT tg_id FROM users WHERE referrer_id = ?", (tg_id,))
                return [r[0] for r in cur.fetchall()]
        except sqlite3.Error as e:
            logger.error("referrals %s", e)
        return []

    def referral_counts(self) -> Dict[int, int]:
        try:
            with get_conn() as con:
                cur = con.execute(
                    "SELECT referrer_id, COUNT(*) FROM users "
                    "WHERE referrer_id IS NOT NULL GROUP BY referrer_id"
                )
                return {uid: cnt for uid, cnt in cur.fetchall()}
        except sqlite3.Error as e:
            logger.error("referral counts %s", e)
        return {}
