from bot.db.repository.user_repo import UserRepository

class ReferralService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def top(self, n: int = 5) -> list[tuple[int, int]]:
        data = self.repo.referral_counts()
        return sorted(data.items(), key=lambda x: x[1], reverse=True)[:n]
