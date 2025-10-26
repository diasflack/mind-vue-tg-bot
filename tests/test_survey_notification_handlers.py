"""
Тесты для handlers управления напоминаниями по опросам (Phase 5.2).
"""

import pytest
import sqlite3
from unittest.mock import MagicMock, AsyncMock, patch

from src.handlers.survey_notification_handlers import (
    survey_reminders_handler,
    set_reminder_handler,
    remove_reminder_handler
)


@pytest.fixture
def temp_db(mock_config):
    """Создает временную БД с таблицами для опросов."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            timezone_offset INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE survey_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_system BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE user_survey_preferences (
            chat_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            is_favorite BOOLEAN DEFAULT 0,
            notification_enabled BOOLEAN DEFAULT 0,
            notification_time TEXT,
            PRIMARY KEY (chat_id, template_id)
        )
    ''')

    # Добавляем тестовые данные
    cursor.execute('INSERT INTO users (chat_id, username, timezone_offset) VALUES (?, ?, ?)',
                   (12345, 'testuser', 3))

    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, is_system, is_active)
        VALUES (1, 'Настроение', 'Ежедневная оценка', 0, 1)
    ''')

    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, is_system, is_active)
        VALUES (2, 'Тревога', 'Оценка тревоги', 0, 1)
    ''')

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_update():
    """Mock объект Update."""
    update = MagicMock()
    update.effective_chat.id = 12345
    update.message = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Mock объект Context."""
    context = MagicMock()
    context.args = []
    return context


class TestSurveyRemindersHandler:
    """Тесты команды /survey_reminders."""

    @pytest.mark.asyncio
    async def test_show_reminders_with_data(self, mock_update, mock_context, temp_db):
        """Отображение существующих напоминаний."""
        # Добавляем напоминания
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, 1, '09:00'))
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 2, 0, '20:00'))
        temp_db.commit()

        with patch('src.handlers.survey_notification_handlers._get_db_connection', return_value=temp_db):
            await survey_reminders_handler(mock_update, mock_context)

            # Проверяем что отправлено сообщение
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]

            # Проверяем содержимое
            assert "Настроение" in call_args
            assert "09:00" in call_args or "12:00" in call_args  # Может быть конвертировано в локальное время
            assert "✅" in call_args or "включено" in call_args.lower()

    @pytest.mark.asyncio
    async def test_show_reminders_empty(self, mock_update, mock_context, temp_db):
        """Отображение когда нет напоминаний."""
        with patch('src.handlers.survey_notification_handlers._get_db_connection', return_value=temp_db):
            await survey_reminders_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "нет" in call_args.lower() or "не настроены" in call_args.lower()


class TestSetReminderHandler:
    """Тесты команды /set_survey_reminder."""

    @pytest.mark.asyncio
    async def test_set_reminder_success(self, mock_update, mock_context, temp_db):
        """Успешная установка напоминания."""
        mock_context.args = ['Настроение', '09:00']

        with patch('src.handlers.survey_notification_handlers._get_db_connection', return_value=temp_db):
            await set_reminder_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "✅" in call_args
            assert "Настроение" in call_args
            assert "09:00" in call_args

    @pytest.mark.asyncio
    async def test_set_reminder_missing_args(self, mock_update, mock_context):
        """Недостаточно аргументов."""
        mock_context.args = ['Настроение']  # Нет времени

        await set_reminder_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "использование" in call_args.lower()

    @pytest.mark.asyncio
    async def test_set_reminder_invalid_time(self, mock_update, mock_context, temp_db):
        """Невалидный формат времени."""
        mock_context.args = ['Настроение', 'invalid']

        with patch('src.handlers.survey_notification_handlers._get_db_connection', return_value=temp_db):
            await set_reminder_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args
            assert "формат" in call_args.lower() or "время" in call_args.lower()

    @pytest.mark.asyncio
    async def test_set_reminder_nonexistent_survey(self, mock_update, mock_context, temp_db):
        """Попытка установить напоминание для несуществующего опроса."""
        mock_context.args = ['НесуществующийОпрос', '09:00']

        with patch('src.handlers.survey_notification_handlers._get_db_connection', return_value=temp_db):
            await set_reminder_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args
            assert "не найден" in call_args.lower()


class TestRemoveReminderHandler:
    """Тесты команды /remove_survey_reminder."""

    @pytest.mark.asyncio
    async def test_remove_reminder_success(self, mock_update, mock_context, temp_db):
        """Успешное удаление напоминания."""
        # Создаем напоминание
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, 1, '09:00'))
        temp_db.commit()

        mock_context.args = ['Настроение']

        with patch('src.handlers.survey_notification_handlers._get_db_connection', return_value=temp_db):
            await remove_reminder_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "✅" in call_args
            assert "отключено" in call_args.lower() or "удалено" in call_args.lower()

    @pytest.mark.asyncio
    async def test_remove_reminder_missing_arg(self, mock_update, mock_context):
        """Недостаточно аргументов."""
        mock_context.args = []

        await remove_reminder_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "использование" in call_args.lower()

    @pytest.mark.asyncio
    async def test_remove_reminder_nonexistent(self, mock_update, mock_context, temp_db):
        """Попытка удалить несуществующее напоминание."""
        mock_context.args = ['Настроение']

        with patch('src.handlers.survey_notification_handlers._get_db_connection', return_value=temp_db):
            await remove_reminder_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args or "ℹ️" in call_args
            assert "не найдено" in call_args.lower() or "не настроено" in call_args.lower() or "не было настроено" in call_args.lower()

    @pytest.mark.asyncio
    async def test_remove_reminder_nonexistent_survey(self, mock_update, mock_context, temp_db):
        """Попытка удалить напоминание для несуществующего опроса."""
        mock_context.args = ['НесуществующийОпрос']

        with patch('src.handlers.survey_notification_handlers._get_db_connection', return_value=temp_db):
            await remove_reminder_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args
            assert "не найден" in call_args.lower()
