"""
Модуль для работы с напоминаниями по опросам (Phase 5.2).

Функции для управления уведомлениями о заполнении опросов.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def _convert_time_to_utc(local_time: str, timezone_offset: int) -> str:
    """
    Конвертирует локальное время в UTC.

    Args:
        local_time: время в формате HH:MM
        timezone_offset: смещение часового пояса (например, +3 для МСК)

    Returns:
        str: время в UTC в формате HH:MM
    """
    hours, minutes = map(int, local_time.split(':'))
    utc_hours = (hours - timezone_offset) % 24
    return f"{utc_hours:02d}:{minutes:02d}"


def _convert_time_from_utc(utc_time: str, timezone_offset: int) -> str:
    """
    Конвертирует UTC время в локальное.

    Args:
        utc_time: время в UTC в формате HH:MM
        timezone_offset: смещение часового пояса

    Returns:
        str: локальное время в формате HH:MM
    """
    hours, minutes = map(int, utc_time.split(':'))
    local_hours = (hours + timezone_offset) % 24
    return f"{local_hours:02d}:{minutes:02d}"


def set_survey_reminder(
    conn: sqlite3.Connection,
    chat_id: int,
    template_id: int,
    notification_time: str,
    timezone_offset: int
) -> bool:
    """
    Устанавливает или обновляет напоминание для опроса.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        template_id: ID опроса
        notification_time: время напоминания в локальном времени (HH:MM)
        timezone_offset: смещение часового пояса

    Returns:
        bool: True если успешно, False если опрос не найден
    """
    cursor = conn.cursor()

    try:
        # Проверяем существование опроса
        cursor.execute('SELECT id FROM survey_templates WHERE id = ?', (template_id,))
        if not cursor.fetchone():
            logger.warning(f"Опрос {template_id} не найден")
            return False

        # Конвертируем время в UTC
        utc_time = _convert_time_to_utc(notification_time, timezone_offset)

        # Проверяем существование записи
        cursor.execute('''
            SELECT chat_id FROM user_survey_preferences
            WHERE chat_id = ? AND template_id = ?
        ''', (chat_id, template_id))

        if cursor.fetchone():
            # Обновляем существующую запись
            cursor.execute('''
                UPDATE user_survey_preferences
                SET notification_enabled = 1,
                    notification_time = ?
                WHERE chat_id = ? AND template_id = ?
            ''', (utc_time, chat_id, template_id))
        else:
            # Создаем новую запись
            cursor.execute('''
                INSERT INTO user_survey_preferences
                (chat_id, template_id, notification_enabled, notification_time)
                VALUES (?, ?, 1, ?)
            ''', (chat_id, template_id, utc_time))

        conn.commit()
        logger.info(f"Установлено напоминание для опроса {template_id} пользователю {chat_id} на {notification_time} (UTC: {utc_time})")
        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при установке напоминания: {e}")
        conn.rollback()
        return False


def remove_survey_reminder(
    conn: sqlite3.Connection,
    chat_id: int,
    template_id: int
) -> bool:
    """
    Удаляет (отключает) напоминание для опроса.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        template_id: ID опроса

    Returns:
        bool: True если успешно отключено, False если запись не найдена
    """
    cursor = conn.cursor()

    try:
        # Проверяем существование записи
        cursor.execute('''
            SELECT chat_id FROM user_survey_preferences
            WHERE chat_id = ? AND template_id = ?
        ''', (chat_id, template_id))

        if not cursor.fetchone():
            return False

        # Отключаем напоминание
        cursor.execute('''
            UPDATE user_survey_preferences
            SET notification_enabled = 0
            WHERE chat_id = ? AND template_id = ?
        ''', (chat_id, template_id))

        conn.commit()
        logger.info(f"Отключено напоминание для опроса {template_id} пользователя {chat_id}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при удалении напоминания: {e}")
        conn.rollback()
        return False


def get_survey_reminders(
    conn: sqlite3.Connection,
    chat_id: int,
    enabled_only: bool = False
) -> List[Dict[str, Any]]:
    """
    Получает список напоминаний пользователя.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        enabled_only: получать только включенные напоминания

    Returns:
        List[Dict]: список напоминаний с информацией об опросах
    """
    cursor = conn.cursor()

    query = '''
        SELECT
            usp.template_id,
            st.name as survey_name,
            st.description,
            usp.notification_enabled,
            usp.notification_time,
            usp.is_favorite
        FROM user_survey_preferences usp
        JOIN survey_templates st ON usp.template_id = st.id
        WHERE usp.chat_id = ?
    '''

    if enabled_only:
        query += ' AND usp.notification_enabled = 1'

    cursor.execute(query, (chat_id,))
    rows = cursor.fetchall()

    reminders = []
    for row in rows:
        reminders.append({
            'template_id': row[0],
            'survey_name': row[1],
            'description': row[2],
            'notification_enabled': row[3],
            'notification_time': row[4],
            'is_favorite': row[5]
        })

    return reminders


def get_surveys_for_notification(
    conn: sqlite3.Connection,
    current_time: str
) -> List[Dict[str, Any]]:
    """
    Получает список опросов для отправки уведомлений в текущее время.

    Args:
        conn: соединение с БД
        current_time: текущее время в UTC (HH:MM)

    Returns:
        List[Dict]: список опросов с информацией о пользователях
    """
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            usp.chat_id,
            usp.template_id,
            st.name as survey_name,
            st.description,
            u.timezone_offset
        FROM user_survey_preferences usp
        JOIN survey_templates st ON usp.template_id = st.id
        JOIN users u ON usp.chat_id = u.chat_id
        WHERE usp.notification_enabled = 1
        AND usp.notification_time = ?
    ''', (current_time,))

    rows = cursor.fetchall()

    surveys = []
    for row in rows:
        surveys.append({
            'chat_id': row[0],
            'template_id': row[1],
            'survey_name': row[2],
            'description': row[3],
            'timezone_offset': row[4] or 0
        })

    return surveys


def is_survey_filled_today(
    conn: sqlite3.Connection,
    chat_id: int,
    template_id: int
) -> bool:
    """
    Проверяет, заполнен ли опрос сегодня.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        template_id: ID опроса

    Returns:
        bool: True если опрос уже заполнен сегодня
    """
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')

    cursor.execute('''
        SELECT id FROM survey_responses
        WHERE chat_id = ?
        AND template_id = ?
        AND response_date = ?
    ''', (chat_id, template_id, today))

    return cursor.fetchone() is not None
