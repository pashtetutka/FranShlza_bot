import logging, sqlite3
from datetime import datetime
from typing import Tuple
from bot.db.session import get_conn

logger = logging.getLogger(__name__)

class PaymentRepository:
    def store(self, tg_id: int, amount: int) -> None:
        try:
            with get_conn() as con:
                con.execute(
                    "INSERT INTO payments(tg_id, amount, paid_at) VALUES (?, ?, ?)",
                    (tg_id, amount, datetime.utcnow().isoformat()),
                )
        except sqlite3.Error as e:
            logger.error("store payment %s %s", tg_id, e)

    def global_stats(self) -> Tuple[int, int, int]:
        try:
            with get_conn() as con:
                cur = con.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                total = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM users WHERE paid=1")
                paid = cur.fetchone()[0]
                cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments")
                money = cur.fetchone()[0]
                return total, paid, money
        except sqlite3.Error as e:
            logger.error("global stats %s", e)
        return 0, 0, 0
