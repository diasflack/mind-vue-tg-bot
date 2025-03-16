"""
Модуль с функциями для работы с датами и временем.
"""

import datetime
from typing import Tuple, Optional


def parse_date_range(date_range: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Парсит строку диапазона дат из callback_data.
    
    Args:
        date_range: строка с диапазоном дат
        
    Returns:
        Tuple[Optional[str], Optional[str]]: кортеж (начальная дата, конечная дата)
    """
    if date_range == "date_range_all":
        return None, None
    
    # Извлечение дат из callback_data
    _, start_date, end_date = date_range.split('_', 2)
    return start_date, end_date


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
    
    # Извлечение дат из callback_data
    _, start_date, end_date = date_range.split('_', 2)
    
    # Преобразование строковых дат в объекты datetime
    start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    
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
    Проверяет, является ли строка корректным форматом времени HH:MM.
    
    Args:
        time_str: строка времени для проверки
        
    Returns:
        bool: True, если формат корректен
    """
    try:
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