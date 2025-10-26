"""
Тесты для handlers управления избранными опросами (Phase 5.3).
"""

import pytest
import sqlite3
from unittest.mock import MagicMock, AsyncMock, patch

from src.handlers.favorite_surveys_handlers import (
    favorite_surveys_handler,
    add_favorite_handler,
    remove_favorite_handler
)


@pytest.fixture
def temp_db(mock_config):
    """Создает временную БД с таблицами для опросов."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT
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
    cursor.execute('INSERT INTO users (chat_id, username) VALUES (?, ?)', (12345, 'testuser'))

    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, is_system, is_active)
        VALUES (1, 'Настроение', 'Ежедневная оценка', 0, 1)
    ''')

    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, is_system, is_active)
        VALUES (2, 'Тревога', 'Оценка тревоги', 0, 1)
    ''')

    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, is_system, is_active)
        VALUES (3, 'Сон', 'Дневник сна', 1, 1)
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


class TestFavoriteSurveysHandler:
    """Тесты команды /favorite_surveys."""

    @pytest.mark.asyncio
    async def test_show_favorites_with_data(self, mock_update, mock_context, temp_db):
        """Отображение существующих избранных опросов."""
        # Добавляем избранные
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 1, 1))
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 2, 1))
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 3, 0))  # Не избранное
        temp_db.commit()

        with patch('src.handlers.favorite_surveys_handlers._get_db_connection', return_value=temp_db):
            await favorite_surveys_handler(mock_update, mock_context)

            # Проверяем что отправлено сообщение
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]

            # Проверяем содержимое
            assert "Настроение" in call_args
            assert "Тревога" in call_args
            assert "Сон" not in call_args  # Не в избранном

    @pytest.mark.asyncio
    async def test_show_favorites_empty(self, mock_update, mock_context, temp_db):
        """Отображение когда нет избранных опросов."""
        with patch('src.handlers.favorite_surveys_handlers._get_db_connection', return_value=temp_db):
            await favorite_surveys_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "нет" in call_args.lower() or "пусто" in call_args.lower()


class TestAddFavoriteHandler:
    """Тесты команды /add_favorite."""

    @pytest.mark.asyncio
    async def test_add_favorite_success(self, mock_update, mock_context, temp_db):
        """Успешное добавление в избранное."""
        mock_context.args = ['Настроение']

        with patch('src.handlers.favorite_surveys_handlers._get_db_connection', return_value=temp_db):
            await add_favorite_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "✅" in call_args
            assert "Настроение" in call_args
            assert "избранное" in call_args.lower()

    @pytest.mark.asyncio
    async def test_add_favorite_missing_arg(self, mock_update, mock_context):
        """Недостаточно аргументов."""
        mock_context.args = []

        await add_favorite_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "использование" in call_args.lower()

    @pytest.mark.asyncio
    async def test_add_favorite_nonexistent_survey(self, mock_update, mock_context, temp_db):
        """Попытка добавить несуществующий опрос."""
        mock_context.args = ['НесуществующийОпрос']

        with patch('src.handlers.favorite_surveys_handlers._get_db_connection', return_value=temp_db):
            await add_favorite_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args
            assert "не найден" in call_args.lower()

    @pytest.mark.asyncio
    async def test_add_favorite_already_favorite(self, mock_update, mock_context, temp_db):
        """Добавление опроса который уже в избранном."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 1, 1))
        temp_db.commit()

        mock_context.args = ['Настроение']

        with patch('src.handlers.favorite_surveys_handlers._get_db_connection', return_value=temp_db):
            await add_favorite_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            # Должно сообщить что уже в избранном
            assert "ℹ️" in call_args or "✅" in call_args
            assert "уже в избранном" in call_args.lower()


class TestRemoveFavoriteHandler:
    """Тесты команды /remove_favorite."""

    @pytest.mark.asyncio
    async def test_remove_favorite_success(self, mock_update, mock_context, temp_db):
        """Успешное удаление из избранного."""
        # Создаем избранный опрос
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 1, 1))
        temp_db.commit()

        mock_context.args = ['Настроение']

        with patch('src.handlers.favorite_surveys_handlers._get_db_connection', return_value=temp_db):
            await remove_favorite_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "✅" in call_args
            assert "удалено" in call_args.lower() or "удален" in call_args.lower()

    @pytest.mark.asyncio
    async def test_remove_favorite_missing_arg(self, mock_update, mock_context):
        """Недостаточно аргументов."""
        mock_context.args = []

        await remove_favorite_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "использование" in call_args.lower()

    @pytest.mark.asyncio
    async def test_remove_favorite_nonexistent(self, mock_update, mock_context, temp_db):
        """Попытка удалить несуществующую запись."""
        mock_context.args = ['Настроение']

        with patch('src.handlers.favorite_surveys_handlers._get_db_connection', return_value=temp_db):
            await remove_favorite_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args or "ℹ️" in call_args
            assert "не найдено" in call_args.lower() or "не в избранном" in call_args.lower() or "не был в избранном" in call_args.lower()

    @pytest.mark.asyncio
    async def test_remove_favorite_nonexistent_survey(self, mock_update, mock_context, temp_db):
        """Попытка удалить несуществующий опрос."""
        mock_context.args = ['НесуществующийОпрос']

        with patch('src.handlers.favorite_surveys_handlers._get_db_connection', return_value=temp_db):
            await remove_favorite_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args
            assert "не найден" in call_args.lower()
