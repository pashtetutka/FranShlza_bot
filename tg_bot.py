from __future__ import annotations
import os
import sqlite3
import logging
import asyncio
from telegram.constants import ParseMode
from datetime import datetime
from typing import Optional, List
from telegram import (
    Update,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from dotenv import load_dotenv
from config import BOT_TOKEN, ADMIN_ID, CARD_NUMBER, PRICE_RUB, SMALL_PRICE_RUB, DB_PATH

# ─── MEDIA FILE IDS (Telegram) ─────────────────────
IMAGE_FILE_IDS = [
    "AgACAgIAAxkDAANhaHL6D6ottuienNw3_MHYheuHs1gAAu8EMhsC0phLe3Xuf69LDzcBAAMCAAN3AAM2BA",
    "AgACAgIAAxkDAANiaHL6DwnIm9XCAAG2sfPEWPZlR0dNAALwBDIbAtKYS4KD2bYx6_7ZAQADAgADdwADNgQ",
    "AgACAgIAAxkDAANjaHL6ED8t9XdCcZx4soJLgomntnsAAvEEMhsC0phLi4NqOQ5LOa8BAAMCAAN3AAM2BA",
    "AgACAgIAAxkDAANkaHL6EX4jVXdCrrqSMEfdisCFb9AAAvIEMhsC0phLOuMcY0CfGUABAAMCAAN3AAM2BA",
    "AgACAgIAAxkDAANlaHL6EaaiBBKuNTneGnxoHGeowdMAAvMEMhsC0phLO5-sUli9yAABAQADAgADdwADNgQ",
    "AgACAgIAAxkDAANmaHL6EgpBeNKLnu7gAAGr86_R6SJpAAL0BDIbAtKYS8gs1elZLtgbAQADAgADdwADNgQ",
    "AgACAgIAAxkDAANnaHL6E2TQXz-C0Cy6JDrsCmPpYYcAAvUEMhsC0phLI2oq0bT_vAwBAAMCAAN3AAM2BA",
    "AgACAgIAAxkDAANoaHL6FLc-HKp24UX76Kf-BMX25P0AAvYEMhsC0phLe5K4v70ahjwBAAMCAAN3AAM2BA",
]
VIDEO_FILE_ID = "BAACAgIAAxkBAAIRwmh7eaB8DOZX1be68Hkhqeikt_JWAALYeAACKF3gSwjj1H5O3kk5NgQ"
YELLOW_FILE_ID = "AgACAgIAAxkDAAIC4mh6Ddsy9-s3rxNnkweC4LPkNwMsAAJW7zEb5E7QS7m4drmHEFyZAQADAgADdwADNgQ"

# ─── LOGGING ───────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── DATABASE SETUP ─────────────────────────────────
def init_db() -> None:
    """Ensure required tables exist."""
    with sqlite3.connect(DB_PATH) as con:
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
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id   INTEGER,
                amount  INTEGER, 
                paid_at TEXT
            );
            """
        )
        try:
            cur.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
        except sqlite3.OperationalError:
            pass
        con.commit()

# ─── DB HELPERS ────────────────────────────────────
def upsert_user(tg_id: int, ref_code: Optional[str]) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT OR IGNORE INTO users(tg_id,ref_code,joined_at,referrer_id) VALUES(?,?,?,?)",
            (tg_id, ref_code, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
             int(ref_code) if ref_code and ref_code.isdigit() else None),
        )
        con.commit()


def set_user_field(tg_id: int, field: str, value) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(f"UPDATE users SET {field}=? WHERE tg_id=?", (value, tg_id))
        con.commit()


def get_user(tg_id: int) -> Optional[tuple]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT role,paid,subs_ok,price_offer,referrer_id,inst_nick FROM users WHERE tg_id=?",
            (tg_id,),
        )
        return cur.fetchone()


def store_payment(tg_id: int, amount: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO payments(tg_id,amount,paid_at) VALUES(?,?,?)",
            (tg_id, amount, datetime.utcnow().isoformat()),
        )
        con.commit()


def fetch_users(limit: int = 20, offset: int = 0) -> List[tuple]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            """SELECT tg_id, role, paid, price_offer,
                     referrer_id, inst_nick, joined_at
               FROM users
               ORDER BY joined_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        )
        return cur.fetchall()


def fetch_user_detail(tg_id: int) -> Optional[tuple]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        return cur.fetchone()


def fetch_referrals(tg_id: int) -> List[int]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT tg_id FROM users WHERE referrer_id=?", (tg_id,))
        return [r[0] for r in cur.fetchall()]


def global_stats() -> tuple[int, int, int]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users"); total_users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE paid=1"); paid_users = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments"); total_rub = cur.fetchone()[0]
        return total_users, paid_users, total_rub

def referral_counts() -> dict[int, int]:
    """{uid: children_qty} для всех пользователей."""
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT referrer_id, COUNT(*) FROM users WHERE referrer_id IS NOT NULL GROUP BY referrer_id")
        return {uid: cnt for uid, cnt in cur.fetchall()}


# ─── KEYBOARDS ─────────────────────────────────────
INTRO_KB = InlineKeyboardMarkup(
    [[InlineKeyboardButton("Ознакомился ✅", callback_data="intro_done")]]
)
CHOICE_KB = ReplyKeyboardMarkup([["👋 Хочу к вам", "ℹ️ Подробнее"]], resize_keyboard=True)
ROLE_KB = InlineKeyboardMarkup(
    [[
        InlineKeyboardButton("Новичок", callback_data="role_new"),
        InlineKeyboardButton("Старичок", callback_data="role_old"),
    ]]
)
PAY_NOTIFY = InlineKeyboardMarkup([[InlineKeyboardButton("Я оплатил", callback_data="notify_payment")]])
MENU_KB = ReplyKeyboardMarkup([[
    "📞 Поддержка", "👥 Реферальная ссылка", "📊 Статистика"
]], resize_keyboard=True)

# ─── UTILS ──────────────────────────────────────────
def _chunks(s: str, n: int = 4000):
    """Разбить строку на куски ≤ n символов для Telegram."""
    for i in range(0, len(s), n):
        yield s[i : i + n]

# ─── send_long ────────────────────────────────────
async def send_long(bot, chat_id: int, text: str) -> None:
    """Разбить текст по строкам (≤4096) и отправить с HTML-парсингом."""
    lines = text.split("\n")
    part = ""
    for line in lines:
        if len(part) + len(line) + 1 > 4000:
            await bot.send_message(chat_id, part, parse_mode=ParseMode.HTML)
            part = ""
        part += line + "\n"
    if part:
        await bot.send_message(chat_id, part, parse_mode=ParseMode.HTML)


# ─── pretty printing ───────────────────────────────
def fmt_table(rows: list[tuple], headers: list[str]) -> str:
    """
    Рисует ровную ASCII-таблицу, оборачивает в <pre>…</pre> для HTML.
    Заголовки — по центру, данные — влево.
    """
    # вычисляем ширины колонок
    cols = list(zip(headers, *rows))
    widths = [max(len(str(v)) for v in col) for col in cols]

    # строка заголовков (центрируем)
    header = " | ".join(
        f"{headers[i]:^{widths[i]}}"
        for i in range(len(headers))
    )
    # разделитель
    sep = "-+-".join("-" * widths[i] for i in range(len(widths)))

    # строки данных (влево)
    data_lines = []
    for row in rows:
        data_lines.append(
            " | ".join(f"{str(row[i]):<{widths[i]}}" for i in range(len(row)))
        )

    body = "\n".join([header, sep] + data_lines)
    return f"<pre>\n{body}\n</pre>"



# ─── HANDLERS ─────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    ref_code: Optional[str] = context.args[0] if context.args else None
    upsert_user(uid, ref_code)

    media: List[InputMediaPhoto] = [InputMediaPhoto(fid) for fid in IMAGE_FILE_IDS]
    try:
        await context.bot.send_media_group(chat_id=uid, media=media)
    except Exception as e:
        logger.warning("send_media_group failed: %s", e)

    await update.message.reply_text(
        "Когда ознакомитесь с материалами — нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Ознакомился ✅", callback_data="intro_done")]]
        ),
    )

async def intro_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "Мы рады, что вы уделили нам время! Что дальше?", reply_markup=CHOICE_KB
    )

ABOUT_CHAT_ID = 918767042
ABOUTMESSAGE_ID = 4646

async def about_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.copy_message(
        chat_id=update.effective_chat.id,
        from_chat_id=ABOUT_CHAT_ID,
        message_id=ABOUTMESSAGE_ID
    )


async def want_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Вы уже ведёте мотивационный блог или только начинаете?",
        reply_markup=ROLE_KB,
    )

async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "role_new":
        set_user_field(uid, "role", "new")
        set_user_field(uid, "price_offer", PRICE_RUB)        
        await q.message.reply_text(
            f"Переведите {PRICE_RUB}₽ на карту {CARD_NUMBER}", reply_markup=PAY_NOTIFY
        )
    else:
        set_user_field(uid, "role", "old_pending")        
        context.user_data["awaiting_inst_nick"] = True
        await q.message.reply_text("Введите ваш Instagram-ник:")


async def notify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    tg_user = f"@{q.from_user.username}" if q.from_user.username else q.from_user.first_name

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Да, он оплатил", callback_data=f"confirm_{uid}")]])
    await context.bot.send_message(
        ADMIN_ID, f"Пользователь {tg_user} нажал «Я оплатил»", reply_markup=kb
    )
    await q.message.reply_text("Администратор получит уведомление.")

async def handle_instagram_nick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Срабатывает ТОЛЬКО если ожидаем ник."""
    if not context.user_data.get("awaiting_inst_nick"):
        return                          
    BAD_PREFIXES = ("ℹ️", "👋", "📞", "👥", "📊")
    if any(update.message.text.startswith(p) for p in BAD_PREFIXES):
        return
    inst_nick_raw = update.message.text.strip()
    inst_nick     = inst_nick_raw.lstrip("@") 
    uid           = update.effective_user.id

    set_user_field(uid, "inst_nick", inst_nick)
    context.user_data["awaiting_inst_nick"] = False

    tg_user = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
    await context.bot.send_message(ADMIN_ID,f"Старичок Instagram: @{inst_nick}\nTelegram: {tg_user}\nuid: {uid}\n")
    await context.bot.send_message(ADMIN_ID,f"/price {uid} 1000")
    await update.message.reply_text(
        "Ваш аккаунт на модерации. Ожидайте индивидуальную цену.📩"
    )

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_ID not in (update.effective_user.id, update.effective_chat.id):
        return
    if len(context.args) != 2:
        await update.message.reply_text("Использование: /price <tg_id> <сумма>")
        return
    try:
        tgt = int(context.args[0]); amt = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Оба аргумента должны быть числами.")
        return

    set_user_field(tgt, "price_offer", amt)
    set_user_field(tgt, "role", "old") 
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"Я оплатил {amt}₽", callback_data="notify_payment")]])
    await context.bot.send_message(
        tgt, f"Ваша цена: {amt}₽. Ждем оплату", reply_markup=kb
    )
    await update.message.reply_text(f"Цена {amt}₽ назначена пользователю {tgt}.")

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    try:
        uid = int(q.data.split("_")[1])
    except (IndexError, ValueError):
        return

    set_user_field(uid, "paid", 1)
    store_payment(uid, PRICE_RUB)

    await q.message.reply_text(f"Оплата пользователя {uid} подтверждена.")

    await context.bot.send_photo(chat_id=uid, photo=YELLOW_FILE_ID)
    await context.bot.send_message(
        chat_id=uid,
        text = '''Итак, первым делом тебе нужно создать новый профиль в инстаграм - это наш фундамент\n
Аватар - бери мой жёлтый цвет, который я прикрепил. В дальнейшем, при достижении целей, ты сможешь поменять аватар на свой\n
Имя профиля - сделай что-то понятное, связанное с нашим контентом (пример, @creatorofmotivation)\n
Описание - добавь смысловую "упаковку" (пример, заряжайся мотивацией каждый день)\n
И последнее - надо переключить аккаунт с личного на профессиональный, чтобы мы могли видеть все цифры. Инструкция как это сделать далее, нажми кнопку''',
        reply_markup=MENU_KB,
    )
    await context.bot.send_video(chat_id=uid, video=VIDEO_FILE_ID)

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid  = update.effective_user.id
    text = update.message.text

    if text == "📞 Поддержка":
        context.user_data["awaiting_support"] = True
        await update.message.reply_text("Напишите ваш вопрос для поддержки.")
    elif text == "👥 Реферальная ссылка":
        await update.message.reply_text(
            f"Ваша реферальная ссылка: \n https://t.me/{context.bot.username}?start={uid}"
        )
    elif text == "📊 Статистика":
        await update.message.reply_text("📊 Статистика в разработке.")

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("awaiting_support"):
        return
    user    = update.effective_user
    tg_user = f"@{user.username}" if user.username else user.first_name
    await context.bot.send_message(ADMIN_ID, f"[Support] from {tg_user} (id={user.id}):\n{update.message.text}")
    await context.bot.send_message(ADMIN_ID,f"/reply {user.id} <ответ>")
    await update.message.reply_text("Ваше сообщение отправлено администратору.\nОжидайте ответ(Не более 2 суток).")
    context.user_data["awaiting_support"] = False


# ─── ADMIN COMMANDS ─────────────────────────────────
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_ID not in (update.effective_user.id, update.effective_chat.id):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /reply <tg_id> <текст>")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Первый аргумент должен быть числовым Telegram-ID.")
        return

    answer = " ".join(context.args[1:])
    await context.bot.send_message(chat_id=target, text=f"💬 Ответ поддержки:\n{answer}")
    await update.message.reply_text(f"Ответ отправлен пользователю {target}.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_ID not in (update.effective_user.id, update.effective_chat.id):
        return

    total, paid, money = global_stats()

    refcnt   = referral_counts()
    leaders  = sorted(refcnt.items(), key=lambda x: x[1], reverse=True)[:5]
    ref_lines = [
        f"{i+1}. <code>{uid}</code> — {cnt}"
        for i, (uid, cnt) in enumerate(leaders)
    ] or ["-"]

    percent = f"{paid/total*100:.1f}%" if total else "0%"

    text = (
        "📊 <b>Общая статистика</b>\n"
        f"• Пользователей всего: <b>{total}</b>\n"
        f"• Оплатили: <b>{paid}</b> ({percent})\n"
        f"• Сумма платежей: <b>{money} ₽</b>\n"
        f"• <u>ТОП-5 рефералов</u> (по числу приглашённых):\n" + "\n".join(ref_lines)
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML")


async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_ID not in (update.effective_user.id, update.effective_chat.id):
        return

    # 1) достаём
    limit = int(context.args[0]) if context.args else 20
    rows  = fetch_users(limit)
    refs  = referral_counts()

    # 2) подготавливаем телеграм-юзеров для юзнеймов
    chats = await asyncio.gather(*(context.bot.get_chat(r[0]) for r in rows))
    users = {c.id: c for c in chats}

    # 3) собираем табличные строки
    data = []
    for tg_id, role, paid, price, parent, inst, joined in rows:
        uname    = users[tg_id].username or "-"
        inst     = inst or "-"
        parent   = str(parent) if parent else "-"
        children = refs.get(tg_id, 0)
        joined   = joined.replace("T", " ")[:19]
        data.append((
            tg_id,
            uname,
            inst,
            role,
            paid,
            price or "-",
            parent,
            children,
            joined
        ))

    # 4) заголовки
    headers = ["TG_ID", "USER", "INST", "ROLE", "PAID", "PRICE", "PARENT", "REFS", "JOINED"]
    text    = fmt_table(data, headers)

    # 5) шлём
    await send_long(context.bot, ADMIN_ID, text)




async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_ID not in (update.effective_user.id, update.effective_chat.id):
        return
    if len(context.args) != 1:
        return

    try:
        tgt = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("ID должен быть числом.")

    row = fetch_user_detail(tgt)
    if not row:
        return await update.message.reply_text("Пользователь не найден.")

    (
        tg_id,
        ref_code,
        parent_id,
        wallet,
        role,
        inst_nick,
        price_offer,
        paid,
        subs_ok,
        joined_at,
    ) = row

    chat = await context.bot.get_chat(tgt)
    username = f"@{chat.username}" if chat.username else chat.first_name
    children = referral_counts().get(tgt, 0)
    joined = joined_at.replace("T", " ")[:19]

    text = (
        f"👤 <u>Профиль пользователя <code>{tg_id}</code></u>\n"
        f"<b>Username</b>: {username}\n"
        f"<b>Instagram</b>: {inst_nick or '-'}\n"
        f"<b>Role</b>: {role}\n"
        f"<b>Paid</b>: {paid}\n"
        f"<b>Price</b>: {price_offer or '-'}\n"
        f"<b>Parent</b>: {parent_id or '-'}\n"
        f"<b>Referrals</b>: {children}\n"
        f"<b>Joined</b>: {joined}"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="HTML")




async def set_field_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_ID not in (update.effective_user.id, update.effective_chat.id):
        return
    try:
        tgt = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("tg_id должен быть числом.")
    field, value = context.args[1], " ".join(context.args[2:])
    try:
        set_user_field(tgt, field, value)
        await update.message.reply_text("OK")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def add_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_ID not in (update.effective_user.id, update.effective_chat.id):
        return
    try:
        tgt = int(context.args[0]); amt = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("Usage: /add_payment <tg_id> <amount>")
    store_payment(tgt, amt)
    set_user_field(tgt, "paid", 1)
    await update.message.reply_text("Записал. ✅")


async def detect_video_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_ID not in (update.effective_user.id, update.effective_chat.id):
        return

    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 Video file_id: <code>{file_id}</code>", parse_mode="HTML")

async def detect_message_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_ID not in (update.effective_user.id, update.effective_chat.id):
        return

    if update.message:
        file_id = update.message.message_id
        await update.message.reply_text(f"🎬 Video file_id: <code>{file_id}</code>", parse_mode="HTML")
    # Берём ID сообщения и чата
    msg_id  = update.message.message_id
    chat_id = update.effective_chat.id

    # Отправляем как HTML, чтобы было удобно копировать
    await update.message.reply_html(
        f"📌 <b>Chat ID</b>: <code>{chat_id}</code>\n"
        f"✉️ <b>Message ID</b>: <code>{msg_id}</code>"
    )


# ─────────────────── MAIN ────────────────────────────────────────────────────
def main() -> None:
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("price",   price_command))
    app.add_handler(CommandHandler("reply",   admin_reply))
    app.add_handler(CommandHandler("stats",   stats_command))
    app.add_handler(CommandHandler("list",   list_users_command))
    app.add_handler(CommandHandler("user",         user_command))
    app.add_handler(CommandHandler("set_field",    set_field_command))
    app.add_handler(CommandHandler("add_payment",  add_payment_command))
   
    app.add_handler(CallbackQueryHandler(intro_done,    pattern="^intro_done$"))
    app.add_handler(CallbackQueryHandler(choose_role,   pattern="^role_"))
    app.add_handler(CallbackQueryHandler(notify_payment,pattern="^notify_payment$"))
    app.add_handler(CallbackQueryHandler(confirm_payment,pattern="^confirm_\\d+$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram_nick), group=0)

    app.add_handler(MessageHandler(filters.Regex("^ℹ️"), about_project), group=1)
    app.add_handler(MessageHandler(filters.Regex("^👋"), want_join),    group=1)
    app.add_handler(MessageHandler(filters.Regex("^(📞 Поддержка|👥 Реферальная ссылка|📊 Статистика)$"), handle_menu), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, support_message), group=1)
    #app.add_handler(MessageHandler(filters.VIDEO & ~filters.COMMAND, detect_video_id),group=1)
    #app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, detect_message_id),group=2)
    
    
    logger.info("Bot polling…")
    app.run_polling()


if __name__ == "__main__":
    main()