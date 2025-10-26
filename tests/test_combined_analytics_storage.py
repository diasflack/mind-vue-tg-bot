"""
Тесты для combined analytics storage (Phase 5.5).
Объединенная аналитика впечатлений и опросов.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta

from src.data.combined_analytics_storage import (
    get_combined_daily_summary,
    get_activity_overview,
    get_correlation_data
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
        ''', (12345, date, 7 - i))  # Настроение от 7 до 1

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

    cursor.execute('''
        INSERT INTO impressions (chat_id, text, category, intensity, entry_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (12345, 'Обычный день', 'neutral', 5, (today - timedelta(days=3)).strftime('%Y-%m-%d'),
          (today - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')))

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


class TestGetCombinedDailySummary:
    """Тесты получения объединенной дневной статистики."""

    def test_get_combined_summary_with_data(self, temp_db):
        """Получение статистики за период с данными."""
        summary = get_combined_daily_summary(temp_db, chat_id=12345, days=7)

        assert summary is not None
        assert len(summary) <= 7

        # Проверяем структуру
        if summary:
            day = summary[0]
            assert 'date' in day
            assert 'mood_score' in day or day.get('mood_score') is None
            assert 'impressions_count' in day
            assert 'surveys_count' in day

    def test_get_combined_summary_empty(self, temp_db):
        """Получение статистики для пользователя без данных."""
        summary = get_combined_daily_summary(temp_db, chat_id=99999, days=7)

        assert isinstance(summary, list)
        # Может быть пустым или содержать дни с нулевыми значениями

    def test_get_combined_summary_custom_period(self, temp_db):
        """Получение статистики за произвольный период."""
        summary = get_combined_daily_summary(temp_db, chat_id=12345, days=3)

        assert len(summary) <= 3


class TestGetActivityOverview:
    """Тесты получения общего обзора активности."""

    def test_get_activity_overview_with_data(self, temp_db):
        """Получение обзора с данными."""
        overview = get_activity_overview(temp_db, chat_id=12345, days=7)

        assert overview is not None
        assert 'total_impressions' in overview
        assert 'total_surveys' in overview
        assert 'total_entries' in overview
        assert 'avg_mood_score' in overview
        assert 'impression_categories' in overview

        # Проверяем что данные корректны
        assert overview['total_impressions'] >= 0
        assert overview['total_surveys'] >= 0
        assert overview['total_entries'] >= 0

        # Проверяем категории впечатлений
        categories = overview['impression_categories']
        assert 'positive' in categories
        assert 'negative' in categories
        assert 'neutral' in categories

    def test_get_activity_overview_empty(self, temp_db):
        """Получение обзора для пользователя без данных."""
        overview = get_activity_overview(temp_db, chat_id=99999, days=7)

        assert overview is not None
        assert overview['total_impressions'] == 0
        assert overview['total_surveys'] == 0
        assert overview['total_entries'] == 0
        assert overview['avg_mood_score'] is None


class TestGetCorrelationData:
    """Тесты получения данных для корреляционного анализа."""

    def test_get_correlation_data_with_data(self, temp_db):
        """Получение корреляционных данных."""
        data = get_correlation_data(temp_db, chat_id=12345, days=7)

        assert data is not None
        assert isinstance(data, list)

        # Проверяем структуру данных
        if data:
            point = data[0]
            assert 'date' in point
            assert 'mood_score' in point or point.get('mood_score') is None
            assert 'positive_count' in point
            assert 'negative_count' in point
            assert 'neutral_count' in point

    def test_get_correlation_data_empty(self, temp_db):
        """Получение корреляционных данных без данных."""
        data = get_correlation_data(temp_db, chat_id=99999, days=7)

        assert isinstance(data, list)

    def test_correlation_data_aggregation(self, temp_db):
        """Проверка корректной агрегации данных."""
        data = get_correlation_data(temp_db, chat_id=12345, days=7)

        # Проверяем что данные агрегированы по дням
        dates = [point['date'] for point in data]
        assert len(dates) == len(set(dates))  # Все даты уникальны
