from pydantic import Field
from pydantic_settings import BaseSettings
from pathlib import Path

class Config(BaseSettings):
    BOT_TOKEN: str = Field(..., env="BOT_TOKEN")
    ADMIN_ID: int = Field(..., env="ADMIN_ID")
    CARD_NUMBER: str = Field("0000 0000 0000 0000", env="CARD_NUMBER")
    PRICE_RUB: int = Field(1000, env="PRICE_RUB")
    SMALL_PRICE_RUB: int = Field(default=None)
    DB_PATH: Path = Path(__file__).resolve().parent / "bot.db"

    class Config:
        env_file = ".env"

cfg = Config()

cfg.SMALL_PRICE_RUB = cfg.PRICE_RUB // 2
