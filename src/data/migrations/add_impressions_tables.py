"""
Миграция: Добавление таблиц для впечатлений (impressions).

Создает таблицы:
- impressions - основная таблица впечатлений
- impression_tags - теги для категоризации
- impression_tag_relations - связь многие-ко-многим
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def migrate(conn: sqlite3.Connection) -> None:
    """
    Выполняет миграцию: создает таблицы для впечатлений.

    Миграция идемпотентна - можно запускать несколько раз без ошибок.

    Args:
        conn: соединение с базой данных SQLite

    Raises:
        sqlite3.Error: при ошибке выполнения миграции
    """
    cursor = conn.cursor()

    try:
        # Включаем поддержку foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        # 1. Создание таблицы impressions (быстрые впечатления)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS impressions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            impression_text TEXT NOT NULL,
            impression_date TEXT NOT NULL,
            impression_time TEXT NOT NULL,
            category TEXT,
            intensity INTEGER,
            entry_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES users(chat_id),
            FOREIGN KEY (chat_id, entry_date) REFERENCES entries(chat_id, date)
        )
        ''')
        logger.info("Таблица impressions создана или уже существует")

        # 2. Создание таблицы impression_tags (теги для категоризации)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS impression_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            tag_name TEXT NOT NULL,
            tag_color TEXT,
            UNIQUE(chat_id, tag_name),
            FOREIGN KEY (chat_id) REFERENCES users(chat_id)
        )
        ''')
        logger.info("Таблица impression_tags создана или уже существует")

        # 3. Создание таблицы impression_tag_relations (связь многие-ко-многим)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS impression_tag_relations (
            impression_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (impression_id, tag_id),
            FOREIGN KEY (impression_id) REFERENCES impressions(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES impression_tags(id) ON DELETE CASCADE
        )
        ''')
        logger.info("Таблица impression_tag_relations создана или уже существует")

        # 4. Создание индексов для оптимизации запросов

        # Индекс для быстрого поиска впечатлений по пользователю и дате
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_impressions_chat_date
        ON impressions(chat_id, impression_date)
        ''')
        logger.info("Индекс idx_impressions_chat_date создан или уже существует")

        # Индекс для фильтрации по категории
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_impressions_category
        ON impressions(category)
        ''')
        logger.info("Индекс idx_impressions_category создан или уже существует")

        # Фиксируем изменения
        conn.commit()
        logger.info("Миграция impressions успешно завершена")

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Ошибка при выполнении миграции impressions: {e}")
        raise
