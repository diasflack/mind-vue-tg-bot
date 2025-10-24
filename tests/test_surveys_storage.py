"""
Тесты для слоя хранения опросов (Phase 2.4).
"""

import pytest
import sqlite3
import json
from datetime import datetime
from src.data.surveys_storage import (
    get_available_templates,
    get_template_by_id,
    get_template_by_name,
    get_template_questions,
    save_survey_response,
    get_user_survey_responses,
    get_responses_by_template,
    delete_survey_response
)


@pytest.fixture
def temp_db(mock_config):
    """Создает временную БД с таблицами для тестирования."""
    conn = sqlite3.connect(':memory:')
    conn.execute('PRAGMA foreign_keys = ON')

    # Создаем необходимые таблицы
    conn.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE survey_templates (
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
    ''')

    conn.execute('''
        CREATE TABLE survey_questions (
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
    ''')

    conn.execute('''
        CREATE TABLE survey_responses (
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
    ''')

    # Создаем индексы
    conn.execute('''
        CREATE INDEX idx_survey_responses_chat_date
        ON survey_responses(chat_id, response_date)
    ''')

    conn.execute('''
        CREATE INDEX idx_survey_questions_template
        ON survey_questions(template_id, order_index)
    ''')

    # Вставляем тестового пользователя
    conn.execute("INSERT INTO users (chat_id, username) VALUES (123, 'test_user')")

    # Создаем тестовый шаблон
    conn.execute("""
        INSERT INTO survey_templates (id, name, description, is_system, icon)
        VALUES (1, 'Test Survey', 'Test Description', 1, '📝')
    """)

    # Создаем вопросы для шаблона
    conn.execute("""
        INSERT INTO survey_questions
        (template_id, question_text, question_type, order_index, is_required, config)
        VALUES (1, 'Question 1', 'text', 1, 1, NULL)
    """)
    conn.execute("""
        INSERT INTO survey_questions
        (template_id, question_text, question_type, order_index, is_required, config)
        VALUES (1, 'Question 2', 'numeric', 2, 1, '{"min": 1, "max": 10}')
    """)

    conn.commit()
    yield conn
    conn.close()


def test_get_all_templates(temp_db):
    """Проверяет получение всех шаблонов."""
    templates = get_available_templates(temp_db)

    assert len(templates) >= 1
    assert templates[0]['name'] == 'Test Survey'
    assert templates[0]['description'] == 'Test Description'
    assert templates[0]['icon'] == '📝'
    assert templates[0]['is_system'] is True


def test_get_all_templates_only_active(temp_db):
    """Проверяет, что возвращаются только активные шаблоны."""
    # Создаем неактивный шаблон
    temp_db.execute("""
        INSERT INTO survey_templates (name, is_system, is_active)
        VALUES ('Inactive Survey', 1, 0)
    """)
    temp_db.commit()

    templates = get_available_templates(temp_db, only_active=True)

    # Должен вернуться только активный
    assert len(templates) == 1
    assert templates[0]['name'] == 'Test Survey'


def test_get_template_by_id(temp_db):
    """Проверяет получение шаблона по ID."""
    template = get_template_by_id(temp_db, 1)

    assert template is not None
    assert template['id'] == 1
    assert template['name'] == 'Test Survey'
    assert template['description'] == 'Test Description'


def test_get_template_by_id_not_found(temp_db):
    """Проверяет, что возвращается None для несуществующего ID."""
    template = get_template_by_id(temp_db, 999)
    assert template is None


def test_get_template_by_name(temp_db):
    """Проверяет получение шаблона по имени."""
    template = get_template_by_name(temp_db, 'Test Survey')

    assert template is not None
    assert template['id'] == 1
    assert template['name'] == 'Test Survey'


def test_get_template_by_name_not_found(temp_db):
    """Проверяет, что возвращается None для несуществующего имени."""
    template = get_template_by_name(temp_db, 'Non-existent Survey')
    assert template is None


def test_get_template_questions(temp_db):
    """Проверяет получение вопросов шаблона."""
    questions = get_template_questions(temp_db, 1)

    assert len(questions) == 2

    # Проверяем первый вопрос
    assert questions[0]['question_text'] == 'Question 1'
    assert questions[0]['question_type'] == 'text'
    assert questions[0]['order_index'] == 1
    assert questions[0]['is_required'] is True

    # Проверяем второй вопрос
    assert questions[1]['question_text'] == 'Question 2'
    assert questions[1]['question_type'] == 'numeric'
    assert questions[1]['order_index'] == 2
    assert questions[1]['config'] == '{"min": 1, "max": 10}'


def test_get_template_questions_ordered(temp_db):
    """Проверяет, что вопросы возвращаются в правильном порядке."""
    # Создаем шаблон с вопросами в случайном порядке
    temp_db.execute("""
        INSERT INTO survey_templates (id, name, is_system)
        VALUES (2, 'Ordered Survey', 1)
    """)

    temp_db.execute("""
        INSERT INTO survey_questions
        (template_id, question_text, question_type, order_index)
        VALUES (2, 'Third', 'text', 3)
    """)
    temp_db.execute("""
        INSERT INTO survey_questions
        (template_id, question_text, question_type, order_index)
        VALUES (2, 'First', 'text', 1)
    """)
    temp_db.execute("""
        INSERT INTO survey_questions
        (template_id, question_text, question_type, order_index)
        VALUES (2, 'Second', 'text', 2)
    """)
    temp_db.commit()

    questions = get_template_questions(temp_db, 2)

    assert len(questions) == 3
    assert questions[0]['question_text'] == 'First'
    assert questions[1]['question_text'] == 'Second'
    assert questions[2]['question_text'] == 'Third'


def test_save_response(temp_db):
    """Проверяет сохранение ответа на опрос."""
    response_data = {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:00:00',
        'answers': {
            '1': 'Answer to question 1',
            '2': '8'
        }
    }

    result = save_survey_response(temp_db, response_data)

    assert result is True

    # Проверяем, что данные сохранились
    cursor = temp_db.execute("""
        SELECT * FROM survey_responses
        WHERE chat_id = 123 AND template_id = 1
    """)
    row = cursor.fetchone()

    assert row is not None
    assert row[3] == '2025-01-15'  # response_date
    assert row[4] == '10:00:00'    # response_time
    # encrypted_data должен быть зашифрован


def test_encryption_decryption(temp_db):
    """Проверяет шифрование и дешифрование ответов."""
    response_data = {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:00:00',
        'answers': {
            '1': 'Secret answer',
            '2': '7'
        }
    }

    # Сохраняем
    save_survey_response(temp_db, response_data)

    # Получаем обратно
    responses = get_user_survey_responses(temp_db, 123)

    assert len(responses) >= 1
    response = responses[0]

    # Проверяем, что ответы расшифрованы правильно
    assert 'answers' in response
    answers = response['answers']
    assert answers['1'] == 'Secret answer'
    assert answers['2'] == '7'


def test_get_user_responses(temp_db):
    """Проверяет получение ответов пользователя."""
    # Создаем несколько ответов
    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:00:00',
        'answers': {'1': 'Answer 1'}
    })

    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-16',
        'response_time': '11:00:00',
        'answers': {'1': 'Answer 2'}
    })

    responses = get_user_survey_responses(temp_db, 123)

    assert len(responses) == 2


def test_get_user_responses_by_date(temp_db):
    """Проверяет фильтрацию ответов по дате."""
    # Создаем ответы на разные даты
    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:00:00',
        'answers': {'1': 'Answer 1'}
    })

    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-16',
        'response_time': '11:00:00',
        'answers': {'1': 'Answer 2'}
    })

    responses = get_user_survey_responses(temp_db, 123, date='2025-01-15')

    assert len(responses) == 1
    assert responses[0]['response_date'] == '2025-01-15'


def test_get_responses_by_template(temp_db):
    """Проверяет получение ответов по конкретному шаблону."""
    # Создаем второй шаблон
    temp_db.execute("""
        INSERT INTO survey_templates (id, name, is_system)
        VALUES (2, 'Another Survey', 1)
    """)
    temp_db.commit()

    # Создаем ответы для разных шаблонов
    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:00:00',
        'answers': {'1': 'Answer for template 1'}
    })

    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 2,
        'response_date': '2025-01-15',
        'response_time': '11:00:00',
        'answers': {'1': 'Answer for template 2'}
    })

    # Получаем только для первого шаблона
    responses = get_responses_by_template(temp_db, 123, 1)

    assert len(responses) == 1
    assert responses[0]['template_id'] == 1


def test_delete_response(temp_db):
    """Проверяет удаление ответа."""
    # Создаем ответ
    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:00:00',
        'answers': {'1': 'Answer'}
    })

    # Получаем ID ответа
    cursor = temp_db.execute("SELECT id FROM survey_responses WHERE chat_id = 123")
    response_id = cursor.fetchone()[0]

    # Удаляем
    result = delete_survey_response(temp_db, response_id, 123)

    assert result is True

    # Проверяем, что удалился
    cursor = temp_db.execute("SELECT COUNT(*) FROM survey_responses WHERE id = ?", (response_id,))
    assert cursor.fetchone()[0] == 0


def test_delete_response_wrong_user(temp_db):
    """Проверяет, что нельзя удалить чужой ответ."""
    # Создаем ответ
    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:00:00',
        'answers': {'1': 'Answer'}
    })

    # Получаем ID ответа
    cursor = temp_db.execute("SELECT id FROM survey_responses WHERE chat_id = 123")
    response_id = cursor.fetchone()[0]

    # Пытаемся удалить от имени другого пользователя
    result = delete_survey_response(temp_db, response_id, 999)

    assert result is False

    # Проверяем, что не удалился
    cursor = temp_db.execute("SELECT COUNT(*) FROM survey_responses WHERE id = ?", (response_id,))
    assert cursor.fetchone()[0] == 1


def test_get_responses_sorted_desc(temp_db):
    """Проверяет, что ответы сортируются по дате DESC (новые первыми)."""
    # Создаем ответы
    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:00:00',
        'answers': {'1': 'Old'}
    })

    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-17',
        'response_time': '10:00:00',
        'answers': {'1': 'New'}
    })

    save_survey_response(temp_db, {
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-16',
        'response_time': '10:00:00',
        'answers': {'1': 'Middle'}
    })

    responses = get_user_survey_responses(temp_db, 123)

    # Проверяем порядок (новые первыми)
    assert responses[0]['response_date'] == '2025-01-17'
    assert responses[1]['response_date'] == '2025-01-16'
    assert responses[2]['response_date'] == '2025-01-15'


def test_get_responses_empty(temp_db):
    """Проверяет, что возвращается пустой список если нет ответов."""
    responses = get_user_survey_responses(temp_db, 999)
    assert responses == []
