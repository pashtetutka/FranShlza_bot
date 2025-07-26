from bot.db.repository.user_repo import UserRepository
from bot.db.repository.payment_repo import PaymentRepository
from .users import UserService
from .payments import PaymentService
from .referral import ReferralService

_user_repo = UserRepository()
_payment_repo = PaymentRepository()

user_service = UserService(_user_repo)
payment_service = PaymentService(_payment_repo, _user_repo)
referral_service = ReferralService(_user_repo)

__all__ = ["user_service", "payment_service", "referral_service"]
