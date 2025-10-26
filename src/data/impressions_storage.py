"""
Модуль для работы с хранилищем впечатлений (impressions).

Предоставляет функции для CRUD операций с впечатлениями и тегами.
"""

import logging
import sqlite3
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def save_impression(conn: sqlite3.Connection, impression_data: Dict[str, Any]) -> Optional[int]:
    """
    Сохраняет впечатление в базу данных.

    Args:
        conn: соединение с базой данных
        impression_data: словарь с данными впечатления
            - chat_id: int
            - impression_text или text: str
            - impression_date или date: str (YYYY-MM-DD)
            - impression_time или time: str (HH:MM:SS)
            - category: Optional[str]
            - intensity: Optional[int]
            - entry_date: Optional[str]

    Returns:
        Optional[int]: ID созданного впечатления или None при ошибке
    """
    try:
        cursor = conn.cursor()

        # Поддержка разных ключей для обратной совместимости
        text = impression_data.get('impression_text') or impression_data.get('text')
        date_val = impression_data.get('impression_date') or impression_data.get('date')
        time_val = impression_data.get('impression_time') or impression_data.get('time')

        cursor.execute("""
            INSERT INTO impressions (
                chat_id, impression_text, impression_date, impression_time,
                category, intensity, entry_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            impression_data['chat_id'],
            text,
            date_val,
            time_val,
            impression_data.get('category'),
            impression_data.get('intensity'),
            impression_data.get('entry_date')
        ))
        conn.commit()
        impression_id = cursor.lastrowid
        logger.debug(f"Впечатление {impression_id} сохранено для пользователя {impression_data['chat_id']}")
        return impression_id

    except sqlite3.Error as e:
        logger.error(f"Ошибка при сохранении впечатления: {e}")
        conn.rollback()
        return None


def get_user_impressions(
    conn: sqlite3.Connection,
    chat_id: int,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    include_tags: bool = False
) -> List[Dict[str, Any]]:
    """
    Получает впечатления пользователя с фильтрацией.

    Args:
        conn: соединение с базой данных
        chat_id: ID пользователя
        date: фильтр по конкретной дате (YYYY-MM-DD)
        start_date: начало диапазона дат
        end_date: конец диапазона дат
        category: фильтр по категории
        include_tags: включить теги в результат

    Returns:
        List[Dict]: список впечатлений
    """
    try:
        cursor = conn.cursor()

        # Базовый запрос
        query = """
            SELECT id, chat_id, impression_text, impression_date, impression_time,
                   category, intensity, entry_date, created_at
            FROM impressions
            WHERE chat_id = ?
        """
        params = [chat_id]

        # Добавляем фильтры
        if date:
            query += " AND impression_date = ?"
            params.append(date)

        if start_date and end_date:
            query += " AND impression_date BETWEEN ? AND ?"
            params.extend([start_date, end_date])

        if category:
            query += " AND category = ?"
            params.append(category)

        # Сортировка от новых к старым
        query += " ORDER BY impression_date DESC, impression_time DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Преобразуем в список словарей
        results = []
        for row in rows:
            impression = {
                'id': row[0],
                'chat_id': row[1],
                'impression_text': row[2],
                'impression_date': row[3],
                'impression_time': row[4],
                'category': row[5],
                'intensity': row[6],
                'entry_date': row[7],
                'created_at': row[8]
            }

            # Добавляем теги если требуется
            if include_tags:
                impression['tags'] = _get_impression_tags(conn, impression['id'])

            results.append(impression)

        logger.debug(f"Получено {len(results)} впечатлений для пользователя {chat_id}")
        return results

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении впечатлений: {e}")
        return []


def _get_impression_tags(conn: sqlite3.Connection, impression_id: int) -> List[Dict[str, Any]]:
    """
    Получает теги, привязанные к впечатлению.

    Args:
        conn: соединение с базой данных
        impression_id: ID впечатления

    Returns:
        List[Dict]: список тегов
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.chat_id, t.tag_name, t.tag_color
            FROM impression_tags t
            JOIN impression_tag_relations r ON t.id = r.tag_id
            WHERE r.impression_id = ?
        """, (impression_id,))

        rows = cursor.fetchall()
        return [
            {
                'id': row[0],
                'chat_id': row[1],
                'tag_name': row[2],
                'tag_color': row[3]
            }
            for row in rows
        ]

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении тегов впечатления: {e}")
        return []


def delete_impression(
    conn: sqlite3.Connection,
    impression_id: int,
    chat_id: int
) -> bool:
    """
    Удаляет впечатление.

    Проверяет что впечатление принадлежит указанному пользователю.

    Args:
        conn: соединение с базой данных
        impression_id: ID впечатления
        chat_id: ID пользователя (для проверки владения)

    Returns:
        bool: True если удалено успешно
    """
    try:
        cursor = conn.cursor()

        # Удаляем только если принадлежит пользователю
        cursor.execute("""
            DELETE FROM impressions
            WHERE id = ? AND chat_id = ?
        """, (impression_id, chat_id))

        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Впечатление {impression_id} удалено")
            return True
        else:
            logger.warning(f"Впечатление {impression_id} не найдено или не принадлежит пользователю {chat_id}")
            return False

    except sqlite3.Error as e:
        logger.error(f"Ошибка при удалении впечатления: {e}")
        conn.rollback()
        return False


def create_tag(
    conn: sqlite3.Connection,
    chat_id: int,
    tag_name: str,
    color: Optional[str] = None
) -> Optional[int]:
    """
    Создает тег или возвращает ID существующего.

    Имя тега нормализуется (lowercase).

    Args:
        conn: соединение с базой данных
        chat_id: ID пользователя
        tag_name: имя тега
        color: цвет тега (опционально)

    Returns:
        Optional[int]: ID тега или None при ошибке
    """
    try:
        # Нормализуем имя
        normalized_name = tag_name.lower().strip()

        cursor = conn.cursor()

        # Проверяем существование
        cursor.execute("""
            SELECT id FROM impression_tags
            WHERE chat_id = ? AND tag_name = ?
        """, (chat_id, normalized_name))

        existing = cursor.fetchone()
        if existing:
            logger.debug(f"Тег '{normalized_name}' уже существует, возвращаем ID {existing[0]}")
            return existing[0]

        # Создаем новый
        cursor.execute("""
            INSERT INTO impression_tags (chat_id, tag_name, tag_color)
            VALUES (?, ?, ?)
        """, (chat_id, normalized_name, color))

        conn.commit()
        tag_id = cursor.lastrowid

        logger.info(f"Создан тег '{normalized_name}' с ID {tag_id}")
        return tag_id

    except sqlite3.Error as e:
        logger.error(f"Ошибка при создании тега: {e}")
        conn.rollback()
        return None


def get_user_tags(conn: sqlite3.Connection, chat_id: int) -> List[Dict[str, Any]]:
    """
    Получает все теги пользователя.

    Args:
        conn: соединение с базой данных
        chat_id: ID пользователя

    Returns:
        List[Dict]: список тегов
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, chat_id, tag_name, tag_color
            FROM impression_tags
            WHERE chat_id = ?
            ORDER BY tag_name
        """, (chat_id,))

        rows = cursor.fetchall()
        return [
            {
                'id': row[0],
                'chat_id': row[1],
                'tag_name': row[2],
                'tag_color': row[3]
            }
            for row in rows
        ]

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении тегов: {e}")
        return []


def attach_tags_to_impression(
    conn: sqlite3.Connection,
    impression_id: int,
    tag_ids: List[int]
) -> bool:
    """
    Привязывает теги к впечатлению.

    Args:
        conn: соединение с базой данных
        impression_id: ID впечатления
        tag_ids: список ID тегов

    Returns:
        bool: True если успешно
    """
    try:
        cursor = conn.cursor()

        # Удаляем существующие связи (для перезаписи)
        cursor.execute("""
            DELETE FROM impression_tag_relations
            WHERE impression_id = ?
        """, (impression_id,))

        # Добавляем новые связи
        for tag_id in tag_ids:
            cursor.execute("""
                INSERT INTO impression_tag_relations (impression_id, tag_id)
                VALUES (?, ?)
            """, (impression_id, tag_id))

        conn.commit()
        logger.debug(f"Привязано {len(tag_ids)} тегов к впечатлению {impression_id}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при привязке тегов: {e}")
        conn.rollback()
        return False

def get_impression_by_id(conn: sqlite3.Connection, impression_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает впечатление по ID с проверкой владельца.

    Args:
        conn: соединение с базой данных
        impression_id: ID впечатления
        chat_id: ID пользователя (для проверки владельца)

    Returns:
        Optional[Dict]: Данные впечатления или None
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, chat_id, impression_text, impression_date, impression_time,
                   category, intensity, entry_date, created_at
            FROM impressions
            WHERE id = ? AND chat_id = ?
        """, (impression_id, chat_id))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'id': row[0],
            'chat_id': row[1],
            'text': row[2],
            'date': row[3],
            'time': row[4],
            'category': row[5],
            'intensity': row[6],
            'entry_date': row[7],
            'created_at': row[8]
        }

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении впечатления {impression_id}: {e}")
        return None


def link_impression_to_entry(
    conn: sqlite3.Connection,
    impression_id: int,
    chat_id: int,
    entry_date: str
) -> bool:
    """
    Привязывает впечатление к записи дня.

    Args:
        conn: соединение с базой данных
        impression_id: ID впечатления
        chat_id: ID пользователя (для проверки владельца)
        entry_date: дата записи (YYYY-MM-DD)

    Returns:
        bool: True если успешно привязано
    """
    try:
        cursor = conn.cursor()

        # Проверяем что впечатление принадлежит пользователю
        cursor.execute("""
            SELECT id FROM impressions
            WHERE id = ? AND chat_id = ?
        """, (impression_id, chat_id))

        if not cursor.fetchone():
            logger.warning(f"Впечатление {impression_id} не найдено для пользователя {chat_id}")
            return False

        # Проверяем существование записи
        cursor.execute("""
            SELECT date FROM entries
            WHERE chat_id = ? AND date = ?
        """, (chat_id, entry_date))

        if not cursor.fetchone():
            logger.warning(f"Запись {entry_date} не найдена для пользователя {chat_id}")
            return False

        # Привязываем впечатление к записи
        cursor.execute("""
            UPDATE impressions
            SET entry_date = ?
            WHERE id = ? AND chat_id = ?
        """, (entry_date, impression_id, chat_id))

        conn.commit()
        logger.debug(f"Впечатление {impression_id} привязано к записи {entry_date}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при привязке впечатления {impression_id} к записи {entry_date}: {e}")
        conn.rollback()
        return False


def unlink_impression(conn: sqlite3.Connection, impression_id: int, chat_id: int) -> bool:
    """
    Отвязывает впечатление от записи дня.

    Args:
        conn: соединение с базой данных
        impression_id: ID впечатления
        chat_id: ID пользователя (для проверки владельца)

    Returns:
        bool: True если успешно отвязано
    """
    try:
        cursor = conn.cursor()

        # Проверяем что впечатление принадлежит пользователю
        cursor.execute("""
            SELECT id FROM impressions
            WHERE id = ? AND chat_id = ?
        """, (impression_id, chat_id))

        if not cursor.fetchone():
            logger.warning(f"Впечатление {impression_id} не найдено для пользователя {chat_id}")
            return False

        # Отвязываем впечатление
        cursor.execute("""
            UPDATE impressions
            SET entry_date = NULL
            WHERE id = ? AND chat_id = ?
        """, (impression_id, chat_id))

        conn.commit()
        logger.debug(f"Впечатление {impression_id} отвязано от записи")
        return True

    except sqlite3.Error as e:
        logger.error(f"Ошибка при отвязке впечатления {impression_id}: {e}")
        conn.rollback()
        return False


def get_entry_impressions(
    conn: sqlite3.Connection,
    chat_id: int,
    entry_date: str
) -> List[Dict[str, Any]]:
    """
    Получает все впечатления, привязанные к конкретной записи дня.

    Args:
        conn: соединение с базой данных
        chat_id: ID пользователя
        entry_date: дата записи (YYYY-MM-DD)

    Returns:
        List[Dict]: Список впечатлений, отсортированных по времени
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, chat_id, impression_text, impression_date, impression_time,
                   category, intensity, entry_date, created_at
            FROM impressions
            WHERE chat_id = ? AND entry_date = ?
            ORDER BY impression_time ASC
        """, (chat_id, entry_date))

        impressions = []
        for row in cursor.fetchall():
            impressions.append({
                'id': row[0],
                'chat_id': row[1],
                'text': row[2],
                'date': row[3],
                'time': row[4],
                'category': row[5],
                'intensity': row[6],
                'entry_date': row[7],
                'created_at': row[8]
            })

        return impressions

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении впечатлений для записи {entry_date}: {e}")
        return []
