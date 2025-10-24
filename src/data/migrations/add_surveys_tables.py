"""
Миграция для добавления таблиц системы опросов.

Создает таблицы:
- survey_templates: Шаблоны опросов (системные и пользовательские)
- survey_questions: Вопросы в шаблонах
- survey_responses: Ответы на опросы (зашифрованные)
- user_survey_preferences: Предпочтения пользователей по опросам
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def migrate(conn: sqlite3.Connection) -> None:
    """
    Выполняет миграцию: создает таблицы для системы опросов.

    Args:
        conn: Соединение с базой данных SQLite

    Raises:
        sqlite3.Error: При ошибках работы с БД
    """
    cursor = conn.cursor()

    try:
        # Проверяем, существует ли уже таблица survey_templates
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='survey_templates'
        """)
        if cursor.fetchone():
            logger.info("Таблицы опросов уже существуют, пропускаем миграцию")
            return

        logger.info("Создание таблиц для системы опросов...")

        # 1. Таблица шаблонов опросов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS survey_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                is_system BOOLEAN DEFAULT 0,
                creator_chat_id INTEGER,
                icon TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (creator_chat_id) REFERENCES users(chat_id)
            )
        """)
        logger.info("✓ Таблица survey_templates создана")

        # 2. Таблица вопросов шаблона
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS survey_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                order_index INTEGER NOT NULL,
                is_required BOOLEAN DEFAULT 1,
                config TEXT,
                help_text TEXT,
                FOREIGN KEY (template_id) REFERENCES survey_templates(id) ON DELETE CASCADE
            )
        """)
        logger.info("✓ Таблица survey_questions создана")

        # 3. Таблица ответов на опросы
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS survey_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                template_id INTEGER NOT NULL,
                response_date TEXT NOT NULL,
                response_time TEXT NOT NULL,
                encrypted_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id),
                FOREIGN KEY (template_id) REFERENCES survey_templates(id)
            )
        """)
        logger.info("✓ Таблица survey_responses создана")

        # 4. Таблица предпочтений пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_survey_preferences (
                chat_id INTEGER NOT NULL,
                template_id INTEGER NOT NULL,
                is_favorite BOOLEAN DEFAULT 0,
                notification_enabled BOOLEAN DEFAULT 0,
                notification_time TEXT,
                PRIMARY KEY (chat_id, template_id),
                FOREIGN KEY (chat_id) REFERENCES users(chat_id),
                FOREIGN KEY (template_id) REFERENCES survey_templates(id) ON DELETE CASCADE
            )
        """)
        logger.info("✓ Таблица user_survey_preferences создана")

        # 5. Индексы для оптимизации запросов
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_survey_responses_chat_date
            ON survey_responses(chat_id, response_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_survey_responses_template
            ON survey_responses(template_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_survey_questions_template
            ON survey_questions(template_id, order_index)
        """)

        logger.info("✓ Индексы созданы")

        conn.commit()
        logger.info("Миграция системы опросов завершена успешно")

    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Ошибка при создании таблиц опросов: {e}")
        raise


if __name__ == '__main__':
    # Для тестирования миграции
    logging.basicConfig(level=logging.INFO)

    from src.data.storage import _get_db_connection

    conn = _get_db_connection()
    try:
        migrate(conn)
        print("Миграция выполнена успешно!")
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        conn.close()
