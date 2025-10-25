"""
Тесты для функций управления напоминаниями по опросам (Phase 5.2).
"""

import pytest
import sqlite3
from datetime import datetime

from src.data.survey_notifications_storage import (
    set_survey_reminder,
    remove_survey_reminder,
    get_survey_reminders,
    get_surveys_for_notification,
    is_survey_filled_today
)


@pytest.fixture
def temp_db(mock_config):
    """Создает временную БД с таблицами для опросов и напоминаний."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Создаем таблицу users
    cursor.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            notification_time TEXT,
            timezone_offset INTEGER DEFAULT 0
        )
    ''')

    # Создаем таблицу survey_templates
    cursor.execute('''
        CREATE TABLE survey_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Создаем таблицу user_survey_preferences
    cursor.execute('''
        CREATE TABLE user_survey_preferences (
            chat_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            is_favorite BOOLEAN DEFAULT 0,
            notification_enabled BOOLEAN DEFAULT 0,
            notification_time TEXT,
            PRIMARY KEY (chat_id, template_id),
            FOREIGN KEY (chat_id) REFERENCES users(chat_id),
            FOREIGN KEY (template_id) REFERENCES survey_templates(id) ON DELETE CASCADE
        )
    ''')

    # Создаем таблицу survey_responses для проверки заполнения
    cursor.execute('''
        CREATE TABLE survey_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            response_date TEXT NOT NULL,
            response_time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Добавляем тестовые данные
    cursor.execute('INSERT INTO users (chat_id, username, timezone_offset) VALUES (?, ?, ?)',
                   (12345, 'testuser', 3))

    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, created_by)
        VALUES (1, 'Настроение', 'Ежедневная оценка настроения', 12345)
    ''')

    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, created_by)
        VALUES (2, 'Тревога', 'Оценка уровня тревоги', 12345)
    ''')

    conn.commit()
    yield conn
    conn.close()


class TestSetSurveyReminder:
    """Тесты установки напоминания для опроса."""

    def test_set_reminder_new(self, temp_db):
        """Установка нового напоминания."""
        result = set_survey_reminder(
            temp_db,
            chat_id=12345,
            template_id=1,
            notification_time='09:00',
            timezone_offset=3
        )

        assert result is True

        # Проверяем что запись создана
        cursor = temp_db.cursor()
        cursor.execute('''
            SELECT notification_enabled, notification_time
            FROM user_survey_preferences
            WHERE chat_id = ? AND template_id = ?
        ''', (12345, 1))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 1  # notification_enabled
        assert row[1] == '06:00'  # UTC time (09:00 - 3 hours)

    def test_set_reminder_update_existing(self, temp_db):
        """Обновление существующего напоминания."""
        # Создаем существующую запись
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, 1, '08:00'))
        temp_db.commit()

        # Обновляем
        result = set_survey_reminder(
            temp_db,
            chat_id=12345,
            template_id=1,
            notification_time='10:00',
            timezone_offset=3
        )

        assert result is True

        # Проверяем обновление
        cursor.execute('''
            SELECT notification_time
            FROM user_survey_preferences
            WHERE chat_id = ? AND template_id = ?
        ''', (12345, 1))
        row = cursor.fetchone()

        assert row[0] == '07:00'  # UTC time (10:00 - 3 hours)

    def test_set_reminder_nonexistent_survey(self, temp_db):
        """Попытка установить напоминание для несуществующего опроса."""
        result = set_survey_reminder(
            temp_db,
            chat_id=12345,
            template_id=999,
            notification_time='09:00',
            timezone_offset=3
        )

        assert result is False


class TestRemoveSurveyReminder:
    """Тесты удаления напоминания."""

    def test_remove_reminder_success(self, temp_db):
        """Успешное удаление напоминания."""
        # Создаем напоминание
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, 1, '09:00'))
        temp_db.commit()

        # Удаляем
        result = remove_survey_reminder(temp_db, chat_id=12345, template_id=1)

        assert result is True

        # Проверяем что отключено
        cursor.execute('''
            SELECT notification_enabled
            FROM user_survey_preferences
            WHERE chat_id = ? AND template_id = ?
        ''', (12345, 1))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 0  # Отключено

    def test_remove_reminder_nonexistent(self, temp_db):
        """Удаление несуществующего напоминания."""
        result = remove_survey_reminder(temp_db, chat_id=12345, template_id=1)

        # Должно вернуть False т.к. записи нет
        assert result is False


class TestGetSurveyReminders:
    """Тесты получения списка напоминаний пользователя."""

    def test_get_reminders_multiple(self, temp_db):
        """Получение нескольких напоминаний."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, 1, '09:00'))
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 2, 1, '20:00'))
        temp_db.commit()

        reminders = get_survey_reminders(temp_db, chat_id=12345)

        assert len(reminders) == 2
        assert reminders[0]['template_id'] == 1
        assert reminders[0]['survey_name'] == 'Настроение'
        assert reminders[0]['notification_time'] == '09:00'
        assert reminders[0]['notification_enabled'] == 1

    def test_get_reminders_empty(self, temp_db):
        """Получение пустого списка напоминаний."""
        reminders = get_survey_reminders(temp_db, chat_id=12345)

        assert len(reminders) == 0

    def test_get_reminders_only_enabled(self, temp_db):
        """Получение только включенных напоминаний."""
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

        # Получаем все
        all_reminders = get_survey_reminders(temp_db, chat_id=12345)
        assert len(all_reminders) == 2

        # Получаем только включенные
        enabled_reminders = get_survey_reminders(temp_db, chat_id=12345, enabled_only=True)
        assert len(enabled_reminders) == 1
        assert enabled_reminders[0]['template_id'] == 1


class TestGetSurveysForNotification:
    """Тесты получения опросов для отправки уведомлений."""

    def test_get_surveys_for_time(self, temp_db):
        """Получение опросов для текущего времени."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, 1, '09:00'))
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 2, 1, '20:00'))
        temp_db.commit()

        # Получаем для времени 09:00
        surveys = get_surveys_for_notification(temp_db, current_time='09:00')

        assert len(surveys) == 1
        assert surveys[0]['chat_id'] == 12345
        assert surveys[0]['template_id'] == 1
        assert surveys[0]['survey_name'] == 'Настроение'

    def test_get_surveys_no_matches(self, temp_db):
        """Нет опросов для текущего времени."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, 1, '09:00'))
        temp_db.commit()

        # Получаем для времени 10:00
        surveys = get_surveys_for_notification(temp_db, current_time='10:00')

        assert len(surveys) == 0

    def test_get_surveys_only_enabled(self, temp_db):
        """Получение только включенных опросов."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, 1, '09:00'))
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, notification_enabled, notification_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 2, 0, '09:00'))
        temp_db.commit()

        surveys = get_surveys_for_notification(temp_db, current_time='09:00')

        # Должен быть только включенный
        assert len(surveys) == 1
        assert surveys[0]['template_id'] == 1


class TestIsSurveyFilledToday:
    """Тесты проверки заполнения опроса сегодня."""

    def test_survey_filled_today(self, temp_db):
        """Опрос заполнен сегодня."""
        today = datetime.now().strftime('%Y-%m-%d')

        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO survey_responses (chat_id, template_id, response_date, response_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, today, '10:00:00'))
        temp_db.commit()

        result = is_survey_filled_today(temp_db, chat_id=12345, template_id=1)

        assert result is True

    def test_survey_not_filled_today(self, temp_db):
        """Опрос не заполнен сегодня."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO survey_responses (chat_id, template_id, response_date, response_time)
            VALUES (?, ?, ?, ?)
        ''', (12345, 1, '2025-10-24', '10:00:00'))
        temp_db.commit()

        result = is_survey_filled_today(temp_db, chat_id=12345, template_id=1)

        assert result is False

    def test_survey_never_filled(self, temp_db):
        """Опрос никогда не заполнялся."""
        result = is_survey_filled_today(temp_db, chat_id=12345, template_id=1)

        assert result is False
