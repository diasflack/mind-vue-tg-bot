"""
Тесты для handlers привязки впечатлений к записям дня (Phase 5.1).
"""

import pytest
import sqlite3
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, date

from src.handlers.impression_link import link_impression_handler, unlink_impression_handler


@pytest.fixture
def temp_db(mock_config):
    """Создает временную БД для тестирования."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Создаем таблицу users
    cursor.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            notification_time TEXT
        )
    ''')

    # Создаем таблицу entries
    cursor.execute('''
        CREATE TABLE entries (
            chat_id INTEGER,
            date TEXT,
            mood INTEGER,
            sleep_hours REAL,
            comment TEXT,
            PRIMARY KEY (chat_id, date),
            FOREIGN KEY (chat_id) REFERENCES users(chat_id)
        )
    ''')

    # Создаем таблицу impressions
    cursor.execute('''
        CREATE TABLE impressions (
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

    # Добавляем тестового пользователя
    cursor.execute('INSERT INTO users (chat_id, username) VALUES (?, ?)', (12345, 'testuser'))

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


class TestLinkImpressionHandler:
    """Тесты команды /link_impression."""

    @pytest.mark.asyncio
    async def test_link_impression_success(self, mock_update, mock_context, temp_db):
        """Успешная привязка впечатления к записи."""
        mock_context.args = ['1', '2025-10-25']

        with patch('src.handlers.impression_link._get_db_connection', return_value=temp_db):
            # Создаем впечатление
            from src.data.impressions_storage import save_impression
            impression_data = {
                'chat_id': 12345,
                'text': 'Тестовое впечатление',
                'date': '2025-10-25',
                'time': '10:00:00',
                'category': 'positive',
                'intensity': 8
            }
            impression_id = save_impression(temp_db, impression_data)

            # Создаем запись дня
            cursor = temp_db.cursor()
            cursor.execute('''
                INSERT INTO entries (chat_id, date, mood)
                VALUES (?, ?, ?)
            ''', (12345, '2025-10-25', 7))
            temp_db.commit()

            # Обновляем args с реальным ID
            mock_context.args = [str(impression_id), '2025-10-25']

            await link_impression_handler(mock_update, mock_context)

            # Проверяем ответ
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "✅" in call_args
            assert "привязано" in call_args.lower()

    @pytest.mark.asyncio
    async def test_link_impression_missing_args(self, mock_update, mock_context):
        """Недостаточно аргументов."""
        mock_context.args = ['1']  # Нет даты

        await link_impression_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "использование" in call_args.lower()

    @pytest.mark.asyncio
    async def test_link_impression_invalid_id(self, mock_update, mock_context):
        """Невалидный ID впечатления."""
        mock_context.args = ['abc', '2025-10-25']

        await link_impression_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "id" in call_args.lower()

    @pytest.mark.asyncio
    async def test_link_impression_invalid_date(self, mock_update, mock_context):
        """Невалидная дата."""
        mock_context.args = ['1', 'invalid-date']

        await link_impression_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "дата" in call_args.lower()

    @pytest.mark.asyncio
    async def test_link_impression_nonexistent(self, mock_update, mock_context, temp_db):
        """Попытка привязать несуществующее впечатление."""
        mock_context.args = ['9999', '2025-10-25']

        with patch('src.handlers.impression_link._get_db_connection', return_value=temp_db):
            # Создаем запись дня
            cursor = temp_db.cursor()
            cursor.execute('''
                INSERT INTO entries (chat_id, date, mood)
                VALUES (?, ?, ?)
            ''', (12345, '2025-10-25', 7))
            temp_db.commit()

            await link_impression_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args
            assert "не найдено" in call_args.lower() or "не удалось" in call_args.lower()

    @pytest.mark.asyncio
    async def test_link_impression_nonexistent_entry(self, mock_update, mock_context, temp_db):
        """Попытка привязать к несуществующей записи."""
        with patch('src.handlers.impression_link._get_db_connection', return_value=temp_db):
            # Создаем впечатление
            from src.data.impressions_storage import save_impression
            impression_data = {
                'chat_id': 12345,
                'text': 'Тестовое впечатление',
                'date': '2025-10-25',
                'time': '10:00:00',
                'category': 'positive',
                'intensity': 8
            }
            impression_id = save_impression(temp_db, impression_data)

            mock_context.args = [str(impression_id), '2025-12-31']

            await link_impression_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args
            assert "запись" in call_args.lower() or "не найдено" in call_args.lower()


class TestUnlinkImpressionHandler:
    """Тесты команды /unlink_impression."""

    @pytest.mark.asyncio
    async def test_unlink_impression_success(self, mock_update, mock_context, temp_db):
        """Успешная отвязка впечатления."""
        with patch('src.handlers.impression_link._get_db_connection', return_value=temp_db):
            # Создаем запись дня
            cursor = temp_db.cursor()
            cursor.execute('''
                INSERT INTO entries (chat_id, date, mood)
                VALUES (?, ?, ?)
            ''', (12345, '2025-10-25', 7))
            temp_db.commit()

            # Создаем привязанное впечатление
            from src.data.impressions_storage import save_impression
            impression_data = {
                'chat_id': 12345,
                'text': 'Привязанное впечатление',
                'date': '2025-10-25',
                'time': '10:00:00',
                'category': 'positive',
                'intensity': 8,
                'entry_date': '2025-10-25'
            }
            impression_id = save_impression(temp_db, impression_data)

            mock_context.args = [str(impression_id)]

            await unlink_impression_handler(mock_update, mock_context)

            # Проверяем ответ
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "✅" in call_args
            assert "отвязано" in call_args.lower()

    @pytest.mark.asyncio
    async def test_unlink_impression_missing_args(self, mock_update, mock_context):
        """Недостаточно аргументов."""
        mock_context.args = []

        await unlink_impression_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "использование" in call_args.lower()

    @pytest.mark.asyncio
    async def test_unlink_impression_invalid_id(self, mock_update, mock_context):
        """Невалидный ID впечатления."""
        mock_context.args = ['abc']

        await unlink_impression_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "id" in call_args.lower()

    @pytest.mark.asyncio
    async def test_unlink_impression_nonexistent(self, mock_update, mock_context, temp_db):
        """Попытка отвязать несуществующее впечатление."""
        mock_context.args = ['9999']

        with patch('src.handlers.impression_link._get_db_connection', return_value=temp_db):
            await unlink_impression_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args
            assert "не найдено" in call_args.lower() or "не удалось" in call_args.lower()

    @pytest.mark.asyncio
    async def test_unlink_already_unlinked(self, mock_update, mock_context, temp_db):
        """Отвязка уже отвязанного впечатления."""
        with patch('src.handlers.impression_link._get_db_connection', return_value=temp_db):
            # Создаем не привязанное впечатление
            from src.data.impressions_storage import save_impression
            impression_data = {
                'chat_id': 12345,
                'text': 'Не привязанное',
                'date': '2025-10-25',
                'time': '10:00:00',
                'category': 'neutral',
                'intensity': 5
            }
            impression_id = save_impression(temp_db, impression_data)

            mock_context.args = [str(impression_id)]

            await unlink_impression_handler(mock_update, mock_context)

            # Должно пройти успешно (отвязка - идемпотентная операция)
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "✅" in call_args
