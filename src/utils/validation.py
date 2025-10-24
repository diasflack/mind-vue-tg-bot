"""
Модуль для валидации пользовательского ввода.
Централизует логику валидации для избежания дублирования кода.
"""

import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def validate_numeric_input(
    text: str,
    min_val: int = 1,
    max_val: int = 10
) -> Tuple[bool, Optional[int]]:
    """
    Валидирует числовой ввод в заданном диапазоне.

    Args:
        text: строка для валидации
        min_val: минимальное допустимое значение (включительно)
        max_val: максимальное допустимое значение (включительно)

    Returns:
        Кортеж (is_valid, value):
            - is_valid: True если ввод корректен, иначе False
            - value: преобразованное число или None если валидация не прошла

    Examples:
        >>> validate_numeric_input("5")
        (True, 5)
        >>> validate_numeric_input("0")
        (False, None)
        >>> validate_numeric_input("abc")
        (False, None)
        >>> validate_numeric_input("15")
        (False, None)
    """
    # Проверка, что строка содержит только цифры
    if not text.isdigit():
        logger.debug(f"Validation failed: '{text}' is not a digit")
        return (False, None)

    # Преобразование в число
    try:
        value = int(text)
    except ValueError:
        logger.debug(f"Validation failed: cannot convert '{text}' to int")
        return (False, None)

    # Проверка диапазона
    if value < min_val or value > max_val:
        logger.debug(f"Validation failed: {value} not in range [{min_val}, {max_val}]")
        return (False, None)

    return (True, value)


def validate_comment(comment: str, max_length: int = 500) -> Tuple[bool, str]:
    """
    Валидирует и санитизирует текстовый комментарий.

    Args:
        comment: текст комментария
        max_length: максимальная длина комментария

    Returns:
        Кортеж (is_valid, sanitized_comment):
            - is_valid: True если комментарий допустим
            - sanitized_comment: обрезанный и очищенный комментарий

    Examples:
        >>> validate_comment("Good day")
        (True, "Good day")
        >>> validate_comment("  Spaces  ")
        (True, "Spaces")
        >>> validate_comment("A" * 600, max_length=500)
        (True, "A" * 500)
    """
    # Убираем лишние пробелы
    sanitized = comment.strip()

    # Проверка длины
    if len(sanitized) > max_length:
        logger.debug(f"Comment truncated from {len(sanitized)} to {max_length} chars")
        sanitized = sanitized[:max_length]

    # Комментарий может быть пустым (это валидно)
    return (True, sanitized)


def get_validation_error_message(field_name: str, min_val: int = 1, max_val: int = 10) -> str:
    """
    Возвращает стандартизированное сообщение об ошибке валидации.

    Args:
        field_name: название поля (для user-friendly сообщения)
        min_val: минимальное значение
        max_val: максимальное значение

    Returns:
        Строка с сообщением об ошибке

    Examples:
        >>> get_validation_error_message("настроение")
        "Пожалуйста, введите число от 1 до 10:"
    """
    return f"Пожалуйста, введите число от {min_val} до {max_val}:"
