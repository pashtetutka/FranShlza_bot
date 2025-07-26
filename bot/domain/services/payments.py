from bot.db.repository.payment_repo import PaymentRepository
from bot.db.repository.user_repo import UserRepository
from bot.constants import Role

class PaymentService:
    def __init__(self, pay_repo: PaymentRepository, user_repo: UserRepository):
        self.pay_repo = pay_repo
        self.user_repo = user_repo

    def store(self, tg_id: int, amount: int) -> None:
        self.pay_repo.store(tg_id, amount)

    def confirm_pending(self, tg_id: int, new_role: Role, amount: int) -> None:
        self.pay_repo.store(tg_id, amount)
        self.user_repo.update_role(tg_id, new_role)

    def global_stats(self) -> tuple[int, int, int]:
        return self.pay_repo.global_stats()
