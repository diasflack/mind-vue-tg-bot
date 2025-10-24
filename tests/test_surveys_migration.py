"""
Тесты для миграции базы данных для системы опросов (Phase 2.1).
"""

import pytest
import sqlite3
from src.data.migrations.add_surveys_tables import migrate


@pytest.fixture
def temp_db():
    """Создает временную БД для тестирования."""
    conn = sqlite3.connect(':memory:')
    conn.execute('PRAGMA foreign_keys = ON')

    # Создаем таблицу users для внешних ключей
    conn.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    yield conn
    conn.close()


def test_survey_templates_table_created(temp_db):
    """Проверяет создание таблицы survey_templates."""
    migrate(temp_db)

    cursor = temp_db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='survey_templates'
    """)
    assert cursor.fetchone() is not None

    # Проверяем структуру таблицы
    cursor = temp_db.execute("PRAGMA table_info(survey_templates)")
    columns = {row[1] for row in cursor.fetchall()}

    expected_columns = {
        'id', 'name', 'description', 'is_system',
        'creator_chat_id', 'icon', 'created_at', 'is_active'
    }
    assert expected_columns.issubset(columns)


def test_survey_questions_table_created(temp_db):
    """Проверяет создание таблицы survey_questions."""
    migrate(temp_db)

    cursor = temp_db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='survey_questions'
    """)
    assert cursor.fetchone() is not None

    # Проверяем структуру таблицы
    cursor = temp_db.execute("PRAGMA table_info(survey_questions)")
    columns = {row[1] for row in cursor.fetchall()}

    expected_columns = {
        'id', 'template_id', 'question_text', 'question_type',
        'order_index', 'is_required', 'config', 'help_text'
    }
    assert expected_columns.issubset(columns)


def test_survey_responses_table_created(temp_db):
    """Проверяет создание таблицы survey_responses."""
    migrate(temp_db)

    cursor = temp_db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='survey_responses'
    """)
    assert cursor.fetchone() is not None

    # Проверяем структуру таблицы
    cursor = temp_db.execute("PRAGMA table_info(survey_responses)")
    columns = {row[1] for row in cursor.fetchall()}

    expected_columns = {
        'id', 'chat_id', 'template_id', 'response_date',
        'response_time', 'encrypted_data', 'created_at'
    }
    assert expected_columns.issubset(columns)


def test_user_survey_preferences_table_created(temp_db):
    """Проверяет создание таблицы user_survey_preferences."""
    migrate(temp_db)

    cursor = temp_db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='user_survey_preferences'
    """)
    assert cursor.fetchone() is not None

    # Проверяем структуру таблицы
    cursor = temp_db.execute("PRAGMA table_info(user_survey_preferences)")
    columns = {row[1] for row in cursor.fetchall()}

    expected_columns = {
        'chat_id', 'template_id', 'is_favorite',
        'notification_enabled', 'notification_time'
    }
    assert expected_columns.issubset(columns)


def test_indexes_created(temp_db):
    """Проверяет создание индексов."""
    migrate(temp_db)

    cursor = temp_db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name IN (
            'idx_survey_responses_chat_date',
            'idx_survey_responses_template',
            'idx_survey_questions_template'
        )
    """)
    indexes = [row[0] for row in cursor.fetchall()]

    assert 'idx_survey_responses_chat_date' in indexes
    assert 'idx_survey_responses_template' in indexes
    assert 'idx_survey_questions_template' in indexes


def test_foreign_keys_constraints(temp_db):
    """Проверяет работу внешних ключей."""
    migrate(temp_db)

    # Вставляем тестового пользователя
    temp_db.execute("INSERT INTO users (chat_id, username) VALUES (123, 'test_user')")

    # Создаем шаблон опроса
    temp_db.execute("""
        INSERT INTO survey_templates (id, name, is_system, creator_chat_id)
        VALUES (1, 'Test Survey', 0, 123)
    """)

    # Создаем вопрос для шаблона
    temp_db.execute("""
        INSERT INTO survey_questions
        (template_id, question_text, question_type, order_index)
        VALUES (1, 'Test Question', 'text', 1)
    """)

    # Создаем ответ
    temp_db.execute("""
        INSERT INTO survey_responses
        (chat_id, template_id, response_date, response_time, encrypted_data)
        VALUES (123, 1, '2025-01-15', '10:00:00', 'encrypted')
    """)

    temp_db.commit()

    # Проверяем, что данные вставлены
    cursor = temp_db.execute("SELECT COUNT(*) FROM survey_questions")
    assert cursor.fetchone()[0] == 1

    cursor = temp_db.execute("SELECT COUNT(*) FROM survey_responses")
    assert cursor.fetchone()[0] == 1


def test_cascade_delete_questions(temp_db):
    """Проверяет CASCADE DELETE для вопросов при удалении шаблона."""
    migrate(temp_db)

    # Создаем тестового пользователя
    temp_db.execute("INSERT INTO users (chat_id, username) VALUES (123, 'test_user')")

    # Создаем шаблон
    temp_db.execute("""
        INSERT INTO survey_templates (id, name, is_system, creator_chat_id)
        VALUES (1, 'Test Survey', 0, 123)
    """)

    # Создаем вопросы
    temp_db.execute("""
        INSERT INTO survey_questions
        (template_id, question_text, question_type, order_index)
        VALUES (1, 'Question 1', 'text', 1)
    """)
    temp_db.execute("""
        INSERT INTO survey_questions
        (template_id, question_text, question_type, order_index)
        VALUES (1, 'Question 2', 'numeric', 2)
    """)
    temp_db.commit()

    # Проверяем, что вопросы созданы
    cursor = temp_db.execute("SELECT COUNT(*) FROM survey_questions")
    assert cursor.fetchone()[0] == 2

    # Удаляем шаблон
    temp_db.execute("DELETE FROM survey_templates WHERE id = 1")
    temp_db.commit()

    # Проверяем, что вопросы тоже удалились (CASCADE DELETE)
    cursor = temp_db.execute("SELECT COUNT(*) FROM survey_questions")
    assert cursor.fetchone()[0] == 0


def test_cascade_delete_preferences(temp_db):
    """Проверяет CASCADE DELETE для предпочтений при удалении шаблона."""
    migrate(temp_db)

    # Создаем тестового пользователя
    temp_db.execute("INSERT INTO users (chat_id, username) VALUES (123, 'test_user')")

    # Создаем шаблон
    temp_db.execute("""
        INSERT INTO survey_templates (id, name, is_system)
        VALUES (1, 'Test Survey', 1)
    """)

    # Создаем предпочтения
    temp_db.execute("""
        INSERT INTO user_survey_preferences
        (chat_id, template_id, is_favorite)
        VALUES (123, 1, 1)
    """)
    temp_db.commit()

    # Проверяем, что предпочтения созданы
    cursor = temp_db.execute("SELECT COUNT(*) FROM user_survey_preferences")
    assert cursor.fetchone()[0] == 1

    # Удаляем шаблон
    temp_db.execute("DELETE FROM survey_templates WHERE id = 1")
    temp_db.commit()

    # Проверяем, что предпочтения тоже удалились (CASCADE DELETE)
    cursor = temp_db.execute("SELECT COUNT(*) FROM user_survey_preferences")
    assert cursor.fetchone()[0] == 0


def test_migration_is_idempotent(temp_db):
    """Проверяет, что миграцию можно запустить несколько раз без ошибок."""
    # Первый запуск
    migrate(temp_db)

    # Проверяем, что таблицы созданы
    cursor = temp_db.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='table' AND name IN (
            'survey_templates', 'survey_questions',
            'survey_responses', 'user_survey_preferences'
        )
    """)
    assert cursor.fetchone()[0] == 4

    # Второй запуск - не должен упасть
    migrate(temp_db)

    # Таблицы по-прежнему существуют
    cursor = temp_db.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='table' AND name IN (
            'survey_templates', 'survey_questions',
            'survey_responses', 'user_survey_preferences'
        )
    """)
    assert cursor.fetchone()[0] == 4


def test_primary_key_constraints(temp_db):
    """Проверяет работу PRIMARY KEY в user_survey_preferences."""
    migrate(temp_db)

    # Создаем тестового пользователя
    temp_db.execute("INSERT INTO users (chat_id, username) VALUES (123, 'test_user')")

    # Создаем шаблон
    temp_db.execute("""
        INSERT INTO survey_templates (id, name, is_system)
        VALUES (1, 'Test Survey', 1)
    """)

    # Первая вставка - OK
    temp_db.execute("""
        INSERT INTO user_survey_preferences
        (chat_id, template_id, is_favorite)
        VALUES (123, 1, 1)
    """)
    temp_db.commit()

    # Вторая вставка с теми же ключами - должна упасть
    with pytest.raises(sqlite3.IntegrityError):
        temp_db.execute("""
            INSERT INTO user_survey_preferences
            (chat_id, template_id, is_favorite)
            VALUES (123, 1, 0)
        """)
        temp_db.commit()
