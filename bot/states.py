from aiogram.fsm.state import StatesGroup, State


class SalaryState(StatesGroup):
    month_input = State()
    salary_change_input = State()
    change_month_input = State()
    old_salary_input = State()
    new_salary_input = State()
    salary_input = State()
