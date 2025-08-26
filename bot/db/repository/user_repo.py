import logging
import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Dict

from bot.constants import Role
from bot.db.session import get_conn  

logger = logging.getLogger(__name__)

def _ensure_user_columns(conn: sqlite3.Connection) -> None:

    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    def add(col: str, ddl: str) -> None:
        if col not in cols:
            conn.execute(ddl)
            cols.add(col)

    add("referrer_id", "ALTER TABLE users ADD COLUMN referrer_id INTEGER")
    add("inst_nick",   "ALTER TABLE users ADD COLUMN inst_nick TEXT")
    add("price_offer", "ALTER TABLE users ADD COLUMN price_offer INTEGER")


def _role_to_value(role: Role | str) -> str:
    return role.value if isinstance(role, Role) else str(role)


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

class UserRepository:
    def upsert(self, tg_user_id: int, ref_code: Optional[str] = None) -> None:
        try:
            with get_conn() as con:
                _ensure_user_columns(con)

                con.execute(
                    """
                    INSERT INTO users (tg_user_id, role, created_at, updated_at, last_seen)
                    VALUES (?, ?, datetime('now'), datetime('now'), datetime('now'))
                    ON CONFLICT(tg_user_id) DO UPDATE SET
                      last_seen  = datetime('now'),
                      updated_at = datetime('now')
                    """,
                    (tg_user_id, _role_to_value(Role.UNREGISTERED)),
                )

                if ref_code and ref_code.isdigit():
                    referrer_id = int(ref_code)
                    if referrer_id != tg_user_id:
                        con.execute(
                            """
                            UPDATE users
                               SET referrer_id = COALESCE(referrer_id, ?)
                             WHERE tg_user_id = ?
                            """,
                            (referrer_id, tg_user_id),
                        )
        except sqlite3.Error as e:
            logger.error("user_repo.upsert tg_user_id=%s error=%s", tg_user_id, e)

    def update_role(self, tg_user_id: int, new_role: Role) -> None:
        try:
            with get_conn() as con:
                con.execute(
                    "UPDATE users SET role = ?, updated_at = datetime('now') WHERE tg_user_id = ?",
                    (_role_to_value(new_role), tg_user_id),
                )
        except sqlite3.Error as e:
            logger.error("user_repo.update_role tg_user_id=%s error=%s", tg_user_id, e)

    def get_role(self, tg_user_id: int) -> Optional[Role]:
        try:
            with get_conn() as con:
                cur = con.execute("SELECT role FROM users WHERE tg_user_id = ?", (tg_user_id,))
                row = cur.fetchone()
                if row and row[0]:
                    val = str(row[0]).lower()
                    try:
                        return Role(val)
                    except Exception:
                        return None
        except sqlite3.Error as e:
            logger.error("user_repo.get_role tg_user_id=%s error=%s", tg_user_id, e)
        return None

    def set_field(self, tg_user_id: int, field: str, value) -> None:
        allowed = {"inst_nick", "price_offer", "referrer_id", "role"}
        if field not in allowed:
            logger.error("user_repo.set_field: field %r is not allowed", field)
            return

        try:
            with get_conn() as con:
                _ensure_user_columns(con)
                if field == "role":
                    value = _role_to_value(value)
                con.execute(
                    f"UPDATE users SET {field} = ?, updated_at = datetime('now') WHERE tg_user_id = ?",
                    (value, tg_user_id),
                )
        except sqlite3.Error as e:
            logger.error("user_repo.set_field field=%s error=%s", field, e)

    def get(self, tg_user_id: int) -> Optional[Tuple]:
        try:
            with get_conn() as con:
                cur = con.execute("SELECT * FROM users WHERE tg_user_id = ?", (tg_user_id,))
                return cur.fetchone()
        except sqlite3.Error as e:
            logger.error("user_repo.get tg_user_id=%s error=%s", tg_user_id, e)
        return None

    def list(self, limit: int = 20, offset: int = 0) -> List[Tuple]:
        try:
            with get_conn() as con:
                _ensure_user_columns(con)
                cur = con.execute(
                    """
                    SELECT
                      u.tg_user_id                                                   AS tg_id,
                      u.role                                                         AS role,
                      CASE
                        WHEN UPPER(COALESCE(s.status,'NONE')) = 'ACTIVE'
                         AND (s.paid_until IS NULL OR s.paid_until >= datetime('now'))
                        THEN 1 ELSE 0
                      END                                                            AS paid,
                      u.price_offer                                                  AS price,
                      u.referrer_id                                                  AS parent,
                      u.inst_nick                                                    AS inst,
                      COALESCE(u.created_at, u.updated_at, datetime('now'))          AS joined_at
                    FROM users u
                    LEFT JOIN subscriptions s ON s.tg_user_id = u.tg_user_id
                    ORDER BY joined_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                return cur.fetchall()
        except sqlite3.Error as e:
            logger.error("user_repo.list error=%s", e)
        return []

    def referrals(self, tg_user_id: int) -> List[int]:
        try:
            with get_conn() as con:
                _ensure_user_columns(con)
                cur = con.execute(
                    "SELECT tg_user_id FROM users WHERE referrer_id = ?",
                    (tg_user_id,),
                )
                return [r[0] for r in cur.fetchall()]
        except sqlite3.Error as e:
            logger.error("user_repo.referrals tg_user_id=%s error=%s", tg_user_id, e)
        return []

    def referral_counts(self) -> Dict[int, int]:
        try:
            with get_conn() as con:
                _ensure_user_columns(con)
                cur = con.execute(
                    """
                    SELECT referrer_id AS uid, COUNT(*) AS cnt
                    FROM users
                    WHERE referrer_id IS NOT NULL
                    GROUP BY referrer_id
                    ORDER BY cnt DESC
                    """
                )
                return {uid: cnt for uid, cnt in cur.fetchall()}
        except sqlite3.Error as e:
            logger.error("user_repo.referral_counts error=%s", e)
        return {}
