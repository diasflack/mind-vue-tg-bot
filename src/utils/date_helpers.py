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


def get_yesterday() -> str:
    """
    Возвращает вчерашнюю дату в формате строки.
    
    Returns:
        str: вчерашняя дата в формате 'YYYY-MM-DD'
    """
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')


def get_days_ago(days: int) -> str:
    """
    Возвращает дату N дней назад в формате строки.
    
    Args:
        days: количество дней назад
        
    Returns:
        str: дата N дней назад в формате 'YYYY-MM-DD'
    """
    target_date = datetime.datetime.now() - datetime.timedelta(days=days)
    return target_date.strftime('%Y-%m-%d')


def parse_user_date(date_str: str) -> str:
    """
    Парсит пользовательский ввод даты в различных форматах.
    
    Поддерживаемые форматы:
    - DD.MM.YYYY (например: 25.05.2025)
    - DD.MM.YY (например: 25.05.25)
    - DD.MM (текущий год, например: 25.05)
    - DD/MM/YYYY, DD/MM/YY, DD/MM
    - YYYY-MM-DD (ISO формат)
    
    Args:
        date_str: строка с датой от пользователя
        
    Returns:
        str: дата в формате 'YYYY-MM-DD' или None если не удалось распарсить
    """
    if not date_str or not isinstance(date_str, str):
        return None
        
    date_str = date_str.strip()
    
    # Список форматов для попытки парсинга
    formats = [
        '%d.%m.%Y',    # DD.MM.YYYY
        '%d.%m.%y',    # DD.MM.YY
        '%d.%m',       # DD.MM (текущий год)
        '%d/%m/%Y',    # DD/MM/YYYY
        '%d/%m/%y',    # DD/MM/YY
        '%d/%m',       # DD/MM (текущий год)
        '%Y-%m-%d'     # YYYY-MM-DD (ISO)
    ]
    
    current_year = datetime.datetime.now().year
    
    for fmt in formats:
        try:
            if '%Y' not in fmt and '%y' not in fmt:
                # Для форматов без года добавляем текущий год
                parsed_date = datetime.datetime.strptime(date_str, fmt)
                parsed_date = parsed_date.replace(year=current_year)
            else:
                parsed_date = datetime.datetime.strptime(date_str, fmt)
                
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue
            
    return None


def is_valid_entry_date(date_str: str) -> bool:
    """
    Проверяет, является ли дата валидной для создания записи.
    
    Ограничения:
    - Не должна быть в будущем
    - Не должна быть раньше 2020-01-01
    
    Args:
        date_str: дата в формате 'YYYY-MM-DD'
        
    Returns:
        bool: True если дата валидна для записи
    """
    if not date_str or not isinstance(date_str, str):
        return False
        
    try:
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        today = datetime.datetime.now().date()
        min_date = datetime.date(2020, 1, 1)
        
        # Дата не должна быть в будущем
        if target_date > today:
            return False
            
        # Дата не должна быть слишком старой
        if target_date < min_date:
            return False
            
        return True
    except ValueError:
        return False


def format_date_for_user(date_str: str, include_day_name: bool = False) -> str:
    """
    Форматирует дату для отображения пользователю.
    
    Args:
        date_str: дата в формате 'YYYY-MM-DD'
        include_day_name: включать ли название дня недели
        
    Returns:
        str: отформатированная дата для пользователя
    """
    if not date_str:
        return ""
        
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        
        if include_day_name:
            # Русские названия дней недели
            day_names = [
                'понедельник', 'вторник', 'среда', 'четверг',
                'пятница', 'суббота', 'воскресенье'
            ]
            day_name = day_names[date_obj.weekday()]
            return f"{day_name} {date_obj.strftime('%d.%m.%Y')}"
        else:
            return date_obj.strftime('%d.%m.%Y')
    except ValueError:
        return date_str



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
        return date_str


def get_date_options() -> list:
    """
    Возвращает список опций дат для выбора (вчера, 2 дня назад и т.д.).
    
    Returns:
        list: список словарей с информацией о датах
    """
    today = datetime.datetime.now().date()
    options = []
    
    # Добавляем опции для последних 7 дней
    for i in range(1, 8):
        date = today - datetime.timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        display_date = date.strftime('%d.%m.%Y')
        
        if i == 1:
            label = f"Вчера ({display_date})"
        else:
            label = f"{i} дня назад ({display_date})"
            
        options.append({
            'date': date_str,
            'label': label,
            'callback': f"date_select_{date_str}"
        })
    
    return options


def validate_manual_date(date_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Валидирует введенную пользователем дату.
    
    Args:
        date_str: строка с датой, введенная пользователем
        
    Returns:
        Tuple[bool, Optional[str], Optional[str]]: 
            (успех, нормализованная_дата, сообщение_об_ошибке)
    """
    if not date_str or not date_str.strip():
        return False, None, "Пожалуйста, введите дату."
    
    date_str = date_str.strip()
    today = datetime.datetime.now().date()
    
    # Поддерживаемые форматы
    formats = [
        '%d.%m.%Y',    # 29.05.2025
        '%d.%m.%y',    # 29.05.25
        '%d-%m-%Y',    # 29-05-2025
        '%d-%m-%y',    # 29-05-25
        '%Y-%m-%d',    # 2025-05-29
        '%d/%m/%Y',    # 29/05/2025
        '%d/%m/%y'     # 29/05/25
    ]
    
    parsed_date = None
    for date_format in formats:
        try:
            parsed_date = datetime.datetime.strptime(date_str, date_format).date()
            break
        except ValueError:
            continue
    
    if parsed_date is None:
        return False, None, (
            "Неверный формат даты. Поддерживаемые форматы:\n"
            "• 29.05.2025\n"
            "• 29.05.25\n"
            "• 29-05-2025\n"
            "• 2025-05-29"
        )
    
    # Проверяем, что дата не в будущем
    if parsed_date > today:
        return False, None, "Нельзя добавлять записи на будущие даты."
    
    # Проверяем, что дата не слишком старая (например, не более 2 лет назад)
    two_years_ago = today - datetime.timedelta(days=730)
    if parsed_date < two_years_ago:
        return False, None, f"Дата слишком старая. Минимальная дата: {two_years_ago.strftime('%d.%m.%Y')}"
    
    return True, parsed_date.strftime('%Y-%m-%d'), None


def get_yesterday() -> str:
    """
    Возвращает вчерашнюю дату в формате строки.
    
    Returns:
        str: вчерашняя дата в формате 'YYYY-MM-DD'
    """
    yesterday = datetime.datetime.now().date() - datetime.timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')


def get_date_n_days_ago(days: int) -> str:
    """
    Возвращает дату N дней назад в формате строки.
    
    Args:
        days: количество дней назад
        
    Returns:
        str: дата N дней назад в формате 'YYYY-MM-DD'
    """
    target_date = datetime.datetime.now().date() - datetime.timedelta(days=days)
    return target_date.strftime('%Y-%m-%d')
  # Возвращаем исходную строку в случае ошибки


def local_to_utc(local_time: datetime.time, offset_hours: int) -> str:
    """
    Convert a clock time that is known to be in a fixed UTC offset
    into the corresponding UTC clock time (“HH:MM”).

    Parameters
    ----------
    local_time     : datetime.time – the time entered by the user
    offset_hours   : int – e.g., +3, -5, 5

    Returns
    -------
    str – formatted as “HH:MM”
    """
    # Build a fixed-offset tzinfo, e.g., UTC+03:00 or UTC−05:30
    sign = 1 if offset_hours >= 0 else -1
    hours = int(abs(offset_hours))
    minutes = int(round((abs(offset_hours) - hours) * 60))
    tz = datetime.timezone(sign * datetime.timedelta(hours=hours, minutes=minutes))

    # Anchor on today's date (any date works; we only care about the clock part)
    today = datetime.datetime.utcnow().date()
    local_dt = datetime.datetime.combine(today, local_time, tzinfo=tz)

    # Convert to UTC and format
    utc_dt = local_dt.astimezone(datetime.timezone.utc)
    return utc_dt.strftime("%H:%M")
