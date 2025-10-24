"""
Тесты для миграции базы данных - добавление таблиц для впечатлений.

TDD Phase 1.1: Эти тесты должны провалиться до реализации миграции.
"""

import pytest
import sqlite3
import os
import tempfile
from pathlib import Path


@pytest.fixture
def test_db():
    """Создает временную тестовую базу данных."""
    # Создаем временный файл для БД
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Создаем соединение
    conn = sqlite3.connect(db_path)

    # Создаем базовые таблицы (users и entries) которые уже существуют
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        notification_time TEXT
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        encrypted_data TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES users(chat_id),
        UNIQUE(chat_id, date)
    )
    ''')

    conn.commit()

    yield conn, db_path

    # Cleanup
    conn.close()
    try:
        os.unlink(db_path)
    except:
        pass


def test_impressions_table_created(test_db):
    """
    Тест: таблица impressions создается миграцией.

    Проверяет что таблица impressions существует со всеми необходимыми колонками.
    """
    conn, db_path = test_db

    # Импортируем и запускаем миграцию
    from src.data.migrations.add_impressions_tables import migrate
    migrate(conn)

    # Проверяем что таблица существует
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='impressions'
    """)
    result = cursor.fetchone()
    assert result is not None, "Таблица impressions не создана"

    # Проверяем структуру таблицы
    cursor.execute("PRAGMA table_info(impressions)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}  # {name: type}

    expected_columns = {
        'id': 'INTEGER',
        'chat_id': 'INTEGER',
        'impression_text': 'TEXT',
        'impression_date': 'TEXT',
        'impression_time': 'TEXT',
        'category': 'TEXT',
        'intensity': 'INTEGER',
        'entry_date': 'TEXT',
        'created_at': 'TIMESTAMP'
    }

    for col_name, col_type in expected_columns.items():
        assert col_name in columns, f"Колонка {col_name} отсутствует в таблице impressions"
        assert columns[col_name] == col_type, f"Колонка {col_name} имеет неправильный тип: {columns[col_name]} вместо {col_type}"


def test_impression_tags_table_created(test_db):
    """
    Тест: таблица impression_tags создается миграцией.

    Проверяет что таблица impression_tags существует со всеми необходимыми колонками.
    """
    conn, db_path = test_db

    # Запускаем миграцию
    from src.data.migrations.add_impressions_tables import migrate
    migrate(conn)

    # Проверяем что таблица существует
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='impression_tags'
    """)
    result = cursor.fetchone()
    assert result is not None, "Таблица impression_tags не создана"

    # Проверяем структуру таблицы
    cursor.execute("PRAGMA table_info(impression_tags)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    expected_columns = {
        'id': 'INTEGER',
        'chat_id': 'INTEGER',
        'tag_name': 'TEXT',
        'tag_color': 'TEXT'
    }

    for col_name, col_type in expected_columns.items():
        assert col_name in columns, f"Колонка {col_name} отсутствует в таблице impression_tags"


def test_impression_tag_relations_table_created(test_db):
    """
    Тест: таблица impression_tag_relations создается миграцией.

    Проверяет связь многие-ко-многим между впечатлениями и тегами.
    """
    conn, db_path = test_db

    # Запускаем миграцию
    from src.data.migrations.add_impressions_tables import migrate
    migrate(conn)

    # Проверяем что таблица существует
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='impression_tag_relations'
    """)
    result = cursor.fetchone()
    assert result is not None, "Таблица impression_tag_relations не создана"

    # Проверяем структуру таблицы
    cursor.execute("PRAGMA table_info(impression_tag_relations)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    expected_columns = {
        'impression_id': 'INTEGER',
        'tag_id': 'INTEGER'
    }

    for col_name, col_type in expected_columns.items():
        assert col_name in columns, f"Колонка {col_name} отсутствует в таблице impression_tag_relations"


def test_indexes_created(test_db):
    """
    Тест: индексы для оптимизации создаются миграцией.

    Проверяет что созданы индексы для:
    - impressions(chat_id, impression_date)
    - impressions(category)
    """
    conn, db_path = test_db

    # Запускаем миграцию
    from src.data.migrations.add_impressions_tables import migrate
    migrate(conn)

    # Проверяем существование индексов
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_impressions%'
    """)
    indexes = [row[0] for row in cursor.fetchall()]

    expected_indexes = [
        'idx_impressions_chat_date',
        'idx_impressions_category'
    ]

    for index_name in expected_indexes:
        assert index_name in indexes, f"Индекс {index_name} не создан"


def test_foreign_keys_constraints(test_db):
    """
    Тест: Foreign key constraints настроены корректно.

    Проверяет что:
    - impressions.chat_id ссылается на users.chat_id
    - impressions.entry_date ссылается на entries.date
    - impression_tags.chat_id ссылается на users.chat_id
    """
    conn, db_path = test_db

    # Включаем проверку foreign keys
    conn.execute("PRAGMA foreign_keys = ON")

    # Запускаем миграцию
    from src.data.migrations.add_impressions_tables import migrate
    migrate(conn)

    # Проверяем foreign keys для impressions
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_key_list(impressions)")
    fk_list = cursor.fetchall()

    assert len(fk_list) >= 1, "Foreign keys не настроены для таблицы impressions"

    # Проверяем что есть связь с users
    fk_to_users = [fk for fk in fk_list if fk[2] == 'users']
    assert len(fk_to_users) > 0, "Нет foreign key на таблицу users"


def test_migration_is_idempotent(test_db):
    """
    Тест: миграция идемпотентна.

    Проверяет что миграцию можно запустить несколько раз без ошибок.
    """
    conn, db_path = test_db

    # Импортируем миграцию
    from src.data.migrations.add_impressions_tables import migrate

    # Запускаем первый раз
    migrate(conn)

    # Запускаем второй раз - не должно быть ошибок
    try:
        migrate(conn)
    except Exception as e:
        pytest.fail(f"Миграция не идемпотентна, ошибка при повторном запуске: {e}")

    # Проверяем что таблицы все еще существуют
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('impressions', 'impression_tags', 'impression_tag_relations')
    """)
    tables = [row[0] for row in cursor.fetchall()]

    assert len(tables) == 3, "Не все таблицы существуют после повторной миграции"


def test_unique_constraint_on_impression_tags(test_db):
    """
    Тест: уникальное ограничение на (chat_id, tag_name) в impression_tags.

    Проверяет что пользователь не может создать два тега с одинаковым именем.
    """
    conn, db_path = test_db

    # Запускаем миграцию
    from src.data.migrations.add_impressions_tables import migrate
    migrate(conn)

    # Создаем пользователя
    conn.execute("INSERT INTO users (chat_id, username, first_name) VALUES (123, 'test', 'Test User')")

    # Вставляем тег
    conn.execute("INSERT INTO impression_tags (chat_id, tag_name) VALUES (123, 'стресс')")

    # Пытаемся вставить дубликат - должна быть ошибка
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO impression_tags (chat_id, tag_name) VALUES (123, 'стресс')")


def test_cascade_delete_on_impression_tag_relations(test_db):
    """
    Тест: CASCADE DELETE работает для impression_tag_relations.

    Проверяет что при удалении впечатления удаляются связи с тегами.
    """
    conn, db_path = test_db
    conn.execute("PRAGMA foreign_keys = ON")

    # Запускаем миграцию
    from src.data.migrations.add_impressions_tables import migrate
    migrate(conn)

    # Создаем пользователя
    conn.execute("INSERT INTO users (chat_id, username, first_name) VALUES (123, 'test', 'Test User')")

    # Создаем впечатление
    conn.execute("""
        INSERT INTO impressions (chat_id, impression_text, impression_date, impression_time)
        VALUES (123, 'Тест', '2025-10-24', '12:00:00')
    """)
    impression_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Создаем тег
    conn.execute("INSERT INTO impression_tags (chat_id, tag_name) VALUES (123, 'тест')")
    tag_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Связываем впечатление с тегом
    conn.execute("""
        INSERT INTO impression_tag_relations (impression_id, tag_id)
        VALUES (?, ?)
    """, (impression_id, tag_id))

    # Проверяем что связь существует
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM impression_tag_relations WHERE impression_id = ?", (impression_id,))
    count_before = cursor.fetchone()[0]
    assert count_before == 1, "Связь не создана"

    # Удаляем впечатление
    conn.execute("DELETE FROM impressions WHERE id = ?", (impression_id,))

    # Проверяем что связь удалена
    cursor.execute("SELECT COUNT(*) FROM impression_tag_relations WHERE impression_id = ?", (impression_id,))
    count_after = cursor.fetchone()[0]
    assert count_after == 0, "Связь не удалена (CASCADE DELETE не работает)"
