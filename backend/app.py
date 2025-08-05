from __future__ import annotations
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
"""
Запуск локально:
    python -m uvicorn backend.app:app --reload --port 8000
"""
import os
import hmac
import hashlib
import json
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Request, status
from telegram import Bot

from bot.constants import YELLOW_FILE_ID, VIDEO_FILE_ID
from bot.keyboards import MENU_KB
from bot.domain.services import user_service
from bot.db.repository.subscription_repo import SubscriptionRepo
from bot.domain.services.payment_service import PaymentService



# ── Конфиг из .env ──────────────────────────────────────────────────────────────
BOT_TOKEN           = os.getenv("TOKEN")
ADMIN_ID            = int(os.getenv("ADMIN_ID", "0"))
LAVA_WEBHOOK_SECRET = os.getenv("LAVA_WEBHOOK_SECRET")
DB_PATH             = os.getenv("DB_PATH", "data/bot.sqlite3")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")
if not LAVA_WEBHOOK_SECRET:
    raise RuntimeError("LAVA_WEBHOOK_SECRET не задан в .env")

# ── Приложение и Телеграм-бот ───────────────────────────────────────────────────
app = FastAPI(title="Lava webhook backend")
bot = Bot(BOT_TOKEN)

# ── Глобальные переменные (инициализируются в startup) ─────────────────────────
repo: SubscriptionRepo
psvc: PaymentService

# ── Инициализация при старте сервера ─────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    global repo, psvc
    repo = await SubscriptionRepo.open(DB_PATH)
    psvc = PaymentService(repo)

# ── Хелпер для проверки подписи ─────────────────────────────────────────────────

def verify_signature(secret: str, body: bytes, header_sig: str) -> bool:
    """Проверка подписи Lava через HMAC-SHA256"""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, header_sig)

# ── Webhook endpoint ───────────────────────────────────────────────────────────
@app.post("/lava/webhook", status_code=200)
async def lava_webhook(
    request: Request,
    x_lava_signature: Annotated[str, Header(alias="X-Lava-Signature")],
):
    # Читаем body как bytes для проверки подписи
    body = await request.body()

    # 1) Проверка подписи
    if not verify_signature(LAVA_WEBHOOK_SECRET, body, x_lava_signature):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid signature")

    # 2) Парсинг JSON
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON body")

    # 3) Обрабатываем только успешные платежи
    if payload.get("status") != "success":
        return {"ok": True}

    # 4) Помечаем в БД и получаем user_id
    try:
        user_id = await psvc.confirm_payment(payload)
    except Exception as e:
        # Логируем и возвращаем 200, чтобы Lava не делала повторные пинги
        print("[webhook] confirm_payment error:", e)
        return {"ok": False}

    # 5) Уведомляем в Telegram
    try:
        await bot.send_message(user_id, "✅ Платёж прошёл! Доступ активирован.")
        await bot.send_photo(chat_id=user_id, photo=YELLOW_FILE_ID)
        await bot.send_message(
        chat_id=user_id,
        text=(
            "Итак, первым делом тебе нужно создать новый профиль в Instagram — это наш фундамент.\n\n"
            "Аватар — возьми мой жёлтый цвет (см. фото выше). Позже, достигнув целей, "
            "сможешь заменить аватар на свой.\n\n"
            "Имя профиля — сделай понятным, связанным с нашим контентом (например, @creatorofmotivation).\n"
            "Описание — добавь «упаковку» (пример: заряжайся мотивацией каждый день).\n\n"
            "И последнее — переключи аккаунт с личного на профессиональный, чтобы видеть статистику. "
            "Нажми кнопку ниже, чтобы получить инструкцию."
            ),
        reply_markup=MENU_KB,
        )
        await bot.send_video(chat_id=user_id, video=VIDEO_FILE_ID)

        tg_user = f"[{user_id}](tg://user?id={user_id})"
        if ADMIN_ID:
            await bot.send_message(
            ADMIN_ID,
            f"✅ Платёж от пользователя {tg_user} подтверждён Lava.",
            parse_mode="Markdown",
        )
    except Exception as e:
        print("[webhook] telegram notification error:", e)

    return {"ok": True}
