from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_ID: int
    CARD_NUMBER: str = "0000 0000 0000 0000"
    PRICE_RUB: int = 1000
    SMALL_PRICE_RUB: int = 500
    DB_PATH: str = str(Path(__file__).parent / "bot.db")
    
    IMAGE_FILE_IDS: List[str] = [
        "AgACAgIAAxkDAANhaHL6D6ottuienNw3_MHYheuHs1gAAu8EMhsC0phLe3Xuf69LDzcBAAMCAAN3AAM2BA",
        "AgACAgIAAxkDAANiaHL6DwnIm9XCAAG2sfPEWPZlR0dNAALwBDIbAtKYS4KD2bYx6_7ZAQADAgADdwADNgQ",
        "AgACAgIAAxkDAANjaHL6ED8t9XdCcZx4soJLgomntnsAAvEEMhsC0phLi4NqOQ5LOa8BAAMCAAN3AAM2BA",
        "AgACAgIAAxkDAANkaHL6EX4jVXdCrrqSMEfdisCFb9AAAvIEMhsC0phLOuMcY0CfGUABAAMCAAN3AAM2BA",
        "AgACAgIAAxkDAANlaHL6EaaiBBKuNTneGnxoHGeowdMAAvMEMhsC0phLO5-sUli9yAABAQADAgADdwADNgQ",
        "AgACAgIAAxkDAANmaHL6EgpBeNKLnu7gAAGr86_R6SJpAAL0BDIbAtKYS8gs1elZLtgbAQADAgADdwADNgQ",
        "AgACAgIAAxkDAANnaHL6E2TQXz-C0Cy6JDrsCmPpYYcAAvUEMhsC0phLI2oq0bT_vAwBAAMCAAN3AAM2BA",
        "AgACAgIAAxkDAANoaHL6FLc-HKp24UX76Kf-BMX25P0AAvYEMhsC0phLe5K4v70ahjwBAAMCAAN3AAM2BA",
    ]
    VIDEO_FILE_ID: str = "BAACAgIAAxkBAAIRwmh7eaB8DOZX1be68Hkhqeikt_JWAALYeAACKF3gSwjj1H5O3kk5NgQ"
    YELLOW_FILE_ID: str = "AgACAgIAAxkDAAIC4mh6Ddsy9-s3rxNnkweC4LPkNwMsAAJW7zEb5E7QS7m4drmHEFyZAQADAgADdwADNgQ"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in .env that aren't defined in the model
