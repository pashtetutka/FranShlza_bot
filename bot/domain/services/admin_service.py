# bot/domain/services/admin_service.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Bot

from bot.db.subscriptions import (
    get_conn, is_paid, get_trial_info, has_active_trial, start_free_trial,
)
from bot.domain.services.onboarding_service import send_instruction_package


def _fmt_ddmmyyyy(dt_str: Optional[str]) -> str:
    if not dt_str:
        return "—"
    s = dt_str.replace("T", " ").replace("Z", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None).strftime("%d.%m.%Y")
    except Exception:
        return dt_str

def _now_ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def _add_months(base: Optional[str], months: int) -> str:
    from calendar import monthrange
    if base:
        s = base.replace("T", " ").replace("Z", "")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        else:
            try:
                dt = datetime.fromisoformat(base.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                dt = datetime.utcnow()
    else:
        dt = datetime.utcnow()
    if dt < datetime.utcnow():
        dt = datetime.utcnow()
    y, m = dt.year, dt.month
    m += months
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    from_day = dt.day
    last_day = monthrange(y, m)[1]
    d = min(from_day, last_day)
    return dt.replace(year=y, month=m, day=d).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class UserCard:
    tg_user_id: int
    username: Optional[str]
    role: Optional[str]
    last_seen: Optional[str]
    sub_status: str
    paid_until: Optional[str]
    trial_status: Optional[str]
    trial_expires_at: Optional[str]

def load_user_card(tg_user_id: int) -> Optional[UserCard]:
    conn = get_conn()
    try:
        u = conn.execute(
            "SELECT tg_user_id, username, role, last_seen FROM users WHERE tg_user_id=?",
            (tg_user_id,),
        ).fetchone()
        if not u:
            return None
        s = conn.execute(
            "SELECT status, paid_until FROM subscriptions WHERE tg_user_id=?",
            (tg_user_id,),
        ).fetchone()
        t = conn.execute(
            "SELECT status, trial_expires_at FROM free_trials WHERE tg_user_id=?",
            (tg_user_id,),
        ).fetchone()

        return UserCard(
            tg_user_id=tg_user_id,
            username=u["username"],
            role=u["role"],
            last_seen=u["last_seen"],
            sub_status=(s["status"] if s else "NONE") or "NONE",
            paid_until=(s["paid_until"] if s else None),
            trial_status=(t["status"] if t else None),
            trial_expires_at=(t["trial_expires_at"] if t else None),
        )
    finally:
        conn.close()

def render_user_card(card: UserCard) -> Tuple[str, InlineKeyboardMarkup]:
    sub_active_now = (card.sub_status or "").upper() == "ACTIVE" and (not card.paid_until or card.paid_until >= _now_ts())
    sub_emoji = "🟢" if sub_active_now else "⚪"
    trial_active = (card.trial_status or "").upper() == "ACTIVE"
    trial_emoji = "🟡" if trial_active else "⚪"

    role_txt = (card.role or "—")
    try:
        role_txt = role_txt.upper()
    except Exception:
        pass

    text = (
        f"<b>Пользователь</b>\n"
        f"ID: <code>{card.tg_user_id}</code>\n"
        f"Username: {('@'+card.username) if card.username else '—'}\n"
        f"Роль: {role_txt}\n"
        f"Последний визит: {_fmt_ddmmyyyy(card.last_seen)}\n\n"
        f"<b>Подписка</b> {sub_emoji}\n"
        f"Статус: {card.sub_status or 'NONE'}\n"
        f"Активен до: {_fmt_ddmmyyyy(card.paid_until)}\n\n"
        f"<b>Фритрайл</b> {trial_emoji}\n"
        f"Статус: {card.trial_status or '—'}\n"
        f"Активен до: {_fmt_ddmmyyyy(card.trial_expires_at)}"
    )

    paid = sub_active_now
    rows = []

    # Подписка
    rows.append([InlineKeyboardButton("➕ Продлить подписку +1 мес", callback_data=f"adm:{card.tg_user_id}:sub:extend:1m")])
    rows.append([InlineKeyboardButton("💳 Активировать подписку на 1 мес", callback_data=f"adm:{card.tg_user_id}:sub:activate:1m")])
    rows.append([InlineKeyboardButton("⛔ Отменить подписку", callback_data=f"adm:{card.tg_user_id}:sub:cancel")])

    # Фритрайл
    if not paid:
        rows.append([InlineKeyboardButton("🎁 Запустить фритрайл (2 мес)", callback_data=f"adm:{card.tg_user_id}:trial:start")])
    if trial_active:
        rows.append([InlineKeyboardButton("⌛ Завершить фритрайл сейчас", callback_data=f"adm:{card.tg_user_id}:trial:expire")])

    # Сервис
    rows.append([InlineKeyboardButton("🗑️ Удалить пользователя…", callback_data=f"adm:{card.tg_user_id}:delete:ask")])
    rows.append([InlineKeyboardButton("🔄 Обновить карточку", callback_data=f"adm:{card.tg_user_id}:menu")])

    return text, InlineKeyboardMarkup(rows)


def _ensure_sub_row(conn, uid: int):
    row = conn.execute("SELECT 1 FROM subscriptions WHERE tg_user_id=? LIMIT 1", (uid,)).fetchone()
    if not row:
        conn.execute("INSERT INTO subscriptions (tg_user_id, status) VALUES (?, 'NONE')", (uid,))

def _ensure_trial_row(conn, uid: int):
    row = conn.execute("SELECT 1 FROM free_trials WHERE tg_user_id=? LIMIT 1", (uid,)).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO free_trials (tg_user_id, started_at, trial_expires_at, status)"
            " VALUES (?, datetime('now'), datetime('now'), 'USED')",
            (uid,)
        )


async def exec_action(bot: Bot, action: str, uid: int) -> str:
    conn = get_conn()
    try:
        with conn:
            if action == "sub:activate:1m":
                _ensure_sub_row(conn, uid)
                row = conn.execute("SELECT paid_until FROM subscriptions WHERE tg_user_id=?", (uid,)).fetchone()
                new_until = _add_months(row["paid_until"] if row else None, 1)

                conn.execute(
                    "UPDATE subscriptions SET status='ACTIVE', paid_until=? WHERE tg_user_id=?",
                    (new_until, uid),
                )
                conn.execute(
                    "UPDATE users SET role='OLD', updated_at=datetime('now') WHERE tg_user_id=?",
                    (uid,),
                ) 

                _ensure_trial_row(conn, uid)
                conn.execute("UPDATE free_trials SET status='USED' WHERE tg_user_id=?", (uid,))

                await send_instruction_package(bot, uid)

                return f"Подписка активирована до { _fmt_ddmmyyyy(new_until) }."

            if action == "sub:extend:1m":
                _ensure_sub_row(conn, uid)
                row = conn.execute("SELECT paid_until FROM subscriptions WHERE tg_user_id=?", (uid,)).fetchone()
                base = row["paid_until"] if row else None
                new_until = _add_months(base, 1)

                conn.execute(
                    "UPDATE subscriptions SET status='ACTIVE', paid_until=? WHERE tg_user_id=?",
                    (new_until, uid),
                )
                conn.execute(
                    "UPDATE users SET role='OLD', updated_at=datetime('now') WHERE tg_user_id=?",
                    (uid,),
                )  

                return f"Подписка продлена до { _fmt_ddmmyyyy(new_until) }."

            if action == "sub:cancel":
                _ensure_sub_row(conn, uid)
                conn.execute("UPDATE subscriptions SET status='CANCELED' WHERE tg_user_id=?", (uid,))
                return "Подписка отменена."

            if action == "trial:start":
                if is_paid(uid):
                    return "Нельзя запустить фритрайл: у пользователя активная платная подписка."
                res = start_free_trial(uid, months=2)
                if res == "STARTED":
                    info = get_trial_info(uid)
                    return f"Фритрайл запущен. Активен до: { _fmt_ddmmyyyy(info['trial_expires_at']) if info else '—' }."
                if res == "ACTIVE_ALREADY":
                    info = get_trial_info(uid)
                    return f"Фритрайл уже активен. Активен до: { _fmt_ddmmyyyy(info['trial_expires_at']) if info else '—' }."
                if res == "ALREADY_USED":
                    return "Фритрайл уже использовался ранее."
                return f"Не удалось запустить фритрайл: {res}"

            if action == "trial:expire":
                _ensure_trial_row(conn, uid)
                conn.execute("UPDATE free_trials SET status='EXPIRED', trial_expires_at=datetime('now') WHERE tg_user_id=?", (uid,))
                return "Фритрайл завершён."

            if action == "delete:confirm":
                conn.execute("UPDATE subscriptions SET status='NONE', paid_until=NULL WHERE tg_user_id=?", (uid,))
                conn.execute("DELETE FROM free_trials   WHERE tg_user_id=?", (uid,))
                conn.execute("DELETE FROM subscriptions WHERE tg_user_id=?", (uid,))
                conn.execute("DELETE FROM users         WHERE tg_user_id=?", (uid,))
                return "Пользователь удалён из БД (подписка обнулена, связанные записи удалены)." 

        return "Неизвестное действие."
    finally:
        conn.close()
