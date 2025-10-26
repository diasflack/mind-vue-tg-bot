"""
Тесты для функций работы с пользовательскими шаблонами опросов (Phase 3).
"""

import pytest
import sqlite3
from datetime import datetime

from src.data.surveys_storage import (
    create_user_template,
    update_template,
    delete_template,
    get_user_templates,
    count_user_templates
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

    conn.execute("""
        CREATE TABLE survey_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            response_date TEXT NOT NULL,
            response_time TEXT NOT NULL,
            encrypted_data TEXT NOT NULL,
            FOREIGN KEY (template_id) REFERENCES survey_templates(id) ON DELETE CASCADE
        )
    """)

    conn.commit()

    yield conn

    conn.close()


class TestCreateUserTemplate:
    """Тесты создания пользовательских шаблонов."""

    def test_create_template_success(self, temp_db):
        """Успешное создание шаблона."""
        chat_id = 12345
        name = "Мой опрос"
        description = "Описание опроса"

        template_id = create_user_template(temp_db, chat_id, name, description)

        assert template_id is not None
        assert template_id > 0

        # Проверяем что шаблон создан
        cursor = temp_db.execute(
            "SELECT * FROM survey_templates WHERE id = ?",
            (template_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        assert row[1] == name  # name
        assert row[2] == description  # description
        assert row[3] == 0  # is_system
        assert row[4] == 0  # is_active (по умолчанию False)
        assert row[5] == chat_id  # created_by

    def test_create_template_duplicate_name(self, temp_db):
        """Попытка создать шаблон с существующим названием."""
        chat_id = 12345
        name = "Мой опрос"

        # Создаем первый шаблон
        template_id1 = create_user_template(temp_db, chat_id, name, "Описание 1")
        assert template_id1 is not None

        # Пытаемся создать второй с тем же названием
        template_id2 = create_user_template(temp_db, chat_id, name, "Описание 2")
        assert template_id2 is None

    def test_create_template_limit_reached(self, temp_db):
        """Проверка лимита шаблонов (максимум 20)."""
        chat_id = 12345

        # Создаем 20 шаблонов
        for i in range(20):
            template_id = create_user_template(
                temp_db, chat_id, f"Опрос {i}", f"Описание {i}"
            )
            assert template_id is not None

        # Пытаемся создать 21-й
        template_id = create_user_template(temp_db, chat_id, "Опрос 21", "Описание")
        assert template_id is None

    def test_create_template_different_users_same_name(self, temp_db):
        """Разные пользователи могут создавать шаблоны с одинаковыми названиями."""
        name = "Общий опрос"

        template_id1 = create_user_template(temp_db, 111, name, "Описание 1")
        template_id2 = create_user_template(temp_db, 222, name, "Описание 2")

        assert template_id1 is not None
        assert template_id2 is not None
        assert template_id1 != template_id2


class TestUpdateTemplate:
    """Тесты обновления шаблонов."""

    def test_update_template_name(self, temp_db):
        """Успешное обновление названия шаблона."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Старое название", "Описание")

        result = update_template(temp_db, template_id, chat_id, name="Новое название")
        assert result is True

        # Проверяем обновление
        cursor = temp_db.execute(
            "SELECT name FROM survey_templates WHERE id = ?",
            (template_id,)
        )
        assert cursor.fetchone()[0] == "Новое название"

    def test_update_template_description(self, temp_db):
        """Успешное обновление описания шаблона."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Название", "Старое описание")

        result = update_template(temp_db, template_id, chat_id, description="Новое описание")
        assert result is True

        cursor = temp_db.execute(
            "SELECT description FROM survey_templates WHERE id = ?",
            (template_id,)
        )
        assert cursor.fetchone()[0] == "Новое описание"

    def test_update_template_is_active(self, temp_db):
        """Успешная активация шаблона."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Название", "Описание")

        result = update_template(temp_db, template_id, chat_id, is_active=True)
        assert result is True

        cursor = temp_db.execute(
            "SELECT is_active FROM survey_templates WHERE id = ?",
            (template_id,)
        )
        assert cursor.fetchone()[0] == 1

    def test_update_template_not_owner(self, temp_db):
        """Попытка обновить чужой шаблон."""
        owner_id = 111
        other_id = 222

        template_id = create_user_template(temp_db, owner_id, "Название", "Описание")

        # Пытаемся обновить как другой пользователь
        result = update_template(temp_db, template_id, other_id, name="Новое название")
        assert result is False

    def test_update_system_template(self, temp_db):
        """Попытка обновить системный шаблон."""
        # Создаем системный шаблон
        temp_db.execute("""
            INSERT INTO survey_templates
            (name, description, is_system, is_active, created_by, created_at)
            VALUES ('Системный', 'Описание', 1, 1, NULL, ?)
        """, (datetime.now().isoformat(),))
        temp_db.commit()
        template_id = temp_db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Пытаемся обновить
        result = update_template(temp_db, template_id, 12345, name="Новое название")
        assert result is False

    def test_update_template_duplicate_name(self, temp_db):
        """Попытка изменить название на уже существующее."""
        chat_id = 12345

        template_id1 = create_user_template(temp_db, chat_id, "Опрос 1", "Описание 1")
        template_id2 = create_user_template(temp_db, chat_id, "Опрос 2", "Описание 2")

        # Пытаемся переименовать template_id2 в "Опрос 1"
        result = update_template(temp_db, template_id2, chat_id, name="Опрос 1")
        assert result is False

    def test_update_template_nonexistent(self, temp_db):
        """Попытка обновить несуществующий шаблон."""
        result = update_template(temp_db, 99999, 12345, name="Название")
        assert result is False


class TestDeleteTemplate:
    """Тесты удаления шаблонов."""

    def test_delete_template_success(self, temp_db):
        """Успешное удаление шаблона."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Название", "Описание")

        result = delete_template(temp_db, template_id, chat_id)
        assert result is True

        # Проверяем что шаблон удален
        cursor = temp_db.execute(
            "SELECT * FROM survey_templates WHERE id = ?",
            (template_id,)
        )
        assert cursor.fetchone() is None

    def test_delete_template_not_owner(self, temp_db):
        """Попытка удалить чужой шаблон."""
        owner_id = 111
        other_id = 222

        template_id = create_user_template(temp_db, owner_id, "Название", "Описание")

        result = delete_template(temp_db, template_id, other_id)
        assert result is False

        # Шаблон должен остаться
        cursor = temp_db.execute(
            "SELECT * FROM survey_templates WHERE id = ?",
            (template_id,)
        )
        assert cursor.fetchone() is not None

    def test_delete_system_template(self, temp_db):
        """Попытка удалить системный шаблон."""
        # Создаем системный шаблон
        temp_db.execute("""
            INSERT INTO survey_templates
            (name, description, is_system, is_active, created_by, created_at)
            VALUES ('Системный', 'Описание', 1, 1, NULL, ?)
        """, (datetime.now().isoformat(),))
        temp_db.commit()
        template_id = temp_db.execute("SELECT last_insert_rowid()").fetchone()[0]

        result = delete_template(temp_db, template_id, 12345)
        assert result is False

        # Шаблон должен остаться
        cursor = temp_db.execute(
            "SELECT * FROM survey_templates WHERE id = ?",
            (template_id,)
        )
        assert cursor.fetchone() is not None

    def test_delete_template_nonexistent(self, temp_db):
        """Попытка удалить несуществующий шаблон."""
        result = delete_template(temp_db, 99999, 12345)
        assert result is False

    def test_delete_template_cascades_questions(self, temp_db):
        """Проверка CASCADE удаления вопросов."""
        chat_id = 12345
        template_id = create_user_template(temp_db, chat_id, "Название", "Описание")

        # Добавляем вопросы
        temp_db.execute("""
            INSERT INTO survey_questions
            (template_id, question_text, question_type, order_index)
            VALUES (?, 'Вопрос 1', 'text', 1)
        """, (template_id,))
        temp_db.execute("""
            INSERT INTO survey_questions
            (template_id, question_text, question_type, order_index)
            VALUES (?, 'Вопрос 2', 'text', 2)
        """, (template_id,))
        temp_db.commit()

        # Удаляем шаблон
        result = delete_template(temp_db, template_id, chat_id)
        assert result is True

        # Проверяем что вопросы тоже удалены
        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM survey_questions WHERE template_id = ?",
            (template_id,)
        )
        assert cursor.fetchone()[0] == 0


class TestGetUserTemplates:
    """Тесты получения шаблонов пользователя."""

    def test_get_user_templates_empty(self, temp_db):
        """Получение шаблонов когда их нет."""
        templates = get_user_templates(temp_db, 12345)
        assert templates == []

    def test_get_user_templates_multiple(self, temp_db):
        """Получение нескольких шаблонов."""
        chat_id = 12345

        create_user_template(temp_db, chat_id, "Опрос 1", "Описание 1")
        create_user_template(temp_db, chat_id, "Опрос 2", "Описание 2")
        create_user_template(temp_db, chat_id, "Опрос 3", "Описание 3")

        templates = get_user_templates(temp_db, chat_id)
        assert len(templates) == 3

        # Проверяем что все шаблоны принадлежат пользователю
        for template in templates:
            assert template['created_by'] == chat_id
            assert template['is_system'] is False

    def test_get_user_templates_only_active(self, temp_db):
        """Получение только активных шаблонов."""
        chat_id = 12345

        template_id1 = create_user_template(temp_db, chat_id, "Активный", "Описание")
        template_id2 = create_user_template(temp_db, chat_id, "Неактивный", "Описание")

        # Активируем первый
        update_template(temp_db, template_id1, chat_id, is_active=True)

        templates = get_user_templates(temp_db, chat_id, only_active=True)
        assert len(templates) == 1
        assert templates[0]['name'] == "Активный"
        assert templates[0]['is_active'] is True

    def test_get_user_templates_isolation(self, temp_db):
        """Проверка изоляции шаблонов разных пользователей."""
        create_user_template(temp_db, 111, "Опрос пользователя 1", "Описание")
        create_user_template(temp_db, 222, "Опрос пользователя 2", "Описание")
        create_user_template(temp_db, 111, "Еще опрос пользователя 1", "Описание")

        templates_user1 = get_user_templates(temp_db, 111)
        templates_user2 = get_user_templates(temp_db, 222)

        assert len(templates_user1) == 2
        assert len(templates_user2) == 1


class TestCountUserTemplates:
    """Тесты подсчета количества шаблонов."""

    def test_count_user_templates_zero(self, temp_db):
        """Подсчет когда шаблонов нет."""
        count = count_user_templates(temp_db, 12345)
        assert count == 0

    def test_count_user_templates_multiple(self, temp_db):
        """Подсчет нескольких шаблонов."""
        chat_id = 12345

        create_user_template(temp_db, chat_id, "Опрос 1", "Описание")
        create_user_template(temp_db, chat_id, "Опрос 2", "Описание")
        create_user_template(temp_db, chat_id, "Опрос 3", "Описание")

        count = count_user_templates(temp_db, chat_id)
        assert count == 3

    def test_count_user_templates_excludes_system(self, temp_db):
        """Подсчет не включает системные шаблоны."""
        chat_id = 12345

        # Создаем пользовательский шаблон
        create_user_template(temp_db, chat_id, "Пользовательский", "Описание")

        # Создаем системный шаблон (с тем же created_by для проверки фильтра)
        temp_db.execute("""
            INSERT INTO survey_templates
            (name, description, is_system, is_active, created_by, created_at)
            VALUES ('Системный', 'Описание', 1, 1, ?, ?)
        """, (chat_id, datetime.now().isoformat()))
        temp_db.commit()

        count = count_user_templates(temp_db, chat_id)
        assert count == 1  # Только пользовательский

    def test_count_respects_user_isolation(self, temp_db):
        """Подсчет учитывает только шаблоны конкретного пользователя."""
        create_user_template(temp_db, 111, "Опрос 1", "Описание")
        create_user_template(temp_db, 111, "Опрос 2", "Описание")
        create_user_template(temp_db, 222, "Опрос 3", "Описание")

        assert count_user_templates(temp_db, 111) == 2
        assert count_user_templates(temp_db, 222) == 1
        assert count_user_templates(temp_db, 333) == 0
