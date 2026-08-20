import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.config import DB_FILE


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS salary_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            month_from INTEGER NOT NULL,
            month_to INTEGER NOT NULL,
            salary REAL NOT NULL,
            year INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            salary REAL NOT NULL,
            advance_net REAL NOT NULL,
            remainder_net REAL NOT NULL,
            advance_gross REAL NOT NULL,
            remainder_gross REAL NOT NULL,
            ndfl_advance REAL NOT NULL,
            ndfl_remainder REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            last_salary_input TEXT,
            last_change_month INTEGER,
            last_old_salary REAL,
            last_new_salary REAL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def get_or_create_user(
        telegram_id: int,
        username: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
) -> int:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    if row:
        user_id = row[0]
    else:
        cur.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_id, username, first_name, last_name, datetime.now().isoformat()),
        )
        user_id = cur.lastrowid

    conn.commit()
    conn.close()
    return user_id


def save_salary_periods(user_id: int, salary_by_month: Dict[int, float], year: int):
    periods = _compress_periods(salary_by_month)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("DELETE FROM salary_periods WHERE user_id = ? AND year = ?", (user_id, year))

    for month_from, month_to, salary in periods:
        cur.execute(
            """
            INSERT INTO salary_periods (user_id, month_from, month_to, salary, year, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, month_from, month_to, salary, year, datetime.now().isoformat()),
        )

    conn.commit()
    conn.close()


def save_calculation(
        user_id: int,
        month: int,
        year: int,
        salary: float,
        advance_net: float,
        remainder_net: float,
        advance_gross: float,
        remainder_gross: float,
        ndfl_advance: float,
        ndfl_remainder: float,
):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO calculations (
            user_id, month, year, salary,
            advance_net, remainder_net,
            advance_gross, remainder_gross,
            ndfl_advance, ndfl_remainder,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id, month, year, salary,
            advance_net, remainder_net,
            advance_gross, remainder_gross,
            ndfl_advance, ndfl_remainder,
            datetime.now().isoformat(),
        ),
    )

    conn.commit()
    conn.close()


def get_user_history(telegram_id: int, limit: int = 10) -> List[Tuple]:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT c.month, c.year, c.salary, c.advance_net, c.remainder_net, c.created_at
        FROM calculations c
        JOIN users u ON c.user_id = u.id
        WHERE u.telegram_id = ?
        ORDER BY c.year DESC, c.month DESC, c.id DESC
        LIMIT ?
        """,
        (telegram_id, limit),
    )

    rows = cur.fetchall()
    conn.close()
    return rows


def _compress_periods(salary_by_month: Dict[int, float]) -> List[Tuple[int, int, float]]:
    months = sorted(salary_by_month.keys())
    if not months:
        return []

    periods = []
    start_month = months[0]
    prev_salary = salary_by_month[start_month]

    for m in months[1:] + [13]:
        if m == 13:
            periods.append((start_month, 12, prev_salary))
            break
        salary = salary_by_month[m]
        if salary != prev_salary:
            periods.append((start_month, m - 1, prev_salary))
            start_month = m
            prev_salary = salary

    return periods


def update_user_last_salary(user_id: int, last_salary_input: str, last_change_month: int = None,
                            last_old_salary: float = None, last_new_salary: float = None):
    """
    Сохраняем последние введённые пользователем данные о зарплате.
    """
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT OR REPLACE INTO user_settings (user_id, last_salary_input, last_change_month, last_old_salary, last_new_salary, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, last_salary_input, last_change_month, last_old_salary, last_new_salary, datetime.now().isoformat()),
    )

    conn.commit()
    conn.close()


def get_user_last_salary(user_id: int) -> Dict:
    """
    Получаем последние введённые пользователем данные о зарплате.
    """
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT last_salary_input, last_change_month, last_old_salary, last_new_salary
        FROM user_settings
        WHERE user_id = ?
        """,
        (user_id,),
    )

    row = cur.fetchone()
    conn.close()

    if row:
        return {
            "last_salary_input": row[0],
            "last_change_month": row[1],
            "last_old_salary": row[2],
            "last_new_salary": row[3],
        }
    return None
