from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.keyboards import (
    get_month_keyboard,
    get_salary_change_keyboard,
    get_change_month_keyboard,
    get_calculation_keyboard,
    MONTH_NAMES,
)
from bot.states import SalaryState
from core.config import CURRENT_YEAR
from core.db import get_or_create_user, save_salary_periods, save_calculation, update_user_last_salary, \
    get_user_last_salary
from services.calculator import parse_salary_periods, calculate_results

# Маппинг названия месяца в номер
MONTH_NAME_TO_NUM = {name: num for num, name in enumerate(MONTH_NAMES, 1)}


def get_ndfl_progress_message(cumulative_income: float) -> str:
    """
    Возвращает сообщение о прогрессе до следующего порога НДФЛ.
    """
    brackets = [
        (2_400_000, "15%"),
        (5_000_000, "18%"),
        (20_000_000, "20%"),
        (50_000_000, "22%"),
    ]

    messages = []

    # Определяем текущую ставку
    current_rate = "13%"
    for limit, rate in brackets:
        if cumulative_income >= limit:
            current_rate = rate
        else:
            break

    messages.append(f"\n\n📊 Текущая ставка НДФЛ: {current_rate}")

    # Показываем следующий порог
    for limit, rate in brackets:
        if cumulative_income < limit:
            remaining = limit - cumulative_income
            messages.append(f"До порога НДФЛ {rate} осталось {remaining:,.0f} ₽")
            break

    return "\n".join(messages)


async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    # Добавляем пользователя в БД сразу после /start
    user_id = get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    # Проверяем, есть ли сохранённая зарплата
    last_salary = get_user_last_salary(user_id)

    # Проверяем, это команда /start или кнопка "Рассчитать ещё раз"
    is_command_start = message.text == "/start"

    if last_salary and last_salary.get("last_salary_input"):
        # Предлагаем использовать последнюю зарплату
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text=f"✅ Использовать {last_salary['last_salary_input']} ₽")],
                [types.KeyboardButton(text="✏️ Ввести новую зарплату")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

        if is_command_start:
            # Полное приветствие для /start
            await message.answer(
                "Привет!\n"
                "Я бот для расчёта аванса и зарплаты.\n\n"
                "У меня есть твои последние данные о зарплате.\n"
                "Хочешь использовать их?\n\n"
                "Выбери месяц для расчёта или нажми 'Весь год📅':",
                reply_markup=keyboard
            )
        else:
            # Короткое сообщение для кнопки "Рассчитать ещё раз"
            await message.answer(
                "У меня есть твои последние данные о зарплате.\n"
                "Хочешь использовать их?\n\n"
                "Выбери месяц для расчёта или нажми 'Весь год📅':",
                reply_markup=keyboard
            )
    else:
        if is_command_start:
            # Полное приветствие для /start
            await message.answer(
                "Привет!\n"
                "Я бот для расчёта аванса и зарплаты.\n\n"
                "Выбери месяц для расчёта или нажми 'Весь год📅':",
                reply_markup=get_month_keyboard()
            )
        else:
            # Короткое сообщение для кнопки "Рассчитать ещё раз"
            await message.answer(
                "Выбери месяц для расчёта или нажми 'Весь год📅':",
                reply_markup=get_month_keyboard()
            )

    await state.set_state(SalaryState.month_input)


async def process_month(message: types.Message, state: FSMContext):
    month_input = message.text.strip()

    # Если нажали кнопку "Использовать последнюю зарплату"
    if message.text and message.text.startswith("✅ Использовать"):
        # Извлекаем сумму из текста кнопки
        salary_amount = message.text.split()[-1].replace("₽", "").strip()
        # Убираем ".0" если есть
        if salary_amount.endswith(".0"):
            salary_amount = salary_amount[:-2]
        await state.update_data(use_last_salary=True, last_salary_amount=salary_amount)
        # Сразу переходим к расчёту с последней зарплатой
        await process_salary(message, state, salary_input=salary_amount)
        return

    # Если нажали кнопку "Ввести новую зарплату"
    if message.text == "✏️ Ввести новую зарплату":
        await message.answer(
            "Выбери месяц для расчёта или нажми 'Весь год📅':",
            reply_markup=get_month_keyboard()
        )
        await state.set_state(SalaryState.month_input)
        return

    # Обработка кнопки "Весь год"
    if month_input == "Весь год📅":
        months_to_show = list(range(1, 13))
        full_year_mode = True
    else:
        # Преобразуем название месяца в номер
        if month_input in MONTH_NAME_TO_NUM:
            month = MONTH_NAME_TO_NUM[month_input]
            months_to_show = [month]
            full_year_mode = False
        else:
            await message.answer("Выберите месяц из клавиатуры или нажмите 'Весь год📅'.")
            return

    await state.update_data(months_to_show=months_to_show, full_year_mode=full_year_mode)

    # Спрашиваем, менялась ли зарплата
    await message.answer(
        "Зарплата менялась в течение года?",
        reply_markup=get_salary_change_keyboard()
    )
    await state.set_state(SalaryState.salary_change_input)


async def process_salary_change(message: types.Message, state: FSMContext):
    data = await state.get_data()

    # Если пользователь выбрал "Использовать последнюю зарплату" — сразу считаем
    if data.get("use_last_salary"):
        salary_amount = data.get("last_salary_amount")
        salary_input = salary_amount
        await process_salary(message, state, salary_input=salary_input)
        return

    change_input = message.text.strip()

    if change_input == "Нет❌":
        await message.answer(
            "Введи зарплату (до вычета НДФЛ)",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="✏️ Ввести вручную")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
        )
        await state.set_state(SalaryState.salary_input)

    elif change_input == "Да✅":
        # Спрашиваем месяц изменения зарплаты
        await message.answer(
            "В каком месяце зарплата изменилась?",
            reply_markup=get_change_month_keyboard()
        )
        await state.set_state(SalaryState.change_month_input)

    else:
        await message.answer(
            "Пожалуйста, выбери 'Да✅' или 'Нет❌' из клавиатуры.",
            reply_markup=get_salary_change_keyboard()
        )


async def process_change_month(message: types.Message, state: FSMContext):
    month_input = message.text.strip()

    if month_input in MONTH_NAME_TO_NUM:
        change_month = MONTH_NAME_TO_NUM[month_input]
        await state.update_data(change_month=change_month)

        # Спрашиваем старую зарплату
        await message.answer(
            "Какая была зарплата до этого месяца (до вычета НДФЛ)?"
        )
        await state.set_state(SalaryState.old_salary_input)
    else:
        await message.answer(
            "Выберите месяц из клавиатуры.",
            reply_markup=get_change_month_keyboard()
        )


async def process_old_salary(message: types.Message, state: FSMContext):
    try:
        old_salary = float(message.text.strip())
        if old_salary <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное число (зарплату).")
        return

    await state.update_data(old_salary=old_salary)

    # Спрашиваем новую зарплату
    await message.answer(
        "Какая стала зарплата с этого месяца (до вычета НДФЛ)?"
    )
    await state.set_state(SalaryState.new_salary_input)


async def process_new_salary(message: types.Message, state: FSMContext):
    try:
        new_salary = float(message.text.strip())
        if new_salary <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное число (зарплату).")
        return

    # Получаем данные из state
    data = await state.get_data()
    change_month = data["change_month"]
    old_salary = data["old_salary"]

    # Формируем строку зарплаты в формате "1-(N-1):old;N-12:new"
    if change_month == 1:
        # Зарплата изменилась с января
        salary_input = f"1-12:{new_salary}"
    else:
        salary_input = f"1-{change_month - 1}:{old_salary};{change_month}-12:{new_salary}"

    # Сохраняем в state и переходим к расчёту
    await state.update_data(salary_input=salary_input)
    await process_salary(message, state, salary_input=salary_input)


async def process_salary(message: types.Message, state: FSMContext, salary_input: str = None):
    # Если salary_input не передан, берём из сообщения
    if salary_input is None:
        salary_input = message.text.strip()

    # Убираем ".0" если есть (для кнопок)
    if salary_input.endswith(".0"):
        salary_input = salary_input[:-2]

    data = await state.get_data()
    months_to_show = data.get("months_to_show", list(range(1, 13)))
    full_year_mode = data.get("full_year_mode", True)

    salary_by_month = parse_salary_periods(salary_input)
    if salary_by_month is None:
        await message.answer(
            "Некорректный формат ввода зарплаты. Попробуй ещё раз в таком виде:\n"
            "442000\n"
            "или\n"
            "1-5:422000;6-12:442000"
        )
        return

    # Получаем user_id (пользователь уже добавлен в БД в cmd_start)
    user_id = get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    await state.update_data(salary_by_month=salary_by_month, user_id=user_id)

    # Сохраняем периоды зарплаты в БД
    save_salary_periods(user_id, salary_by_month, CURRENT_YEAR)

    # Сохраняем последнюю зарплату пользователя
    salary_values = list(set(salary_by_month.values()))
    if len(salary_values) == 1:
        # Зарплата не менялась
        update_user_last_salary(user_id, str(salary_values[0]))
    else:
        # Зарплата менялась, извлекаем данные
        change_month = None
        old_salary = None
        new_salary = None
        for m in range(1, 13):
            if salary_by_month[m] != salary_by_month[1]:
                change_month = m
                old_salary = salary_by_month[1]
                new_salary = salary_by_month[m]
                break
        update_user_last_salary(user_id, salary_input, change_month, old_salary, new_salary)

    # Считаем результаты
    results = calculate_results(months_to_show, salary_by_month)

    # Формируем итоговое сообщение
    if full_year_mode:
        lines = ["Результат за весь год (Месяц, аванс после вычета налогов, остаток зп после вычета налогов):"]
        for m in months_to_show:
            res = results[m]
            lines.append(f"{res['month_name']}, {res['advance_net']:,.2f} ₽, {res['remainder_net']:,.2f} ₽")

            # Сохраняем расчёт в БД для каждого месяца
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

        result_text = "\n".join(lines)

        # Уведомление о порогах НДФЛ
        cumulative_income = results[12]["cumulative_after_month"]
        ndfl_message = get_ndfl_progress_message(cumulative_income)
        if ndfl_message:
            result_text += ndfl_message

    else:
        m = months_to_show[0]
        res = results[m]
        result_text = (
            f"Результат:\n"
            f"Месяц: {res['month_name']}\n"
            f"Аванс после вычета налогов: {res['advance_net']:,.2f} ₽\n"
            f"Остаток зарплаты после вычета налога: {res['remainder_net']:,.2f} ₽"
        )

        # Сохраняем расчёт в БД
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

        # Уведомление о порогах НДФЛ
        cumulative_income = res["cumulative_after_month"]
        ndfl_message = get_ndfl_progress_message(cumulative_income)
        if ndfl_message:
            result_text += ndfl_message

    await state.clear()

    # Отправляем результат + кнопку
    await message.answer(
        result_text,
        reply_markup=get_calculation_keyboard()
    )


async def cmd_stats(message: types.Message):
    """
    Команда /stats — статистика за год.
    """
    user_id = get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    import sqlite3
    from core.config import DB_FILE

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Общая сумма зарплаты и НДФЛ
    cur.execute(
        """
        SELECT SUM(advance_gross + remainder_gross), SUM(advance_net + remainder_net), SUM(ndfl_advance + ndfl_remainder)
        FROM calculations
        WHERE user_id = ? AND year = ?
        """,
        (user_id, CURRENT_YEAR),
    )
    row = cur.fetchone()
    conn.close()

    if row and row[0]:
        total_gross = row[0]
        total_net = row[1]
        total_ndfl = row[2]

        # Считаем количество месяцев с расчётами
        cur.execute(
            """
            SELECT COUNT(DISTINCT month)
            FROM calculations
            WHERE user_id = ? AND year = ?
            """,
            (user_id, CURRENT_YEAR),
        )
        months_count = cur.fetchone()[0]

        if months_count > 0:
            avg_salary = total_gross / months_count
        else:
            avg_salary = 0

        text = (
            f"📊 Статистика за {CURRENT_YEAR} год:\n\n"
            f"Всего заработано (до вычета): {total_gross:,.2f} ₽\n"
            f"Всего получено (после вычета): {total_net:,.2f} ₽\n"
            f"Всего НДФЛ: {total_ndfl:,.2f} ₽\n"
            f"Средняя зарплата в месяц: {avg_salary:,.2f} ₽\n"
            f"Месяцев с расчётами: {months_count}"
        )
    else:
        text = "Пока нет расчётов за этот год."

    await message.answer(text)


async def cmd_edit(message: types.Message):
    """
    Команда /edit — редактирование зарплаты.
    """
    user_id = get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    last_salary = get_user_last_salary(user_id)

    if last_salary and last_salary.get("last_salary_input"):
        text = (
            f"✏️ Редактирование зарплаты\n\n"
            f"Твоя последняя зарплата: {last_salary['last_salary_input']} ₽\n\n"
            f"Введи новую зарплату в таком же формате:\n"
            f"442000 — одна зарплата на весь год\n"
            f"или\n"
            f"1-5:422000;6-12:442000 — с периодами"
        )
        await message.answer(text)
    else:
        await message.answer("У тебя пока нет сохранённой зарплаты. Сначала сделай расчёт.")