"""
Тесты для экспорта впечатлений (Phase 5.4).
"""

import pytest
import sqlite3
import json
import csv
from io import StringIO
from datetime import datetime

from src.data.export import export_impressions_csv, export_impressions_json


@pytest.fixture
def temp_db(mock_config):
    """Создает временную БД с впечатлениями."""
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
            FOREIGN KEY (chat_id) REFERENCES users(chat_id)
        )
    ''')

    # Добавляем тестового пользователя
    cursor.execute('INSERT INTO users (chat_id, username) VALUES (?, ?)', (12345, 'testuser'))

    # Добавляем тестовые впечатления
    test_impressions = [
        (12345, 'Отличное утро!', '2025-10-20', '08:00:00', 'positive', 9, None),
        (12345, 'Стресс на работе', '2025-10-21', '14:30:00', 'negative', 7, None),
        (12345, 'Обычный день', '2025-10-22', '12:00:00', 'neutral', 5, None),
        (12345, 'Хорошая пробежка', '2025-10-23', '07:00:00', 'positive', 8, '2025-10-23'),
        (12345, 'Усталость', '2025-10-24', '20:00:00', 'negative', 6, None),
    ]

    cursor.executemany('''
        INSERT INTO impressions
        (chat_id, impression_text, impression_date, impression_time, category, intensity, entry_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', test_impressions)

    conn.commit()
    yield conn
    conn.close()


class TestExportImpressionsCSV:
    """Тесты экспорта впечатлений в CSV."""

    def test_export_all_impressions_csv(self, temp_db):
        """Экспорт всех впечатлений в CSV."""
        csv_data = export_impressions_csv(temp_db, chat_id=12345)

        # Проверяем что получили строку
        assert isinstance(csv_data, str)
        assert len(csv_data) > 0

        # Парсим CSV
        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)

        # Проверяем количество записей
        assert len(rows) == 5

        # Проверяем наличие всех колонок
        assert 'id' in rows[0]
        assert 'text' in rows[0]
        assert 'date' in rows[0]
        assert 'time' in rows[0]
        assert 'category' in rows[0]
        assert 'intensity' in rows[0]
        assert 'entry_date' in rows[0]

        # Проверяем данные первой строки
        assert rows[0]['text'] == 'Отличное утро!'
        assert rows[0]['category'] == 'positive'
        assert rows[0]['intensity'] == '9'

    def test_export_impressions_csv_with_date_filter(self, temp_db):
        """Экспорт впечатлений с фильтром по дате."""
        csv_data = export_impressions_csv(
            temp_db,
            chat_id=12345,
            from_date='2025-10-22',
            to_date='2025-10-23'
        )

        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)

        # Должно быть только 2 записи (22 и 23 октября)
        assert len(rows) == 2
        assert rows[0]['text'] == 'Обычный день'
        assert rows[1]['text'] == 'Хорошая пробежка'

    def test_export_impressions_csv_from_date_only(self, temp_db):
        """Экспорт с фильтром только from_date."""
        csv_data = export_impressions_csv(
            temp_db,
            chat_id=12345,
            from_date='2025-10-23'
        )

        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)

        # Должно быть 2 записи (23 и 24 октября)
        assert len(rows) == 2

    def test_export_impressions_csv_to_date_only(self, temp_db):
        """Экспорт с фильтром только to_date."""
        csv_data = export_impressions_csv(
            temp_db,
            chat_id=12345,
            to_date='2025-10-21'
        )

        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)

        # Должно быть 2 записи (20 и 21 октября)
        assert len(rows) == 2

    def test_export_impressions_csv_empty_result(self, temp_db):
        """Экспорт когда нет подходящих записей."""
        csv_data = export_impressions_csv(
            temp_db,
            chat_id=12345,
            from_date='2025-12-01',
            to_date='2025-12-31'
        )

        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)

        # Должно быть 0 записей, но заголовки должны быть
        assert len(rows) == 0
        assert csv_data.startswith('id,')

    def test_export_impressions_csv_no_data_for_user(self, temp_db):
        """Экспорт для пользователя без впечатлений."""
        csv_data = export_impressions_csv(temp_db, chat_id=99999)

        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)

        assert len(rows) == 0


class TestExportImpressionsJSON:
    """Тесты экспорта впечатлений в JSON."""

    def test_export_all_impressions_json(self, temp_db):
        """Экспорт всех впечатлений в JSON."""
        json_data = export_impressions_json(temp_db, chat_id=12345)

        # Проверяем что получили строку
        assert isinstance(json_data, str)

        # Парсим JSON
        data = json.loads(json_data)

        # Проверяем структуру
        assert 'impressions' in data
        assert 'count' in data
        assert 'exported_at' in data

        # Проверяем количество
        assert data['count'] == 5
        assert len(data['impressions']) == 5

        # Проверяем первое впечатление
        first = data['impressions'][0]
        assert first['text'] == 'Отличное утро!'
        assert first['category'] == 'positive'
        assert first['intensity'] == 9
        assert first['date'] == '2025-10-20'

    def test_export_impressions_json_with_date_filter(self, temp_db):
        """Экспорт впечатлений в JSON с фильтром по дате."""
        json_data = export_impressions_json(
            temp_db,
            chat_id=12345,
            from_date='2025-10-22',
            to_date='2025-10-23'
        )

        data = json.loads(json_data)

        # Должно быть только 2 записи
        assert data['count'] == 2
        assert len(data['impressions']) == 2

    def test_export_impressions_json_empty_result(self, temp_db):
        """Экспорт в JSON когда нет подходящих записей."""
        json_data = export_impressions_json(
            temp_db,
            chat_id=12345,
            from_date='2025-12-01'
        )

        data = json.loads(json_data)

        assert data['count'] == 0
        assert data['impressions'] == []

    def test_export_impressions_json_includes_metadata(self, temp_db):
        """JSON экспорт содержит метаданные."""
        json_data = export_impressions_json(temp_db, chat_id=12345)
        data = json.loads(json_data)

        # Проверяем метаданные
        assert 'exported_at' in data
        assert 'filters' in data
        assert data['filters']['chat_id'] == 12345

    def test_export_impressions_json_with_linked_entries(self, temp_db):
        """JSON экспорт включает информацию о привязанных записях."""
        json_data = export_impressions_json(temp_db, chat_id=12345)
        data = json.loads(json_data)

        # Ищем впечатление с привязанной записью
        linked = [imp for imp in data['impressions'] if imp['entry_date'] is not None]
        assert len(linked) == 1
        assert linked[0]['text'] == 'Хорошая пробежка'
        assert linked[0]['entry_date'] == '2025-10-23'
