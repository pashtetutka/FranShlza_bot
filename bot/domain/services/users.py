from typing import Optional, List, Tuple
from bot.db.repository.user_repo import UserRepository
from bot.constants import Role

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def register(self, tg_id: int, ref_code: Optional[str] = None) -> None:
        self.repo.upsert(tg_id, ref_code)

    def set_role(self, tg_id: int, role: Role) -> None:
        self.repo.update_role(tg_id, role)

    def get_role(self, tg_id: int) -> Optional[Role]:
        return self.repo.get_role(tg_id)

    def set_field(self, tg_id: int, field: str, value) -> None:
        self.repo.set_field(tg_id, field, value)

    def get(self, tg_id: int) -> Optional[Tuple]:
        return self.repo.get(tg_id)

    def list(self, limit: int = 20, offset: int = 0) -> List[Tuple]:
        return self.repo.list(limit, offset)

    def referrals(self, tg_id: int) -> List[int]:
        return self.repo.referrals(tg_id)

    def referral_counts(self) -> dict[int, int]:
        return self.repo.referral_counts()
