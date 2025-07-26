from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from bot.constants import Role


@dataclass(slots=True)
class User:
    tg_id: int
    ref_code: Optional[str]
    referrer_id: Optional[int]
    wallet: Optional[str]
    role: Role
    inst_nick: Optional[str]
    price_offer: Optional[int]
    paid: int
    subs_ok: int
    joined_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "User":
        return cls(
            tg_id=row[0],
            ref_code=row[1],
            referrer_id=row[2],
            wallet=row[3],
            role=Role(row[4]),
            inst_nick=row[5],
            price_offer=row[6],
            paid=row[7],
            subs_ok=row[8],
            joined_at=datetime.fromisoformat(row[9]),
        )


@dataclass(slots=True)
class Payment:
    id: int
    tg_id: int
    amount: int
    paid_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "Payment":
        return cls(
            id=row[0],
            tg_id=row[1],
            amount=row[2],
            paid_at=datetime.fromisoformat(row[3]),
        )
