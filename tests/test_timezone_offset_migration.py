"""
Тесты для миграции timezone_offset.
"""

import pytest
import sqlite3

from src.data.migrations.add_timezone_offset import migrate


@pytest.fixture
def temp_db():
    """Создает временную БД без timezone_offset."""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    # Создаем таблицу users БЕЗ timezone_offset (старая схема)
    cursor.execute('''
        CREATE TABLE users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            notification_time TEXT
        )
    ''')

    # Добавляем тестового пользователя
    cursor.execute('''
        INSERT INTO users (chat_id, username, first_name, notification_time)
        VALUES (12345, 'testuser', 'Test User', '09:00')
    ''')

    conn.commit()
    yield conn
    conn.close()


class TestTimezoneMigration:
    """Тесты миграции timezone_offset."""

    def test_migration_adds_column(self, temp_db):
        """Миграция добавляет колонку timezone_offset."""
        cursor = temp_db.cursor()

        # Проверяем что колонки нет
        cursor.execute("PRAGMA table_info(users)")
        columns_before = [row[1] for row in cursor.fetchall()]
        assert 'timezone_offset' not in columns_before

        # Выполняем миграцию
        migrate(temp_db)

        # Проверяем что колонка добавлена
        cursor.execute("PRAGMA table_info(users)")
        columns_after = [row[1] for row in cursor.fetchall()]
        assert 'timezone_offset' in columns_after

    def test_migration_preserves_data(self, temp_db):
        """Миграция сохраняет существующие данные."""
        # Выполняем миграцию
        migrate(temp_db)

        # Проверяем что данные сохранились
        cursor = temp_db.cursor()
        cursor.execute('SELECT chat_id, username, timezone_offset FROM users WHERE chat_id = 12345')
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 12345
        assert row[1] == 'testuser'
        assert row[2] == 0  # default value

    def test_migration_sets_default_value(self, temp_db):
        """Миграция устанавливает значение по умолчанию 0."""
        migrate(temp_db)

        cursor = temp_db.cursor()
        cursor.execute('SELECT timezone_offset FROM users')
        timezone_offset = cursor.fetchone()[0]

        assert timezone_offset == 0

    def test_migration_idempotent(self, temp_db):
        """Миграция идемпотентна (можно запускать многократно)."""
        # Первый запуск
        migrate(temp_db)

        # Второй запуск не должен вызывать ошибку
        try:
            migrate(temp_db)
        except Exception as e:
            pytest.fail(f"Повторный запуск миграции вызвал ошибку: {e}")

        # Проверяем что колонка одна
        cursor = temp_db.cursor()
        cursor.execute("PRAGMA table_info(users)")
        timezone_columns = [row for row in cursor.fetchall() if row[1] == 'timezone_offset']
        assert len(timezone_columns) == 1

    def test_new_users_get_default_timezone(self, temp_db):
        """Новые пользователи получают timezone_offset по умолчанию."""
        # Выполняем миграцию
        migrate(temp_db)

        # Добавляем нового пользователя
        cursor = temp_db.cursor()
        cursor.execute('''
            INSERT INTO users (chat_id, username)
            VALUES (67890, 'newuser')
        ''')

        # Проверяем что timezone_offset = 0
        cursor.execute('SELECT timezone_offset FROM users WHERE chat_id = 67890')
        timezone_offset = cursor.fetchone()[0]

        assert timezone_offset == 0
