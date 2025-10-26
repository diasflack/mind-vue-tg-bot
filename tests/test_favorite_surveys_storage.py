"""
Тесты для функций управления избранными опросами (Phase 5.3).
"""

import pytest
import sqlite3

from src.data.favorite_surveys_storage import (
    add_to_favorites,
    remove_from_favorites,
    get_favorite_surveys,
    is_favorite
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
        VALUES (2, 'Тревога', 'Оценка тревоги', 1, 1)
    ''')

    cursor.execute('''
        INSERT INTO survey_templates (id, name, description, is_system, is_active)
        VALUES (3, 'Сон', 'Дневник сна', 1, 1)
    ''')

    conn.commit()
    yield conn
    conn.close()


class TestAddToFavorites:
    """Тесты добавления опроса в избранное."""

    def test_add_to_favorites_new(self, temp_db):
        """Добавление нового избранного опроса."""
        result = add_to_favorites(temp_db, chat_id=12345, template_id=1)

        assert result is True

        # Проверяем что запись создана
        cursor = temp_db.cursor()
        cursor.execute('''
            SELECT is_favorite FROM user_survey_preferences
            WHERE chat_id = ? AND template_id = ?
        ''', (12345, 1))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 1  # is_favorite = True

    def test_add_to_favorites_update_existing(self, temp_db):
        """Обновление существующей записи."""
        # Создаем существующую запись без избранного
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 1, 0))
        temp_db.commit()

        # Добавляем в избранное
        result = add_to_favorites(temp_db, chat_id=12345, template_id=1)

        assert result is True

        # Проверяем обновление
        cursor.execute('''
            SELECT is_favorite FROM user_survey_preferences
            WHERE chat_id = ? AND template_id = ?
        ''', (12345, 1))
        row = cursor.fetchone()

        assert row[0] == 1

    def test_add_to_favorites_nonexistent_survey(self, temp_db):
        """Попытка добавить несуществующий опрос."""
        result = add_to_favorites(temp_db, chat_id=12345, template_id=999)

        assert result is False

    def test_add_to_favorites_already_favorite(self, temp_db):
        """Добавление опроса который уже в избранном."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 1, 1))
        temp_db.commit()

        # Попытка добавить снова - должно пройти успешно (идемпотентность)
        result = add_to_favorites(temp_db, chat_id=12345, template_id=1)

        assert result is True


class TestRemoveFromFavorites:
    """Тесты удаления опроса из избранного."""

    def test_remove_from_favorites_success(self, temp_db):
        """Успешное удаление из избранного."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 1, 1))
        temp_db.commit()

        result = remove_from_favorites(temp_db, chat_id=12345, template_id=1)

        assert result is True

        # Проверяем что отключено
        cursor.execute('''
            SELECT is_favorite FROM user_survey_preferences
            WHERE chat_id = ? AND template_id = ?
        ''', (12345, 1))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 0  # is_favorite = False

    def test_remove_from_favorites_nonexistent(self, temp_db):
        """Удаление несуществующей записи."""
        result = remove_from_favorites(temp_db, chat_id=12345, template_id=1)

        # Должно вернуть False т.к. записи нет
        assert result is False

    def test_remove_from_favorites_not_favorite(self, temp_db):
        """Удаление опроса который не в избранном."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 1, 0))
        temp_db.commit()

        result = remove_from_favorites(temp_db, chat_id=12345, template_id=1)

        # Должно пройти успешно (идемпотентность)
        assert result is True


class TestGetFavoriteSurveys:
    """Тесты получения списка избранных опросов."""

    def test_get_favorite_surveys_multiple(self, temp_db):
        """Получение нескольких избранных опросов."""
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

        favorites = get_favorite_surveys(temp_db, chat_id=12345)

        assert len(favorites) == 2
        assert favorites[0]['template_id'] == 1
        assert favorites[0]['survey_name'] == 'Настроение'
        assert favorites[1]['template_id'] == 2
        assert favorites[1]['survey_name'] == 'Тревога'

    def test_get_favorite_surveys_empty(self, temp_db):
        """Получение пустого списка избранных."""
        favorites = get_favorite_surveys(temp_db, chat_id=12345)

        assert len(favorites) == 0

    def test_get_favorite_surveys_includes_metadata(self, temp_db):
        """Список избранных включает метаданные опросов."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 1, 1))
        temp_db.commit()

        favorites = get_favorite_surveys(temp_db, chat_id=12345)

        assert len(favorites) == 1
        assert 'template_id' in favorites[0]
        assert 'survey_name' in favorites[0]
        assert 'description' in favorites[0]
        assert 'is_system' in favorites[0]


class TestIsFavorite:
    """Тесты проверки находится ли опрос в избранном."""

    def test_is_favorite_true(self, temp_db):
        """Опрос в избранном."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 1, 1))
        temp_db.commit()

        result = is_favorite(temp_db, chat_id=12345, template_id=1)

        assert result is True

    def test_is_favorite_false(self, temp_db):
        """Опрос не в избранном."""
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO user_survey_preferences (chat_id, template_id, is_favorite)
            VALUES (?, ?, ?)
        ''', (12345, 1, 0))
        temp_db.commit()

        result = is_favorite(temp_db, chat_id=12345, template_id=1)

        assert result is False

    def test_is_favorite_no_record(self, temp_db):
        """Нет записи для опроса."""
        result = is_favorite(temp_db, chat_id=12345, template_id=1)

        assert result is False
