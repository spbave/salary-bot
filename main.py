import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import cmd_start, process_month, process_salary
from bot.states import SalaryState
from core.config import BOT_TOKEN
from core.db import init_db

logging.basicConfig(level=logging.INFO)

dp = Dispatcher(storage=MemoryStorage())

dp.message(Command("start"))(cmd_start)
dp.message(SalaryState.month_input)(process_month)
dp.message(SalaryState.salary_input)(process_salary)


async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())