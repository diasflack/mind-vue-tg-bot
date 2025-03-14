"""
Модуль с определениями клавиатур для взаимодействия с пользователем.
"""

from datetime import datetime, timedelta
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

# Клавиатура для ввода числовых значений от 1 до 10
NUMERIC_KEYBOARD = ReplyKeyboardMarkup([
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['10', '/cancel']
], one_time_keyboard=True)

# Основная клавиатура с командами - только /add и /help
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    ['/add', '/help']
], resize_keyboard=True, is_persistent=True)


def get_date_range_keyboard(prefix=""):
    """
    Создает inline-клавиатуру для выбора диапазона дат.

    Args:
        prefix: префикс для callback_data

    Returns:
        InlineKeyboardMarkup: клавиатура с кнопками выбора диапазона дат
    """
    # Создание кнопок выбора диапазона дат - последние 7, 30, 90 дней или все время
    today = datetime.now().date()
    week_ago = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    month_ago = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    quarter_ago = (today - timedelta(days=90)).strftime('%Y-%m-%d')

    keyboard = [
        [InlineKeyboardButton("Последние 7 дней", callback_data=f"{prefix}date_range_{week_ago}_{today}")],
        [InlineKeyboardButton("Последние 30 дней", callback_data=f"{prefix}date_range_{month_ago}_{today}")],
        [InlineKeyboardButton("Последние 90 дней", callback_data=f"{prefix}date_range_{quarter_ago}_{today}")],
        [InlineKeyboardButton("Всё время", callback_data=f"{prefix}date_range_all")]
    ]

    return InlineKeyboardMarkup(keyboard)