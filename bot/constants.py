from typing import List
from enum import Enum

class Role(str, Enum):
    UNREGISTERED = "unregistered"  # Начальное состояние
    NEW_PENDING = "new_pending"    # Выбрал "Новичок", но еще не оплатил
    NEW = "new"                    # Новичок после оплаты
    OLD_PENDING = "old_pending"    # Выбрал "Старичок", ждет одобрения
    OLD = "old"                    # Старичок после одобрения/оплаты

class CallbackData(str, Enum):
    INTRO_DONE = "intro_done"
    ROLE_NEW = "role_new"
    ROLE_OLD = "role_old"
    NOTIFY_PAYMENT = "notify_payment"
    CONFIRM_PAYMENT = "confirm_{user_id}"

# Telegram Media File IDs
IMAGE_FILE_IDS: List[str] = [
    "AgACAgIAAxkDAANhaHL6D6ottuienNw3_MHYheuHs1gAAu8EMhsC0phLe3Xuf69LDzcBAAMCAAN3AAM2BA",
    "AgACAgIAAxkDAANiaHL6DwnIm9XCAAG2sfPEWPZlR0dNAALwBDIbAtKYS4KD2bYx6_7ZAQADAgADdwADNgQ",
    "AgACAgIAAxkDAANjaHL6ED8t9XdCcZx4soJLgomntnsAAvEEMhsC0phLi4NqOQ5LOa8BAAMCAAN3AAM2BA",
    "AgACAgIAAxkDAANkaHL6EX4jVXdCrrqSMEfdisCFb9AAAvIEMhsC0phLOuMcY0CfGUABAAMCAAN3AAM2BA",
    "AgACAgIAAxkDAANlaHL6EaaiBBKuNTneGnxoHGeowdMAAvMEMhsC0phLO5-sUli9yAABAQADAgADdwADNgQ",
    "AgACAgIAAxkDAANmaHL6EgpBeNKLnu7gAAGr86_R6SJpAAL0BDIbAtKYS8gs1elZLtgbAQADAgADdwADNgQ",
    "AgACAgIAAxkDAANnaHL6E2TQXz-C0Cy6JDrsCmPpYYcAAvUEMhsC0phLI2oq0bT_vAwBAAMCAAN3AAM2BA",
    "AgACAgIAAxkDAANoaHL6FLc-HKp24UX76Kf-BMX25P0AAvYEMhsC0phLe5K4v70ahjwBAAMCAAN3AAM2BA"
]

VIDEO_FILE_ID: str = "BAACAgIAAxkBAAIRwmh7eaB8DOZX1be68Hkhqeikt_JWAALYeAACKF3gSwjj1H5O3kk5NgQ"
YELLOW_FILE_ID: str = "AgACAgIAAxkDAAIC4mh6Ddsy9-s3rxNnkweC4LPkNwMsAAJW7zEb5E7QS7m4drmHEFyZAQADAgADdwADNgQ"

# About section constants
ABOUT_CHAT_ID: int = 918767042
ABOUT_MESSAGE_ID: int = 4646

# Menu command prefixes
BAD_PREFIXES: tuple = ("ℹ️", "👋", "📞", "👥", "📊")