from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

MONTH_NAMES = ["Январь❄️", "Февраль❄️", "Март🌳",
               "Апрель🌳", "Май🌳", "Июнь☀️",
               "Июль☀️", "Август☀️", "Сентябрь🍁",
               "Октябрь🍁", "Ноябрь🍁", "Декабрь❄️"]


def get_month_keyboard() -> ReplyKeyboardMarkup:
    keyboard = []
    # 3 ряда по 4 кнопки
    for row in range(3):
        row_buttons = []
        for col in range(4):
            month_num = row * 4 + col + 1
            row_buttons.append(KeyboardButton(text=MONTH_NAMES[month_num - 1]))
        keyboard.append(row_buttons)

    # Последний ряд: кнопка "Весь год"
    keyboard.append([KeyboardButton(text="Весь год📅")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_salary_change_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да✅"), KeyboardButton(text="Нет❌")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return keyboard


def get_change_month_keyboard() -> ReplyKeyboardMarkup:
    keyboard = []
    # 3 ряда по 4 кнопки
    for row in range(3):
        row_buttons = []
        for col in range(4):
            month_num = row * 4 + col + 1
            row_buttons.append(KeyboardButton(text=MONTH_NAMES[month_num - 1]))
        keyboard.append(row_buttons)

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_calculation_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Рассчитать ещё раз🔄")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return keyboard
