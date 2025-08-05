from datetime import date, timedelta
from typing import Optional

from bot.integration.lava.client import create_invoice
from bot.db.repository.subscription_repo import SubscriptionRepo


class PaymentService:

    def __init__(self, repo: SubscriptionRepo):
        self.repo = repo

    async def start_subscription(
        self,
        user_id: int,
        email: str,
        offer_id: str,
        currency: str = "RUB",
        payment_method: Optional[str] = None,
        periodicity: Optional[str] = None,
    ) -> str:
        payment_url = await create_invoice(
            email=email,
            offer_id=offer_id,
            currency=currency,
            payment_method=payment_method,
            periodicity=periodicity,
        )

        await self.repo.create_pending(
            user_id=user_id,
            email=email,
            payment_url=payment_url,
            periodicity=periodicity,
        )
        return payment_url

    async def confirm_payment(self, payload: dict) -> int:
        user_id = int(payload["metadata"]["tg_id"])
        started_at = date.today()
        expired_at: Optional[date] = None
        period = payload.get("periodicity")
        if period:
            days_map = {"PERIOD_30_DAYS": 30, "PERIOD_90_DAYS": 90}
            if period in days_map:
                expired_at = started_at + timedelta(days=days_map[period])

        await self.repo.mark_paid(
            user_id=user_id,
            started_at=started_at,
            expired_at=expired_at,
        )
        return user_id
