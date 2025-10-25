"""
Тесты для привязки впечатлений к записям дня (Phase 5.1).
"""

import pytest
import sqlite3
from datetime import datetime, date
from unittest.mock import MagicMock

from src.data.impressions_storage import (
    save_impression,
    link_impression_to_entry,
    unlink_impression,
    get_entry_impressions,
    get_impression_by_id
)


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

    # Добавляем тестовую запись
    cursor.execute('''
        INSERT INTO entries (chat_id, date, mood, sleep_hours, comment)
        VALUES (?, ?, ?, ?, ?)
    ''', (12345, '2025-10-25', 7, 8.0, 'Test entry'))

    conn.commit()
    yield conn
    conn.close()


class TestLinkImpressionToEntry:
    """Тесты привязки впечатления к записи."""

    def test_link_existing_impression_to_entry(self, temp_db):
        """Привязка существующего впечатления к записи."""
        # Создаем впечатление без привязки
        impression_data = {
            'chat_id': 12345,
            'text': 'Хорошее утро',
            'category': 'positive',
            'intensity': 8,
            'date': '2025-10-25',
            'time': '10:00:00'
        }

        impression_id = save_impression(temp_db, impression_data)
        assert impression_id is not None

        # Проверяем что entry_date пустой
        impression = get_impression_by_id(temp_db, impression_id, 12345)
        assert impression['entry_date'] is None

        # Привязываем к записи
        success = link_impression_to_entry(temp_db, impression_id, 12345, '2025-10-25')
        assert success is True

        # Проверяем что привязалось
        impression = get_impression_by_id(temp_db, impression_id, 12345)
        assert impression['entry_date'] == '2025-10-25'

    def test_link_to_nonexistent_entry(self, temp_db):
        """Попытка привязать к несуществующей записи."""
        impression_data = {
            'chat_id': 12345,
            'text': 'Тест',
            'category': 'neutral',
            'intensity': 5,
            'date': '2025-10-25',
            'time': '10:00:00'
        }

        impression_id = save_impression(temp_db, impression_data)

        # Пытаемся привязать к несуществующей дате
        success = link_impression_to_entry(temp_db, impression_id, 12345, '2025-12-31')
        assert success is False

    def test_link_wrong_user(self, temp_db):
        """Попытка привязать чужое впечатление."""
        impression_data = {
            'chat_id': 12345,
            'text': 'Тест',
            'category': 'neutral',
            'intensity': 5,
            'date': '2025-10-25',
            'time': '10:00:00'
        }

        impression_id = save_impression(temp_db, impression_data)

        # Пытаемся привязать от другого пользователя
        success = link_impression_to_entry(temp_db, impression_id, 99999, '2025-10-25')
        assert success is False

    def test_link_already_linked(self, temp_db):
        """Перепривязка впечатления к другой записи."""
        # Создаем еще одну запись
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO entries (chat_id, date, mood)
            VALUES (?, ?, ?)
        ''', (12345, '2025-10-26', 6))
        temp_db.commit()

        impression_data = {
            'chat_id': 12345,
            'text': 'Тест',
            'category': 'positive',
            'intensity': 7,
            'date': '2025-10-25',
            'time': '10:00:00',
            'entry_date': '2025-10-25'  # Уже привязано
        }

        impression_id = save_impression(temp_db, impression_data)

        # Проверяем начальную привязку
        impression = get_impression_by_id(temp_db, impression_id, 12345)
        assert impression['entry_date'] == '2025-10-25'

        # Перепривязываем к другой дате
        success = link_impression_to_entry(temp_db, impression_id, 12345, '2025-10-26')
        assert success is True

        # Проверяем новую привязку
        impression = get_impression_by_id(temp_db, impression_id, 12345)
        assert impression['entry_date'] == '2025-10-26'


class TestUnlinkImpression:
    """Тесты отвязки впечатления."""

    def test_unlink_linked_impression(self, temp_db):
        """Отвязка привязанного впечатления."""
        impression_data = {
            'chat_id': 12345,
            'text': 'Привязанное впечатление',
            'category': 'positive',
            'intensity': 7,
            'date': '2025-10-25',
            'time': '10:00:00',
            'entry_date': '2025-10-25'
        }

        impression_id = save_impression(temp_db, impression_data)

        # Проверяем что привязано
        impression = get_impression_by_id(temp_db, impression_id, 12345)
        assert impression['entry_date'] == '2025-10-25'

        # Отвязываем
        success = unlink_impression(temp_db, impression_id, 12345)
        assert success is True

        # Проверяем что отвязалось
        impression = get_impression_by_id(temp_db, impression_id, 12345)
        assert impression['entry_date'] is None

    def test_unlink_already_unlinked(self, temp_db):
        """Отвязка уже отвязанного впечатления."""
        impression_data = {
            'chat_id': 12345,
            'text': 'Не привязанное',
            'category': 'neutral',
            'intensity': 5,
            'date': '2025-10-25',
            'time': '10:00:00'
        }

        impression_id = save_impression(temp_db, impression_data)

        # Отвязываем (хотя уже не привязано)
        success = unlink_impression(temp_db, impression_id, 12345)
        assert success is True

    def test_unlink_wrong_user(self, temp_db):
        """Попытка отвязать чужое впечатление."""
        impression_data = {
            'chat_id': 12345,
            'text': 'Тест',
            'category': 'neutral',
            'intensity': 5,
            'date': '2025-10-25',
            'time': '10:00:00',
            'entry_date': '2025-10-25'
        }

        impression_id = save_impression(temp_db, impression_data)

        # Пытаемся отвязать от другого пользователя
        success = unlink_impression(temp_db, impression_id, 99999)
        assert success is False


class TestGetEntryImpressions:
    """Тесты получения впечатлений для записи."""

    def test_get_impressions_for_entry(self, temp_db):
        """Получение всех впечатлений для записи."""
        # Создаем несколько впечатлений
        impressions_data = [
            {
                'chat_id': 12345,
                'text': 'Утро',
                'date': '2025-10-25',
                'time': '10:00:00',
                'category': 'positive',
                'intensity': 8,
                'entry_date': '2025-10-25'
            },
            {
                'chat_id': 12345,
                'text': 'День',
                'date': '2025-10-25',
                'time': '14:00:00',
                'category': 'neutral',
                'intensity': 6,
                'entry_date': '2025-10-25'
            },
            {
                'chat_id': 12345,
                'text': 'Другой день',
                'date': '2025-10-26',
                'time': '10:00:00',
                'category': 'positive',
                'intensity': 7,
                'entry_date': '2025-10-26'
            },
            {
                'chat_id': 12345,
                'text': 'Не привязано',
                'date': '2025-10-25',
                'time': '15:00:00',
                'category': 'neutral',
                'intensity': 5
            }
        ]

        # Создаем еще одну запись для теста
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO entries (chat_id, date, mood)
            VALUES (?, ?, ?)
        ''', (12345, '2025-10-26', 6))
        temp_db.commit()

        for imp_data in impressions_data:
            save_impression(temp_db, imp_data)

        # Получаем впечатления для 2025-10-25
        impressions = get_entry_impressions(temp_db, 12345, '2025-10-25')
        assert len(impressions) == 2
        assert all(imp['entry_date'] == '2025-10-25' for imp in impressions)

        texts = [imp['text'] for imp in impressions]
        assert 'Утро' in texts
        assert 'День' in texts

    def test_get_impressions_for_entry_no_impressions(self, temp_db):
        """Получение впечатлений для записи без впечатлений."""
        impressions = get_entry_impressions(temp_db, 12345, '2025-10-25')
        assert impressions == []

    def test_get_impressions_sorted_by_time(self, temp_db):
        """Впечатления сортируются по времени."""
        impressions_data = [
            {
                'chat_id': 12345,
                'text': 'Вечер',
                'date': '2025-10-25',
                'time': '20:00:00',
                'category': 'positive',
                'intensity': 8,
                'entry_date': '2025-10-25'
            },
            {
                'chat_id': 12345,
                'text': 'Утро',
                'date': '2025-10-25',
                'time': '08:00:00',
                'category': 'neutral',
                'intensity': 6,
                'entry_date': '2025-10-25'
            },
            {
                'chat_id': 12345,
                'text': 'День',
                'date': '2025-10-25',
                'time': '14:00:00',
                'category': 'positive',
                'intensity': 7,
                'entry_date': '2025-10-25'
            }
        ]

        for imp_data in impressions_data:
            save_impression(temp_db, imp_data)

        # Получаем впечатления
        impressions = get_entry_impressions(temp_db, 12345, '2025-10-25')
        assert len(impressions) == 3

        # Проверяем сортировку по времени
        texts = [imp['text'] for imp in impressions]
        assert texts == ['Утро', 'День', 'Вечер']
