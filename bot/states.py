from aiogram.fsm.state import StatesGroup, State


class SalaryState(StatesGroup):
    month_input = State()
    salary_input = State()