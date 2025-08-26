from __future__ import annotations
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import os
import hmac
import hashlib
import json
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Request, status
from telegram import Bot

from bot.domain.services.onboarding_service import send_instruction_package
from bot.domain.services import user_service
from bot.db.repository.subscription_repo import SubscriptionRepo
from bot.domain.services.payment_service import PaymentService

BOT_TOKEN           = os.getenv("TOKEN")
ADMIN_ID            = int(os.getenv("ADMIN_ID", "0"))
LAVA_WEBHOOK_SECRET = os.getenv("LAVA_WEBHOOK_SECRET")
DB_PATH             = os.getenv("DB_PATH", "data/bot.sqlite3")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")
if not LAVA_WEBHOOK_SECRET:
    raise RuntimeError("LAVA_WEBHOOK_SECRET не задан в .env")

app = FastAPI(title="Lava webhook backend")
bot = Bot(BOT_TOKEN)

repo: SubscriptionRepo
psvc: PaymentService

@app.on_event("startup")
async def startup_event():
    global repo, psvc
    repo = await SubscriptionRepo.open(DB_PATH)
    psvc = PaymentService(repo)


def verify_signature(secret: str, body: bytes, header_sig: str) -> bool:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, header_sig)

@app.post("/lava/webhook", status_code=200)
async def lava_webhook(
    request: Request,
    x_lava_signature: Annotated[str, Header(alias="X-Lava-Signature")],
):
    body = await request.body()

    if not verify_signature(LAVA_WEBHOOK_SECRET, body, x_lava_signature):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON body")

    if payload.get("status") != "success":
        return {"ok": True}
    try:
        user_id = await psvc.confirm_payment(payload)
    except Exception as e:
        print("[webhook] confirm_payment error:", e)
        return {"ok": False}

    try:
        await bot.send_message(user_id, "✅ Платёж прошёл! Доступ активирован.")
        await send_instruction_package(bot, user_id)

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
