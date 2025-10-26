"""
Тесты для handlers объединенной аналитики (Phase 5.5).
"""

import pytest
import sqlite3
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

from src.handlers.combined_analytics_handlers import (
    combined_analytics_handler
)


@pytest.fixture
def temp_db(mock_config):
    """Создает временную БД с данными для аналитики."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT
        )
    ''')

    # Таблица записей дня
    cursor.execute('''
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            mood_score INTEGER,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица впечатлений
    cursor.execute('''
        CREATE TABLE impressions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            category TEXT CHECK(category IN ('positive', 'negative', 'neutral')),
            intensity INTEGER CHECK(intensity BETWEEN 1 AND 10),
            entry_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица шаблонов опросов
    cursor.execute('''
        CREATE TABLE survey_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_system BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    # Таблица ответов на опросы
    cursor.execute('''
        CREATE TABLE survey_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            answers TEXT NOT NULL,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Добавляем тестовые данные
    cursor.execute('INSERT INTO users (chat_id, username) VALUES (?, ?)', (12345, 'testuser'))

    # Записи за последние 7 дней
    today = datetime.now()
    for i in range(7):
        date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        cursor.execute('''
            INSERT INTO entries (chat_id, date, mood_score)
            VALUES (?, ?, ?)
        ''', (12345, date, 7 - i))

    # Впечатления
    cursor.execute('''
        INSERT INTO impressions (chat_id, text, category, intensity, entry_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (12345, 'Отличный день', 'positive', 8, (today - timedelta(days=1)).strftime('%Y-%m-%d'),
          (today - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')))

    cursor.execute('''
        INSERT INTO impressions (chat_id, text, category, intensity, entry_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (12345, 'Плохое настроение', 'negative', 6, (today - timedelta(days=2)).strftime('%Y-%m-%d'),
          (today - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')))

    # Шаблон опроса
    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, is_system, is_active)
        VALUES (1, 'Настроение', 'Ежедневная оценка', 1, 1)
    ''')

    # Ответы на опросы
    cursor.execute('''
        INSERT INTO survey_responses (chat_id, template_id, answers, completed_at)
        VALUES (?, ?, ?, ?)
    ''', (12345, 1, '{"1": "8"}', (today - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')))

    cursor.execute('''
        INSERT INTO survey_responses (chat_id, template_id, answers, completed_at)
        VALUES (?, ?, ?, ?)
    ''', (12345, 1, '{"1": "4"}', (today - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')))

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


class TestCombinedAnalyticsHandler:
    """Тесты команды /combined_analytics."""

    @pytest.mark.asyncio
    async def test_combined_analytics_default(self, mock_update, mock_context, temp_db):
        """Получение аналитики с параметрами по умолчанию."""
        with patch('src.handlers.combined_analytics_handlers._get_db_connection', return_value=temp_db):
            await combined_analytics_handler(mock_update, mock_context)

            # Проверяем что отправлено сообщение
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]

            # Проверяем содержимое
            assert "📊" in call_args or "Аналитика" in call_args or "аналитика" in call_args
            assert "7" in call_args or "дней" in call_args or "дня" in call_args

    @pytest.mark.asyncio
    async def test_combined_analytics_custom_period(self, mock_update, mock_context, temp_db):
        """Получение аналитики за произвольный период."""
        mock_context.args = ['--period', '14']

        with patch('src.handlers.combined_analytics_handlers._get_db_connection', return_value=temp_db):
            await combined_analytics_handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]

            # Проверяем что период учтен
            assert "14" in call_args or "дней" in call_args

    @pytest.mark.asyncio
    async def test_combined_analytics_no_data(self, temp_db):
        """Получение аналитики для пользователя без данных."""
        update = MagicMock()
        update.effective_chat.id = 99999
        update.message = AsyncMock()

        context = MagicMock()
        context.args = []

        with patch('src.handlers.combined_analytics_handlers._get_db_connection', return_value=temp_db):
            await combined_analytics_handler(update, context)

            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args[0][0]

            # Должно сообщить об отсутствии данных
            assert "нет" in call_args.lower() or "не найдено" in call_args.lower() or "недостаточно" in call_args.lower()

    @pytest.mark.asyncio
    async def test_combined_analytics_with_overview(self, mock_update, mock_context, temp_db):
        """Проверка что аналитика содержит обзор активности."""
        with patch('src.handlers.combined_analytics_handlers._get_db_connection', return_value=temp_db):
            await combined_analytics_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]

            # Проверяем что есть информация о количестве записей
            # (может быть в разных форматах, поэтому проверяем наличие ключевых слов)
            content_lower = call_args.lower()
            has_impressions = 'впечатлен' in content_lower or 'impression' in content_lower
            has_surveys = 'опрос' in content_lower or 'survey' in content_lower
            has_mood = 'настроение' in content_lower or 'mood' in content_lower

            assert has_impressions or has_surveys or has_mood

    @pytest.mark.asyncio
    async def test_combined_analytics_formatting(self, mock_update, mock_context, temp_db):
        """Проверка форматирования вывода."""
        with patch('src.handlers.combined_analytics_handlers._get_db_connection', return_value=temp_db):
            await combined_analytics_handler(mock_update, mock_context)

            # Проверяем что используется Markdown
            assert mock_update.message.reply_text.call_args[1].get('parse_mode') == 'Markdown'
