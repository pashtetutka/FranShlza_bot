from pydantic_settings import BaseSettings
from pathlib import Path

class BotConfig(BaseSettings):
    TOKEN: str
    ADMIN_ID: int
    CARD_NUMBER: str = "0000 0000 0000 0000"
    PRICE_RUB: int = 1000
    DB_PATH: Path = Path(__file__).parent / "bot.db"  # Изменено на локальный путь

    class Config:
        env_prefix = "BOT_"
        env_file = Path(__file__).parent / ".env"  # Обновлен путь к .env
        case_sensitive = True
        extra = "allow"  # Allow extra fields in .env

settings = BotConfig()
