"""
Модуль с функциями для работы с датами и временем.
"""

import datetime
from typing import Tuple, Optional


def parse_date_range(date_range: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses a date range string from callback_data.
    """
    if date_range == "date_range_all":
        return None, None

    # Make sure we're parsing the string correctly
    parts = date_range.split('_')
    if len(parts) >= 3:
        # Extract dates from the 3rd and 4th parts
        start_date = parts[2]
        end_date = parts[3] if len(parts) > 3 else None
        return start_date, end_date
    else:
        # Invalid format
        return None, None


def get_period_name(date_range: str) -> str:
    """
    Возвращает название периода для диапазона дат.
    
    Args:
        date_range: строка с диапазоном дат
        
    Returns:
        str: название периода
    """
    if date_range == "date_range_all":
        return "за все время"

    # Parsing correctly - using the entire string after "date_range_"
    parts = date_range.split('_')
    # Make sure we have at least 3 parts (date_range, start_date, end_date)
    if len(parts) >= 3:
        start_date = parts[2]
        end_date = parts[3] if len(parts) > 3 else None

        # Convert dates
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.datetime.strptime(end_date,
                                         '%Y-%m-%d').date() if end_date else datetime.datetime.now().date()
    
    # Определение периода
    delta = end - start
    
    if delta.days == 6:
        return "за последнюю неделю"
    elif delta.days == 29:
        return "за последний месяц"
    elif delta.days == 89:
        return "за последние 3 месяца"
    else:
        return f"с {start_date} по {end_date}"


def get_today() -> str:
    """
    Возвращает сегодняшнюю дату в формате строки.
    
    Returns:
        str: сегодняшняя дата в формате 'YYYY-MM-DD'
    """
    return datetime.datetime.now().strftime('%Y-%m-%d')


def is_valid_time_format(time_str: str) -> bool:
    """
    Checks if the string is a valid time format HH:MM (with exactly 2 digits for both).
    """
    try:
        # Check basic format with regex to enforce 2 digits for both hours and minutes
        import re
        if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$', time_str):
            return False

        # If the regex passes, parse the values as a double-check
        hour, minute = map(int, time_str.split(':'))
        return 0 <= hour <= 23 and 0 <= minute <= 59
    except (ValueError, TypeError):
        return False


def format_date(date_str: str, output_format: str = '%d.%m.%Y') -> str:
    """
    Форматирует дату из формата YYYY-MM-DD в указанный формат.

    Args:
        date_str: дата в формате 'YYYY-MM-DD'
        output_format: формат вывода даты

    Returns:
        str: отформатированная дата
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime(output_format)
    except ValueError:
        return date_str  # Возвращаем исходную строку в случае ошибки