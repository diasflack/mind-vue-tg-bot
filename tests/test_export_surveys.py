"""
Тесты для экспорта ответов на опросы (Phase 5.4).
"""

import pytest
import sqlite3
import json
import csv
from io import StringIO

from src.data.export import export_survey_responses_csv, export_survey_responses_json


@pytest.fixture
def temp_db(mock_config):
    """Создает временную БД с опросами и ответами."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Создаем таблицу users
    cursor.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT
        )
    ''')

    # Создаем таблицу survey_templates
    cursor.execute('''
        CREATE TABLE survey_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Создаем таблицу survey_questions
    cursor.execute('''
        CREATE TABLE survey_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL,
            question_config TEXT,
            order_num INTEGER,
            FOREIGN KEY (template_id) REFERENCES survey_templates(id)
        )
    ''')

    # Создаем таблицу survey_responses
    cursor.execute('''
        CREATE TABLE survey_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            response_date TEXT NOT NULL,
            response_time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES users(chat_id),
            FOREIGN KEY (template_id) REFERENCES survey_templates(id)
        )
    ''')

    # Создаем таблицу survey_answers
    cursor.execute('''
        CREATE TABLE survey_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            response_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer_text TEXT,
            answer_numeric REAL,
            FOREIGN KEY (response_id) REFERENCES survey_responses(id),
            FOREIGN KEY (question_id) REFERENCES survey_questions(id)
        )
    ''')

    # Добавляем тестовые данные
    cursor.execute('INSERT INTO users (chat_id, username) VALUES (?, ?)', (12345, 'testuser'))

    # Создаем опрос "Настроение"
    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, created_by)
        VALUES (1, 'Настроение', 'Ежедневная оценка настроения', 12345)
    ''')

    # Добавляем вопросы
    cursor.execute('''
        INSERT INTO survey_questions (template_id, question_text, question_type, question_config, order_num)
        VALUES (1, 'Как настроение?', 'numeric', '{"min": 1, "max": 10}', 1)
    ''')
    cursor.execute('''
        INSERT INTO survey_questions (template_id, question_text, question_type, question_config, order_num)
        VALUES (1, 'Что делал сегодня?', 'choice', '{"choices": ["Работал", "Отдыхал", "Учился"]}', 2)
    ''')

    # Создаем опрос "Тревога"
    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, created_by)
        VALUES (2, 'Тревога', 'Оценка уровня тревоги', 12345)
    ''')

    cursor.execute('''
        INSERT INTO survey_questions (template_id, question_text, question_type, question_config, order_num)
        VALUES (2, 'Уровень тревоги', 'numeric', '{"min": 0, "max": 10}', 1)
    ''')

    # Добавляем ответы для опроса "Настроение"
    cursor.execute('''
        INSERT INTO survey_responses (id, chat_id, template_id, response_date, response_time)
        VALUES (1, 12345, 1, '2025-10-20', '09:00:00')
    ''')
    cursor.execute('''
        INSERT INTO survey_answers (response_id, question_id, answer_numeric)
        VALUES (1, 1, 8)
    ''')
    cursor.execute('''
        INSERT INTO survey_answers (response_id, question_id, answer_text)
        VALUES (1, 2, 'Работал')
    ''')

    cursor.execute('''
        INSERT INTO survey_responses (id, chat_id, template_id, response_date, response_time)
        VALUES (2, 12345, 1, '2025-10-21', '10:00:00')
    ''')
    cursor.execute('''
        INSERT INTO survey_answers (response_id, question_id, answer_numeric)
        VALUES (2, 1, 6)
    ''')
    cursor.execute('''
        INSERT INTO survey_answers (response_id, question_id, answer_text)
        VALUES (2, 2, 'Отдыхал')
    ''')

    cursor.execute('''
        INSERT INTO survey_responses (id, chat_id, template_id, response_date, response_time)
        VALUES (3, 12345, 1, '2025-10-22', '11:00:00')
    ''')
    cursor.execute('''
        INSERT INTO survey_answers (response_id, question_id, answer_numeric)
        VALUES (3, 1, 7)
    ''')
    cursor.execute('''
        INSERT INTO survey_answers (response_id, question_id, answer_text)
        VALUES (3, 2, 'Учился')
    ''')

    # Добавляем ответ для опроса "Тревога"
    cursor.execute('''
        INSERT INTO survey_responses (id, chat_id, template_id, response_date, response_time)
        VALUES (4, 12345, 2, '2025-10-20', '12:00:00')
    ''')
    cursor.execute('''
        INSERT INTO survey_answers (response_id, question_id, answer_numeric)
        VALUES (4, 3, 5)
    ''')

    conn.commit()
    yield conn
    conn.close()


class TestExportSurveyResponsesCSV:
    """Тесты экспорта ответов на опросы в CSV."""

    def test_export_survey_responses_csv(self, temp_db):
        """Экспорт ответов на конкретный опрос в CSV."""
        csv_data = export_survey_responses_csv(
            temp_db,
            chat_id=12345,
            survey_name='Настроение'
        )

        # Проверяем что получили строку
        assert isinstance(csv_data, str)
        assert len(csv_data) > 0

        # Парсим CSV
        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)

        # Должно быть 3 ответа
        assert len(rows) == 3

        # Проверяем наличие колонок
        assert 'response_date' in rows[0]
        assert 'response_time' in rows[0]
        assert 'Как настроение?' in rows[0]
        assert 'Что делал сегодня?' in rows[0]

        # Проверяем данные первой строки
        assert rows[0]['response_date'] == '2025-10-20'
        assert rows[0]['Как настроение?'] == '8.0'
        assert rows[0]['Что делал сегодня?'] == 'Работал'

    def test_export_survey_responses_csv_with_date_filter(self, temp_db):
        """Экспорт с фильтром по дате."""
        csv_data = export_survey_responses_csv(
            temp_db,
            chat_id=12345,
            survey_name='Настроение',
            from_date='2025-10-21',
            to_date='2025-10-22'
        )

        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)

        # Должно быть 2 ответа (21 и 22 октября)
        assert len(rows) == 2

    def test_export_survey_responses_csv_nonexistent_survey(self, temp_db):
        """Экспорт несуществующего опроса."""
        csv_data = export_survey_responses_csv(
            temp_db,
            chat_id=12345,
            survey_name='НесуществующийОпрос'
        )

        # Должен вернуть None или пустой результат
        assert csv_data is None or csv_data == ''

    def test_export_survey_responses_csv_empty_result(self, temp_db):
        """Экспорт когда нет ответов в указанном диапазоне."""
        csv_data = export_survey_responses_csv(
            temp_db,
            chat_id=12345,
            survey_name='Настроение',
            from_date='2025-12-01'
        )

        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)

        assert len(rows) == 0


class TestExportSurveyResponsesJSON:
    """Тесты экспорта ответов на опросы в JSON."""

    def test_export_survey_responses_json(self, temp_db):
        """Экспорт ответов на опрос в JSON."""
        json_data = export_survey_responses_json(
            temp_db,
            chat_id=12345,
            survey_name='Настроение'
        )

        # Проверяем что получили строку
        assert isinstance(json_data, str)

        # Парсим JSON
        data = json.loads(json_data)

        # Проверяем структуру
        assert 'survey_name' in data
        assert 'responses' in data
        assert 'count' in data
        assert 'exported_at' in data

        # Проверяем данные
        assert data['survey_name'] == 'Настроение'
        assert data['count'] == 3
        assert len(data['responses']) == 3

        # Проверяем первый ответ
        first = data['responses'][0]
        assert first['date'] == '2025-10-20'
        assert 'answers' in first
        assert len(first['answers']) == 2

    def test_export_survey_responses_json_with_date_filter(self, temp_db):
        """Экспорт в JSON с фильтром по дате."""
        json_data = export_survey_responses_json(
            temp_db,
            chat_id=12345,
            survey_name='Настроение',
            from_date='2025-10-21'
        )

        data = json.loads(json_data)

        # Должно быть 2 ответа
        assert data['count'] == 2

    def test_export_survey_responses_json_includes_questions(self, temp_db):
        """JSON экспорт включает информацию о вопросах."""
        json_data = export_survey_responses_json(
            temp_db,
            chat_id=12345,
            survey_name='Настроение'
        )

        data = json.loads(json_data)

        # Проверяем что есть структура вопросов
        first_response = data['responses'][0]
        answers = first_response['answers']

        assert any('Как настроение?' in str(a) for a in answers)
        assert any('Что делал сегодня?' in str(a) for a in answers)

    def test_export_survey_responses_json_nonexistent_survey(self, temp_db):
        """Экспорт несуществующего опроса в JSON."""
        json_data = export_survey_responses_json(
            temp_db,
            chat_id=12345,
            survey_name='НесуществующийОпрос'
        )

        # Должен вернуть None или валидный JSON с пустым результатом
        if json_data:
            data = json.loads(json_data)
            assert data['count'] == 0 or 'error' in data
