from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.states import SalaryState
from core.config import CURRENT_YEAR
from core.db import get_or_create_user, save_salary_periods, save_calculation
from services.calculator import parse_salary_periods, calculate_results


async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    await message.answer(
        "Привет! Я бот для расчёта аванса и остатка зарплаты с учётом НДФЛ.\n\n"
        "Отправь номер месяца (1–12) или '1-12' для расчёта за весь год."
    )
    await state.set_state(SalaryState.month_input)


async def process_month(message: types.Message, state: FSMContext):
    month_input = message.text.strip()

    if month_input == "1-12":
        months_to_show = list(range(1, 13))
        full_year_mode = True
    else:
        try:
            month = int(month_input)
            if 1 <= month <= 12:
                months_to_show = [month]
                full_year_mode = False
            else:
                await message.answer("Номер месяца должен быть от 1 до 12. Попробуй ещё раз.")
                return
        except ValueError:
            await message.answer("Введите корректный номер месяца (1–12) или '1-12'.")
            return

    await state.update_data(months_to_show=months_to_show, full_year_mode=full_year_mode)
    await message.answer(
        "Теперь введи зарплату (до вычета налогов).\n\n"
        "Примеры:\n"
        "442000 — одна зарплата на весь год\n"
        "1-5:422000;6-12:442000 — с января по май 422000, с июня по декабрь 442000"
    )
    await state.set_state(SalaryState.salary_input)


async def process_salary(message: types.Message, state: FSMContext):
    salary_input = message.text.strip()
    data = await state.get_data()
    months_to_show = data["months_to_show"]
    full_year_mode = data["full_year_mode"]

    salary_by_month = parse_salary_periods(salary_input)
    if salary_by_month is None:
        await message.answer(
            "Некорректный формат ввода зарплаты. Попробуй ещё раз в таком виде:\n"
            "442000\n"
            "или\n"
            "1-5:422000;6-12:442000"
        )
        return

    user_id = get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    save_salary_periods(user_id, salary_by_month, CURRENT_YEAR)

    results = calculate_results(months_to_show, salary_by_month)

    if full_year_mode:
        lines = ["Результат за весь год (Месяц, аванс после вычета налогов, остаток зп после вычета налогов):"]
        for m in months_to_show:
            res = results[m]
            lines.append(f"{res['month_name']}, {res['advance_net']:,.2f} ₽, {res['remainder_net']:,.2f} ₽")

            save_calculation(
                user_id=user_id,
                month=m,
                year=CURRENT_YEAR,
                salary=salary_by_month[m],
                advance_net=res["advance_net"],
                remainder_net=res["remainder_net"],
                advance_gross=res["advance_gross"],
                remainder_gross=res["remainder_gross"],
                ndfl_advance=res["ndfl_advance"],
                ndfl_remainder=res["ndfl_remainder"],
            )

        await message.answer("\n".join(lines))
    else:
        m = months_to_show[0]
        res = results[m]
        text = (
            f"Результат:\n"
            f"Месяц: {res['month_name']}\n"
            f"Аванс после вычета налогов: {res['advance_net']:,.2f} ₽\n"
            f"Остаток зарплаты после вычета налога: {res['remainder_net']:,.2f} ₽"
        )
        await message.answer(text)

        save_calculation(
            user_id=user_id,
            month=m,
            year=CURRENT_YEAR,
            salary=salary_by_month[m],
            advance_net=res["advance_net"],
            remainder_net=res["remainder_net"],
            advance_gross=res["advance_gross"],
            remainder_gross=res["remainder_gross"],
            ndfl_advance=res["ndfl_advance"],
            ndfl_remainder=res["ndfl_remainder"],
        )

    await state.clear()
    await message.answer(
        "Если нужно, могу посчитать ещё раз. Отправь /start для нового расчёта."
    )
