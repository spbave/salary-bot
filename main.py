import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import (
    cmd_start,
    process_month,
    process_salary_change,
    process_change_month,
    process_old_salary,
    process_new_salary,
    process_salary,
    cmd_stats,
    cmd_edit,
)
from bot.states import SalaryState
from core.config import BOT_TOKEN
from core.db import init_db

logging.basicConfig(level=logging.INFO)

dp = Dispatcher(storage=MemoryStorage())

# Команда /start
dp.message(Command("start"))(cmd_start)
dp.message(Command("stats"))(cmd_stats)
dp.message(Command("edit"))(cmd_edit)

# Хендлер для кнопки "Рассчитать ещё раз" (без состояния)
dp.message(lambda msg: msg.text == "Рассчитать ещё раз🔄")(cmd_start)

# Остальные хендлеры с состоянием
dp.message(StateFilter(SalaryState.month_input))(process_month)
dp.message(StateFilter(SalaryState.salary_change_input))(process_salary_change)
dp.message(StateFilter(SalaryState.change_month_input))(process_change_month)
dp.message(StateFilter(SalaryState.old_salary_input))(process_old_salary)
dp.message(StateFilter(SalaryState.new_salary_input))(process_new_salary)
dp.message(StateFilter(SalaryState.salary_input))(process_salary)


async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())