"""
Миграция для добавления timezone_offset в таблицу users (Phase 5.2).

Добавляет поддержку часовых поясов для корректной работы напоминаний.
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def migrate(conn: sqlite3.Connection) -> None:
    """
    Добавляет колонку timezone_offset в таблицу users.

    Args:
        conn: соединение с БД
    """
    cursor = conn.cursor()

    try:
        # Проверяем существует ли колонка
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'timezone_offset' not in columns:
            logger.info("Добавление колонки timezone_offset в таблицу users...")

            # Добавляем колонку timezone_offset (по умолчанию 0 - UTC)
            cursor.execute("""
                ALTER TABLE users ADD COLUMN timezone_offset INTEGER DEFAULT 0
            """)

            conn.commit()
            logger.info("✓ Колонка timezone_offset успешно добавлена")
        else:
            logger.info("✓ Колонка timezone_offset уже существует")

    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении timezone_offset: {e}")
        conn.rollback()
        raise


if __name__ == '__main__':
    # Для ручного запуска миграции
    logging.basicConfig(level=logging.INFO)
    from src.data.storage import _get_db_connection

    conn = _get_db_connection()
    migrate(conn)
    logger.info("Миграция успешно выполнена!")
