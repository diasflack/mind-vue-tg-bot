"""
Модуль для работы с избранными опросами (Phase 5.3).

Функции для управления избранными опросами пользователя.
"""

import sqlite3
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def add_to_favorites(
    conn: sqlite3.Connection,
    chat_id: int,
    template_id: int
) -> bool:
    """
    Добавляет опрос в избранное.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        template_id: ID опроса

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

        # Проверяем существование записи предпочтений
        cursor.execute('''
            SELECT chat_id FROM user_survey_preferences
            WHERE chat_id = ? AND template_id = ?
        ''', (chat_id, template_id))

        if cursor.fetchone():
            # Обновляем существующую запись
            cursor.execute('''
                UPDATE user_survey_preferences
                SET is_favorite = 1
                WHERE chat_id = ? AND template_id = ?
            ''', (chat_id, template_id))
        else:
            # Создаем новую запись
            cursor.execute('''
                INSERT INTO user_survey_preferences
                (chat_id, template_id, is_favorite)
                VALUES (?, ?, 1)
            ''', (chat_id, template_id))

        conn.commit()
        logger.info(f"Опрос {template_id} добавлен в избранное пользователя {chat_id}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении в избранное: {e}")
        conn.rollback()
        return False


def remove_from_favorites(
    conn: sqlite3.Connection,
    chat_id: int,
    template_id: int
) -> bool:
    """
    Удаляет опрос из избранного.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        template_id: ID опроса

    Returns:
        bool: True если успешно, False если запись не найдена
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

        # Обновляем запись
        cursor.execute('''
            UPDATE user_survey_preferences
            SET is_favorite = 0
            WHERE chat_id = ? AND template_id = ?
        ''', (chat_id, template_id))

        conn.commit()
        logger.info(f"Опрос {template_id} удален из избранного пользователя {chat_id}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при удалении из избранного: {e}")
        conn.rollback()
        return False


def get_favorite_surveys(
    conn: sqlite3.Connection,
    chat_id: int
) -> List[Dict[str, Any]]:
    """
    Получает список избранных опросов пользователя.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя

    Returns:
        List[Dict]: список избранных опросов с метаданными
    """
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            usp.template_id,
            st.name as survey_name,
            st.description,
            st.is_system
        FROM user_survey_preferences usp
        JOIN survey_templates st ON usp.template_id = st.id
        WHERE usp.chat_id = ? AND usp.is_favorite = 1
        ORDER BY st.name
    ''', (chat_id,))

    rows = cursor.fetchall()

    favorites = []
    for row in rows:
        favorites.append({
            'template_id': row[0],
            'survey_name': row[1],
            'description': row[2],
            'is_system': row[3]
        })

    return favorites


def is_favorite(
    conn: sqlite3.Connection,
    chat_id: int,
    template_id: int
) -> bool:
    """
    Проверяет, находится ли опрос в избранном.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        template_id: ID опроса

    Returns:
        bool: True если опрос в избранном
    """
    cursor = conn.cursor()

    cursor.execute('''
        SELECT is_favorite FROM user_survey_preferences
        WHERE chat_id = ? AND template_id = ?
    ''', (chat_id, template_id))

    row = cursor.fetchone()

    if row is None:
        return False

    return bool(row[0])
