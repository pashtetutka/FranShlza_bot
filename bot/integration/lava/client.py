from __future__ import annotations
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, EmailStr, Field, ValidationError, model_validator

# ── Константы / конфиг ──────────────────────────────────────────────────────────
LAVA_API_BASE = os.getenv("LAVA_API_BASE", "https://gate.lava.top").rstrip("/")
API_KEY       = os.getenv("LAVA_SHOP_API_KEY", "")
DEFAULT_LANG  = os.getenv("LAVA_LANG", "RU")
DEFAULT_UTM   = {"utm_source": "telegram_bot"}

if not API_KEY:
    raise RuntimeError("LAVA_SHOP_API_KEY is not задан в .env")

# ── Типы данных ─────────────────────────────────────────────────────────────────
Currency      = Literal["RUB", "USD", "EUR"]
PaymentMethod = Literal["BANK131", "UNLIMINT", "PAYPAL", "STRIPE"]

class InvoiceRequest(BaseModel):
    email:         EmailStr
    offerId:       str = Field(..., description="ID тарифа/подписки")
    currency:      Currency
    paymentMethod: PaymentMethod
    buyerLanguage: str                = Field(DEFAULT_LANG, description="Язык писем")
    clientUTM:     dict[str, str]     = Field(DEFAULT_UTM, description="UTM-метки")
    periodicity:   Optional[str]      = Field(None, description="Напр. 'PERIOD_30_DAYS'")

    @model_validator(mode='after')
    def check_method_vs_currency(cls, values):  # noqa: N805
        m2c = {
            "BANK131":  {"RUB"},
            "UNLIMINT": {"USD", "EUR"},
            "PAYPAL":   {"USD", "EUR"},
            "STRIPE":   {"USD", "EUR"},
        }
        pm = values.paymentMethod
        curr = values.currency
        if curr not in m2c.get(pm, {}):
            raise ValueError(f"{pm} не поддерживает валюту {curr}")
        return values

# ── Клиент ──────────────────────────────────────────────────────────────────────
_headers = {
    "X-Api-Key":   API_KEY,
    "Content-Type": "application/json",
    "Accept":       "application/json",
}

async def create_invoice(
    *,
    email: str,
    offer_id: str,
    currency: Currency = "RUB",
    payment_method: Optional[PaymentMethod] = None,
    buyer_language: str = DEFAULT_LANG,
    periodicity: Optional[str] = None,
    client_utm: Optional[dict[str, str]] = None,
) -> str:
    if payment_method is None:
        payment_method = "BANK131" if currency == "RUB" else "UNLIMINT"

    req = InvoiceRequest(
        email=email,
        offerId=offer_id,
        currency=currency,
        paymentMethod=payment_method,
        buyerLanguage=buyer_language,
        clientUTM=client_utm or DEFAULT_UTM,
        periodicity=periodicity,
    )

    url = f"{LAVA_API_BASE}/api/v2/invoice"
    async with httpx.AsyncClient(base_url=LAVA_API_BASE, timeout=10) as cli:
        r = await cli.post(url, json=req.model_dump(exclude_none=True), headers=_headers)
        r.raise_for_status()

        data = r.json()
        payment_url = data.get("paymentUrl") or data.get("payment_url")
        if not payment_url:
            raise RuntimeError("paymentUrl не найден в ответе Lava")
        return payment_url

if __name__ == "__main__":
    import asyncio, sys, textwrap, argparse

    parser = argparse.ArgumentParser("Test Lava invoice creation")
    parser.add_argument("--email", required=True)
    parser.add_argument("--offer-id", required=True)
    parser.add_argument("--currency", default="RUB")
    args = parser.parse_args()

    try:
        url = asyncio.run(
            create_invoice(
                email=args.email,
                offer_id=args.offer_id,
                currency=args.currency,
            )
        )
        print("Payment URL:", url)
    except Exception as e:
        sys.exit(textwrap.fill(f"Ошибка: {e}", 80))
