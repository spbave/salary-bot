from typing import Dict, List, Optional

WORK_DAYS_2026 = {
    1: 15,
    2: 19,
    3: 21,
    4: 22,
    5: 19,
    6: 21,
    7: 23,
    8: 21,
    9: 22,
    10: 22,
    11: 20,
    12: 22,
}

WORK_DAYS_UPTO_15_2026 = {
    1: 4,
    2: 10,
    3: 9,
    4: 11,
    5: 9,
    6: 10,
    7: 11,
    8: 10,
    9: 11,
    10: 11,
    11: 9,
    12: 11,
}

MONTH_NAMES = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


def ndfl_progressive(cumulative_income: float) -> float:
    tax = 0.0
    prev_limit = 0.0

    brackets = [
        (2_400_000, 0.13),
        (5_000_000, 0.15),
        (20_000_000, 0.18),
        (50_000_000, 0.20),
        (float("inf"), 0.22),
    ]

    income_left = cumulative_income

    for limit, rate in brackets:
        if income_left <= 0:
            break
        bracket_size = limit - prev_limit
        taxable_in_bracket = min(income_left, bracket_size)
        tax += taxable_in_bracket * rate
        income_left -= taxable_in_bracket
        prev_limit = limit

    return tax


def parse_salary_periods(salary_input: str) -> Optional[Dict[int, float]]:
    salary_input = salary_input.strip()

    if ":" not in salary_input and ";" not in salary_input:
        try:
            salary = float(salary_input)
            if salary <= 0:
                raise ValueError
            return {m: salary for m in range(1, 13)}
        except ValueError:
            return None

    salary_by_month = {}
    parts = [p.strip() for p in salary_input.split(";") if p.strip()]

    for part in parts:
        if ":" not in part:
            return None
        range_part, sal_part = part.split(":", 1)
        try:
            salary = float(sal_part.strip())
            if salary <= 0:
                return None
        except ValueError:
            return None

        range_part = range_part.strip()
        if "-" in range_part:
            try:
                m_from, m_to = map(int, range_part.split("-", 1))
            except ValueError:
                return None
        else:
            try:
                m_from = m_to = int(range_part)
            except ValueError:
                return None

        if not (1 <= m_from <= m_to <= 12):
            return None

        for m in range(m_from, m_to + 1):
            salary_by_month[m] = salary

    if len(salary_by_month) != 12:
        return None

    return salary_by_month


def calc_advance_for_month(month: int, monthly_gross: float, cumulative_before_month: float):
    work_days_month = WORK_DAYS_2026[month]
    work_days_upto_15 = WORK_DAYS_UPTO_15_2026[month]

    advance_gross = monthly_gross / work_days_month * work_days_upto_15
    remainder_gross = monthly_gross - advance_gross

    cumulative_after_advance = cumulative_before_month + advance_gross
    cumulative_after_month = cumulative_before_month + monthly_gross

    tax_before = ndfl_progressive(cumulative_before_month)
    tax_after_advance = ndfl_progressive(cumulative_after_advance)
    tax_after_month = ndfl_progressive(cumulative_after_month)

    ndfl_advance = tax_after_advance - tax_before
    ndfl_remainder = tax_after_month - tax_after_advance

    advance_net = advance_gross - ndfl_advance
    remainder_net = remainder_gross - ndfl_remainder

    return {
        "month": month,
        "month_name": MONTH_NAMES[month],
        "advance_net": advance_net,
        "remainder_net": remainder_net,
        "advance_gross": advance_gross,
        "remainder_gross": remainder_gross,
        "ndfl_advance": ndfl_advance,
        "ndfl_remainder": ndfl_remainder,
        "cumulative_before": cumulative_before_month,
        "cumulative_after_advance": cumulative_after_advance,
        "cumulative_after_month": cumulative_after_month,
    }


def calculate_results(months_to_show: List[int], salary_by_month: Dict[int, float]):
    cumulative_before = 0.0
    results = {}

    for m in range(1, 13):
        salary = salary_by_month[m]
        res = calc_advance_for_month(m, salary, cumulative_before)
        results[m] = res
        cumulative_before = res["cumulative_after_month"]

    return results
