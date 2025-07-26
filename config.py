import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "0000 0000 0000 0000")
PRICE_RUB = int(os.getenv("PRICE_RUB", "1000"))
SMALL_PRICE_RUB = int(os.getenv("SMALL_PRICE_RUB", str(PRICE_RUB // 2)))
DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")
