"""
Тесты для handlers экспорта данных (Phase 5.4).
"""

import pytest
import sqlite3
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from io import BytesIO

from src.handlers.export_handlers import (
    export_impressions_handler,
    export_surveys_handler,
    export_all_handler
)


@pytest.fixture
def temp_db(mock_config):
    """Создает временную БД с данными для экспорта."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Создаем таблицы
    cursor.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT
        )
    ''')

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE survey_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE survey_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL,
            question_config TEXT,
            order_num INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE survey_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            response_date TEXT NOT NULL,
            response_time TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE survey_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            response_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer_text TEXT,
            answer_numeric REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE entries (
            chat_id INTEGER,
            date TEXT,
            mood INTEGER,
            sleep_hours REAL,
            comment TEXT,
            balance INTEGER,
            mania INTEGER,
            depression INTEGER,
            anxiety INTEGER,
            irritability INTEGER,
            productivity INTEGER,
            sociability INTEGER,
            PRIMARY KEY (chat_id, date)
        )
    ''')

    # Добавляем тестовые данные
    cursor.execute('INSERT INTO users (chat_id, username) VALUES (?, ?)', (12345, 'testuser'))

    cursor.execute('''
        INSERT INTO impressions (chat_id, impression_text, impression_date, impression_time, category, intensity)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (12345, 'Тестовое впечатление', '2025-10-25', '10:00:00', 'positive', 8))

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


class TestExportImpressionsHandler:
    """Тесты команды /export_impressions."""

    @pytest.mark.asyncio
    async def test_export_impressions_default_format(self, mock_update, mock_context, temp_db):
        """Экспорт впечатлений в формате по умолчанию (CSV)."""
        with patch('src.handlers.export_handlers._get_db_connection', return_value=temp_db):
            await export_impressions_handler(mock_update, mock_context)

            # Проверяем что был вызван reply_document
            mock_update.message.reply_document.assert_called_once()

            # Проверяем что отправлен файл
            call_args = mock_update.message.reply_document.call_args
            assert call_args is not None
            assert 'document' in call_args[1] or len(call_args[0]) > 0

    @pytest.mark.asyncio
    async def test_export_impressions_json_format(self, mock_update, mock_context, temp_db):
        """Экспорт впечатлений в JSON формате."""
        mock_context.args = ['--format', 'json']

        with patch('src.handlers.export_handlers._get_db_connection', return_value=temp_db):
            await export_impressions_handler(mock_update, mock_context)

            # Проверяем что был вызван reply_document
            mock_update.message.reply_document.assert_called_once()

            # Проверяем что filename содержит .json
            call_args = mock_update.message.reply_document.call_args
            filename = call_args[1].get('filename', '')
            assert '.json' in filename

    @pytest.mark.asyncio
    async def test_export_impressions_with_date_filters(self, mock_update, mock_context, temp_db):
        """Экспорт впечатлений с фильтрами по дате."""
        mock_context.args = ['--from', '2025-10-01', '--to', '2025-10-31']

        with patch('src.handlers.export_handlers._get_db_connection', return_value=temp_db):
            await export_impressions_handler(mock_update, mock_context)

            # Проверяем что экспорт выполнился
            mock_update.message.reply_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_impressions_invalid_format(self, mock_update, mock_context, temp_db):
        """Попытка экспорта с невалидным форматом."""
        mock_context.args = ['--format', 'xml']

        with patch('src.handlers.export_handlers._get_db_connection', return_value=temp_db):
            await export_impressions_handler(mock_update, mock_context)

            # Проверяем что отправлено сообщение об ошибке
            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args or "неверный" in call_args.lower()

    @pytest.mark.asyncio
    async def test_export_impressions_no_data(self, mock_update, mock_context, temp_db):
        """Экспорт когда нет впечатлений."""
        # Очищаем впечатления
        cursor = temp_db.cursor()
        cursor.execute('DELETE FROM impressions')
        temp_db.commit()

        with patch('src.handlers.export_handlers._get_db_connection', return_value=temp_db):
            await export_impressions_handler(mock_update, mock_context)

            # Проверяем что отправлено сообщение о том, что нет данных
            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "нет" in call_args.lower() or "отсутствуют" in call_args.lower()


class TestExportSurveysHandler:
    """Тесты команды /export_surveys."""

    @pytest.mark.asyncio
    async def test_export_surveys_missing_name(self, mock_update, mock_context):
        """Попытка экспорта без указания названия опроса."""
        mock_context.args = []

        await export_surveys_handler(mock_update, mock_context)

        # Проверяем что отправлено сообщение об ошибке
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args or "использование" in call_args.lower()

    @pytest.mark.asyncio
    async def test_export_surveys_csv_format(self, mock_update, mock_context, temp_db):
        """Экспорт опроса в CSV формате."""
        # Добавляем опрос
        cursor = temp_db.cursor()
        cursor.execute('INSERT INTO survey_templates (id, name) VALUES (?, ?)', (1, 'Настроение'))
        cursor.execute('''
            INSERT INTO survey_questions (template_id, question_text, question_type, order_num)
            VALUES (?, ?, ?, ?)
        ''', (1, 'Как настроение?', 'numeric', 1))
        cursor.execute('''
            INSERT INTO survey_responses (chat_id, template_id, response_date, response_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, '2025-10-25', '10:00:00'))
        temp_db.commit()

        mock_context.args = ['Настроение']

        with patch('src.handlers.export_handlers._get_db_connection', return_value=temp_db):
            await export_surveys_handler(mock_update, mock_context)

            # Проверяем что файл отправлен
            mock_update.message.reply_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_surveys_json_format(self, mock_update, mock_context, temp_db):
        """Экспорт опроса в JSON формате."""
        # Добавляем опрос
        cursor = temp_db.cursor()
        cursor.execute('INSERT INTO survey_templates (id, name) VALUES (?, ?)', (1, 'Настроение'))
        temp_db.commit()

        mock_context.args = ['Настроение', '--format', 'json']

        with patch('src.handlers.export_handlers._get_db_connection', return_value=temp_db):
            await export_surveys_handler(mock_update, mock_context)

            # Проверяем что файл отправлен с .json расширением
            call_args = mock_update.message.reply_document.call_args
            filename = call_args[1].get('filename', '')
            assert '.json' in filename

    @pytest.mark.asyncio
    async def test_export_surveys_nonexistent(self, mock_update, mock_context, temp_db):
        """Попытка экспорта несуществующего опроса."""
        mock_context.args = ['НесуществующийОпрос']

        with patch('src.handlers.export_handlers._get_db_connection', return_value=temp_db):
            await export_surveys_handler(mock_update, mock_context)

            # Проверяем что отправлено сообщение об ошибке
            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args or "не найден" in call_args.lower()


class TestExportAllHandler:
    """Тесты команды /export_all."""

    @pytest.mark.asyncio
    async def test_export_all_data(self, mock_update, mock_context, temp_db):
        """Экспорт всех данных пользователя."""
        with patch('src.handlers.export_handlers._get_db_connection', return_value=temp_db):
            await export_all_handler(mock_update, mock_context)

            # Проверяем что файл отправлен
            mock_update.message.reply_document.assert_called_once()

            # Проверяем что это JSON файл
            call_args = mock_update.message.reply_document.call_args
            filename = call_args[1].get('filename', '')
            assert '.json' in filename

    @pytest.mark.asyncio
    async def test_export_all_no_data(self, mock_update, mock_context, temp_db):
        """Экспорт всех данных когда их нет."""
        # Очищаем все данные
        cursor = temp_db.cursor()
        cursor.execute('DELETE FROM impressions')
        temp_db.commit()

        with patch('src.handlers.export_handlers._get_db_connection', return_value=temp_db):
            await export_all_handler(mock_update, mock_context)

            # Все равно должен отправить файл, но с пустыми массивами
            mock_update.message.reply_document.assert_called_once()
