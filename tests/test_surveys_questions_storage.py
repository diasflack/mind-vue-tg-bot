"""
Тесты для функций работы с вопросами в пользовательских шаблонах (Phase 3.2).
"""

import pytest
import sqlite3
from datetime import datetime

from src.data.surveys_storage import (
    create_user_template,
    add_question_to_template,
    update_question,
    delete_question,
    reorder_questions,
    get_template_questions
)


@pytest.fixture
def mock_config(monkeypatch):
    """Мокируем конфигурацию для шифрования."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_for_salt")


@pytest.fixture
def temp_db(mock_config):
    """Создает временную БД с таблицами для тестирования."""
    conn = sqlite3.connect(':memory:')
    conn.execute('PRAGMA foreign_keys = ON')

    # Создаем таблицы
    conn.execute("""
        CREATE TABLE survey_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            is_system INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_by INTEGER,
            icon TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE survey_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL,
            config TEXT,
            order_index INTEGER NOT NULL,
            is_required INTEGER DEFAULT 1,
            FOREIGN KEY (template_id) REFERENCES survey_templates(id) ON DELETE CASCADE
        )
    """)

    conn.commit()

    yield conn

    conn.close()


class TestAddQuestionToTemplate:
    """Тесты добавления вопросов к шаблону."""

    def test_add_question_success(self, temp_db):
        """Успешное добавление вопроса."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Тест", "Описание")

        question_data = {
            'question_text': 'Как ваше настроение?',
            'question_type': 'text'
        }

        question_id = add_question_to_template(temp_db, template_id, chat_id, question_data)

        assert question_id is not None
        assert question_id > 0

        # Проверяем что вопрос добавлен
        questions = get_template_questions(temp_db, template_id)
        assert len(questions) == 1
        assert questions[0]['question_text'] == 'Как ваше настроение?'
        assert questions[0]['question_type'] == 'text'
        assert questions[0]['order_index'] == 1

    def test_add_question_with_config(self, temp_db):
        """Добавление вопроса с конфигурацией."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Тест", "Описание")

        question_data = {
            'question_text': 'Оцените от 1 до 10',
            'question_type': 'numeric',
            'config': '{"min": 1, "max": 10}'
        }

        question_id = add_question_to_template(temp_db, template_id, chat_id, question_data)

        assert question_id is not None

        questions = get_template_questions(temp_db, template_id)
        assert questions[0]['config'] == '{"min": 1, "max": 10}'

    def test_add_question_order_index_increments(self, temp_db):
        """Порядковый номер автоматически увеличивается."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Тест", "Описание")

        # Добавляем 3 вопроса
        for i in range(3):
            question_data = {
                'question_text': f'Вопрос {i+1}',
                'question_type': 'text'
            }
            add_question_to_template(temp_db, template_id, chat_id, question_data)

        questions = get_template_questions(temp_db, template_id)
        assert len(questions) == 3
        assert questions[0]['order_index'] == 1
        assert questions[1]['order_index'] == 2
        assert questions[2]['order_index'] == 3

    def test_add_question_not_owner(self, temp_db):
        """Попытка добавить вопрос к чужому шаблону."""
        owner_id = 111
        other_id = 222

        template_id = create_user_template(temp_db, owner_id, "Тест", "Описание")

        question_data = {
            'question_text': 'Вопрос',
            'question_type': 'text'
        }

        question_id = add_question_to_template(temp_db, template_id, other_id, question_data)

        assert question_id is None

    def test_add_question_to_system_template(self, temp_db):
        """Попытка добавить вопрос к системному шаблону."""
        # Создаем системный шаблон
        temp_db.execute("""
            INSERT INTO survey_templates
            (name, description, is_system, is_active, created_by, created_at)
            VALUES ('Системный', 'Описание', 1, 1, NULL, ?)
        """, (datetime.now().isoformat(),))
        temp_db.commit()
        template_id = temp_db.execute("SELECT last_insert_rowid()").fetchone()[0]

        question_data = {
            'question_text': 'Вопрос',
            'question_type': 'text'
        }

        question_id = add_question_to_template(temp_db, template_id, 12345, question_data)

        assert question_id is None

    def test_add_question_limit_reached(self, temp_db):
        """Достижение лимита вопросов (30)."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Тест", "Описание")

        # Добавляем 30 вопросов
        for i in range(30):
            question_data = {
                'question_text': f'Вопрос {i+1}',
                'question_type': 'text'
            }
            add_question_to_template(temp_db, template_id, chat_id, question_data)

        # Пытаемся добавить 31-й
        question_data = {
            'question_text': 'Вопрос 31',
            'question_type': 'text'
        }
        question_id = add_question_to_template(temp_db, template_id, chat_id, question_data)

        assert question_id is None

        # Проверяем что осталось 30 вопросов
        questions = get_template_questions(temp_db, template_id)
        assert len(questions) == 30


class TestUpdateQuestion:
    """Тесты обновления вопросов."""

    def test_update_question_text(self, temp_db):
        """Успешное обновление текста вопроса."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Тест", "Описание")

        question_data = {
            'question_text': 'Старый текст',
            'question_type': 'text'
        }
        question_id = add_question_to_template(temp_db, template_id, chat_id, question_data)

        result = update_question(
            temp_db, question_id, template_id, chat_id,
            question_text='Новый текст'
        )

        assert result is True

        questions = get_template_questions(temp_db, template_id)
        assert questions[0]['question_text'] == 'Новый текст'

    def test_update_question_type_and_config(self, temp_db):
        """Обновление типа и конфигурации вопроса."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Тест", "Описание")

        question_data = {
            'question_text': 'Вопрос',
            'question_type': 'text'
        }
        question_id = add_question_to_template(temp_db, template_id, chat_id, question_data)

        result = update_question(
            temp_db, question_id, template_id, chat_id,
            question_type='numeric',
            config='{"min": 0, "max": 100}'
        )

        assert result is True

        questions = get_template_questions(temp_db, template_id)
        assert questions[0]['question_type'] == 'numeric'
        assert questions[0]['config'] == '{"min": 0, "max": 100}'

    def test_update_question_not_owner(self, temp_db):
        """Попытка обновить вопрос в чужом шаблоне."""
        owner_id = 111
        other_id = 222

        template_id = create_user_template(temp_db, owner_id, "Тест", "Описание")
        question_data = {'question_text': 'Вопрос', 'question_type': 'text'}
        question_id = add_question_to_template(temp_db, template_id, owner_id, question_data)

        result = update_question(
            temp_db, question_id, template_id, other_id,
            question_text='Новый текст'
        )

        assert result is False

    def test_update_question_system_template(self, temp_db):
        """Попытка обновить вопрос в системном шаблоне."""
        # Создаем системный шаблон с вопросом
        temp_db.execute("""
            INSERT INTO survey_templates
            (id, name, description, is_system, is_active, created_by, created_at)
            VALUES (1, 'Системный', 'Описание', 1, 1, NULL, ?)
        """, (datetime.now().isoformat(),))
        temp_db.execute("""
            INSERT INTO survey_questions
            (id, template_id, question_text, question_type, order_index)
            VALUES (1, 1, 'Вопрос', 'text', 1)
        """)
        temp_db.commit()

        result = update_question(
            temp_db, 1, 1, 12345,
            question_text='Новый текст'
        )

        assert result is False


class TestDeleteQuestion:
    """Тесты удаления вопросов."""

    def test_delete_question_success(self, temp_db):
        """Успешное удаление вопроса."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Тест", "Описание")

        question_data = {'question_text': 'Вопрос', 'question_type': 'text'}
        question_id = add_question_to_template(temp_db, template_id, chat_id, question_data)

        result = delete_question(temp_db, question_id, template_id, chat_id)

        assert result is True

        questions = get_template_questions(temp_db, template_id)
        assert len(questions) == 0

    def test_delete_question_reorders_remaining(self, temp_db):
        """Удаление вопроса пересчитывает order_index оставшихся."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Тест", "Описание")

        # Добавляем 3 вопроса
        q1 = add_question_to_template(temp_db, template_id, chat_id,
                                      {'question_text': 'Q1', 'question_type': 'text'})
        q2 = add_question_to_template(temp_db, template_id, chat_id,
                                      {'question_text': 'Q2', 'question_type': 'text'})
        q3 = add_question_to_template(temp_db, template_id, chat_id,
                                      {'question_text': 'Q3', 'question_type': 'text'})

        # Удаляем второй вопрос
        delete_question(temp_db, q2, template_id, chat_id)

        questions = get_template_questions(temp_db, template_id)
        assert len(questions) == 2
        assert questions[0]['question_text'] == 'Q1'
        assert questions[0]['order_index'] == 1
        assert questions[1]['question_text'] == 'Q3'
        assert questions[1]['order_index'] == 2  # Был 3, стал 2

    def test_delete_question_not_owner(self, temp_db):
        """Попытка удалить вопрос из чужого шаблона."""
        owner_id = 111
        other_id = 222

        template_id = create_user_template(temp_db, owner_id, "Тест", "Описание")
        question_data = {'question_text': 'Вопрос', 'question_type': 'text'}
        question_id = add_question_to_template(temp_db, template_id, owner_id, question_data)

        result = delete_question(temp_db, question_id, template_id, other_id)

        assert result is False

        # Вопрос не удален
        questions = get_template_questions(temp_db, template_id)
        assert len(questions) == 1


class TestReorderQuestions:
    """Тесты изменения порядка вопросов."""

    def test_reorder_questions_success(self, temp_db):
        """Успешное изменение порядка."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Тест", "Описание")

        # Добавляем 3 вопроса
        q1 = add_question_to_template(temp_db, template_id, chat_id,
                                      {'question_text': 'Q1', 'question_type': 'text'})
        q2 = add_question_to_template(temp_db, template_id, chat_id,
                                      {'question_text': 'Q2', 'question_type': 'text'})
        q3 = add_question_to_template(temp_db, template_id, chat_id,
                                      {'question_text': 'Q3', 'question_type': 'text'})

        # Меняем порядок: Q3, Q1, Q2
        new_order = [q3, q1, q2]
        result = reorder_questions(temp_db, template_id, chat_id, new_order)

        assert result is True

        questions = get_template_questions(temp_db, template_id)
        assert questions[0]['question_text'] == 'Q3'
        assert questions[0]['order_index'] == 1
        assert questions[1]['question_text'] == 'Q1'
        assert questions[1]['order_index'] == 2
        assert questions[2]['question_text'] == 'Q2'
        assert questions[2]['order_index'] == 3

    def test_reorder_questions_invalid_list(self, temp_db):
        """Попытка изменить порядок с некорректным списком."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Тест", "Описание")

        q1 = add_question_to_template(temp_db, template_id, chat_id,
                                      {'question_text': 'Q1', 'question_type': 'text'})
        q2 = add_question_to_template(temp_db, template_id, chat_id,
                                      {'question_text': 'Q2', 'question_type': 'text'})

        # Некорректный список (пропущен вопрос)
        new_order = [q1]
        result = reorder_questions(temp_db, template_id, chat_id, new_order)

        assert result is False

    def test_reorder_questions_not_owner(self, temp_db):
        """Попытка изменить порядок в чужом шаблоне."""
        owner_id = 111
        other_id = 222

        template_id = create_user_template(temp_db, owner_id, "Тест", "Описание")
        q1 = add_question_to_template(temp_db, template_id, owner_id,
                                      {'question_text': 'Q1', 'question_type': 'text'})
        q2 = add_question_to_template(temp_db, template_id, owner_id,
                                      {'question_text': 'Q2', 'question_type': 'text'})

        new_order = [q2, q1]
        result = reorder_questions(temp_db, template_id, other_id, new_order)

        assert result is False
