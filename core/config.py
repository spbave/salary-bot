import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CURRENT_YEAR = int(os.getenv("CURRENT_YEAR", "2026"))
DB_FILE = os.getenv("DB_FILE", "salary_bot.db")
