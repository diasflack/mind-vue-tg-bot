"""
Тесты для хранилища впечатлений (impressions_storage.py).

TDD Phase 1.3: Эти тесты должны провалиться до реализации хранилища.
"""

import pytest
import sqlite3
import os
import tempfile
from datetime import datetime


@pytest.fixture
def test_db_with_schema():
    """Создает временную БД с полной схемой (включая impressions таблицы)."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # Создаем базовые таблицы
    conn.execute('''
    CREATE TABLE users (
        chat_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        notification_time TEXT
    )
    ''')

    conn.execute('''
    CREATE TABLE entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        encrypted_data TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES users(chat_id),
        UNIQUE(chat_id, date)
    )
    ''')

    # Применяем миграцию для impressions
    from src.data.migrations.add_impressions_tables import migrate
    migrate(conn)

    # Создаем тестового пользователя
    conn.execute("INSERT INTO users (chat_id, username, first_name) VALUES (123, 'test_user', 'Test')")
    conn.commit()

    yield conn, db_path

    conn.close()
    try:
        os.unlink(db_path)
    except:
        pass


def test_save_impression(test_db_with_schema):
    """
    Тест: сохранение впечатления в БД.
    """
    from src.data.impressions_storage import save_impression

    conn, db_path = test_db_with_schema
    chat_id = 123

    impression_data = {
        'chat_id': chat_id,
        'impression_text': "Хочется выпить",
        'impression_date': "2025-10-24",
        'impression_time': "18:45:00",
        'category': "craving",
        'intensity': 7,
        'entry_date': None
    }

    # Сохраняем впечатление
    result = save_impression(conn, impression_data)

    assert result is True, "save_impression должна вернуть True"

    # Проверяем что впечатление сохранено
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM impressions WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()

    assert row is not None, "Впечатление не сохранено в БД"
    assert row[2] == "Хочется выпить"  # impression_text
    assert row[5] == "craving"  # category
    assert row[6] == 7  # intensity


def test_save_impression_without_optional_fields(test_db_with_schema):
    """
    Тест: сохранение впечатления без опциональных полей.
    """
    from src.data.impressions_storage import save_impression

    conn, db_path = test_db_with_schema
    chat_id = 123

    impression_data = {
        'chat_id': chat_id,
        'impression_text': "Просто впечатление",
        'impression_date': "2025-10-24",
        'impression_time': "12:00:00",
        'category': None,
        'intensity': None,
        'entry_date': None
    }

    result = save_impression(conn, impression_data)

    assert result is True

    cursor = conn.cursor()
    cursor.execute("SELECT category, intensity FROM impressions WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()

    assert row[0] is None  # category
    assert row[1] is None  # intensity


def test_get_user_impressions_all(test_db_with_schema):
    """
    Тест: получение всех впечатлений пользователя.
    """
    from src.data.impressions_storage import save_impression, get_user_impressions

    conn, db_path = test_db_with_schema
    chat_id = 123

    # Создаем несколько впечатлений
    impressions = [
        {
            'chat_id': chat_id,
            'impression_text': "Впечатление 1",
            'impression_date': "2025-10-24",
            'impression_time': "10:00:00",
            'category': "emotion",
            'intensity': 5,
            'entry_date': None
        },
        {
            'chat_id': chat_id,
            'impression_text': "Впечатление 2",
            'impression_date': "2025-10-24",
            'impression_time': "15:00:00",
            'category': "craving",
            'intensity': 8,
            'entry_date': None
        }
    ]

    for imp in impressions:
        save_impression(conn, imp)

    # Получаем все впечатления (сортировка от новых к старым)
    results = get_user_impressions(conn, chat_id)

    assert len(results) == 2, "Должно быть 2 впечатления"
    # Сортировка DESC: сначала 15:00 (Впечатление 2), потом 10:00 (Впечатление 1)
    assert results[0]['impression_text'] == "Впечатление 2"
    assert results[1]['impression_text'] == "Впечатление 1"


def test_get_user_impressions_by_date(test_db_with_schema):
    """
    Тест: получение впечатлений за определенную дату.
    """
    from src.data.impressions_storage import save_impression, get_user_impressions

    conn, db_path = test_db_with_schema
    chat_id = 123

    # Создаем впечатления за разные даты
    impressions = [
        {
            'chat_id': chat_id,
            'impression_text': "Вчера",
            'impression_date': "2025-10-23",
            'impression_time': "10:00:00",
            'category': None,
            'intensity': None,
            'entry_date': None
        },
        {
            'chat_id': chat_id,
            'impression_text': "Сегодня 1",
            'impression_date': "2025-10-24",
            'impression_time': "10:00:00",
            'category': None,
            'intensity': None,
            'entry_date': None
        },
        {
            'chat_id': chat_id,
            'impression_text': "Сегодня 2",
            'impression_date': "2025-10-24",
            'impression_time': "15:00:00",
            'category': None,
            'intensity': None,
            'entry_date': None
        }
    ]

    for imp in impressions:
        save_impression(conn, imp)

    # Получаем впечатления за 2025-10-24
    results = get_user_impressions(conn, chat_id, date="2025-10-24")

    assert len(results) == 2, "Должно быть 2 впечатления за 24.10"
    assert all(r['impression_date'] == "2025-10-24" for r in results)


def test_get_user_impressions_by_category(test_db_with_schema):
    """
    Тест: фильтрация впечатлений по категории.
    """
    from src.data.impressions_storage import save_impression, get_user_impressions

    conn, db_path = test_db_with_schema
    chat_id = 123

    impressions = [
        {
            'chat_id': chat_id,
            'impression_text': "Эмоция",
            'impression_date': "2025-10-24",
            'impression_time': "10:00:00",
            'category': "emotion",
            'intensity': 5,
            'entry_date': None
        },
        {
            'chat_id': chat_id,
            'impression_text': "Влечение",
            'impression_date': "2025-10-24",
            'impression_time': "15:00:00",
            'category': "craving",
            'intensity': 8,
            'entry_date': None
        }
    ]

    for imp in impressions:
        save_impression(conn, imp)

    # Фильтруем по категории "craving"
    results = get_user_impressions(conn, chat_id, category="craving")

    assert len(results) == 1, "Должно быть 1 впечатление с категорией craving"
    assert results[0]['category'] == "craving"
    assert results[0]['impression_text'] == "Влечение"


def test_delete_impression(test_db_with_schema):
    """
    Тест: удаление впечатления.
    """
    from src.data.impressions_storage import save_impression, delete_impression, get_user_impressions

    conn, db_path = test_db_with_schema
    chat_id = 123

    impression_data = {
        'chat_id': chat_id,
        'impression_text': "Тест",
        'impression_date': "2025-10-24",
        'impression_time': "12:00:00",
        'category': None,
        'intensity': None,
        'entry_date': None
    }

    save_impression(conn, impression_data)

    # Получаем ID впечатления
    results = get_user_impressions(conn, chat_id)
    impression_id = results[0]['id']

    # Удаляем
    result = delete_impression(conn, impression_id, chat_id)

    assert result is True, "delete_impression должна вернуть True"

    # Проверяем что удалено
    results_after = get_user_impressions(conn, chat_id)
    assert len(results_after) == 0, "Впечатление должно быть удалено"


def test_delete_impression_wrong_user(test_db_with_schema):
    """
    Тест: нельзя удалить чужое впечатление.
    """
    from src.data.impressions_storage import save_impression, delete_impression, get_user_impressions

    conn, db_path = test_db_with_schema
    chat_id = 123
    other_chat_id = 456

    # Создаем пользователя 456
    conn.execute("INSERT INTO users (chat_id, username, first_name) VALUES (456, 'other', 'Other')")
    conn.commit()

    impression_data = {
        'chat_id': chat_id,
        'impression_text': "Тест",
        'impression_date': "2025-10-24",
        'impression_time': "12:00:00",
        'category': None,
        'intensity': None,
        'entry_date': None
    }

    save_impression(conn, impression_data)
    results = get_user_impressions(conn, chat_id)
    impression_id = results[0]['id']

    # Пытаемся удалить от другого пользователя
    result = delete_impression(conn, impression_id, other_chat_id)

    assert result is False, "Не должно быть возможности удалить чужое впечатление"

    # Проверяем что впечатление не удалено
    results_after = get_user_impressions(conn, chat_id)
    assert len(results_after) == 1, "Впечатление не должно быть удалено"


def test_create_tag(test_db_with_schema):
    """
    Тест: создание тега.
    """
    from src.data.impressions_storage import create_tag

    conn, db_path = test_db_with_schema
    chat_id = 123

    tag_id = create_tag(conn, chat_id, "алкоголь", color="#FF0000")

    assert tag_id is not None, "create_tag должна вернуть ID тега"
    assert isinstance(tag_id, int)

    # Проверяем что тег создан
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM impression_tags WHERE id = ?", (tag_id,))
    row = cursor.fetchone()

    assert row is not None
    assert row[2] == "алкоголь"  # tag_name
    assert row[3] == "#FF0000"  # tag_color


def test_create_duplicate_tag(test_db_with_schema):
    """
    Тест: создание дубликата тега возвращает существующий ID.
    """
    from src.data.impressions_storage import create_tag

    conn, db_path = test_db_with_schema
    chat_id = 123

    # Создаем тег первый раз
    tag_id_1 = create_tag(conn, chat_id, "стресс")

    # Создаем тег второй раз с тем же именем
    tag_id_2 = create_tag(conn, chat_id, "стресс")

    # Должен вернуться тот же ID
    assert tag_id_1 == tag_id_2, "Дубликат тега должен вернуть существующий ID"

    # Проверяем что в БД только один тег
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM impression_tags WHERE chat_id = ? AND tag_name = ?", (chat_id, "стресс"))
    count = cursor.fetchone()[0]
    assert count == 1


def test_get_user_tags(test_db_with_schema):
    """
    Тест: получение всех тегов пользователя.
    """
    from src.data.impressions_storage import create_tag, get_user_tags

    conn, db_path = test_db_with_schema
    chat_id = 123

    # Создаем несколько тегов
    create_tag(conn, chat_id, "алкоголь")
    create_tag(conn, chat_id, "стресс")
    create_tag(conn, chat_id, "работа")

    # Получаем все теги
    tags = get_user_tags(conn, chat_id)

    assert len(tags) == 3, "Должно быть 3 тега"
    tag_names = [t['tag_name'] for t in tags]
    assert "алкоголь" in tag_names
    assert "стресс" in tag_names
    assert "работа" in tag_names


def test_attach_tags_to_impression(test_db_with_schema):
    """
    Тест: привязка тегов к впечатлению.
    """
    from src.data.impressions_storage import (
        save_impression, create_tag, attach_tags_to_impression,
        get_user_impressions
    )

    conn, db_path = test_db_with_schema
    chat_id = 123

    # Создаем впечатление
    impression_data = {
        'chat_id': chat_id,
        'impression_text': "Хочется выпить",
        'impression_date': "2025-10-24",
        'impression_time': "18:45:00",
        'category': "craving",
        'intensity': 7,
        'entry_date': None
    }
    save_impression(conn, impression_data)

    results = get_user_impressions(conn, chat_id)
    impression_id = results[0]['id']

    # Создаем теги
    tag_id_1 = create_tag(conn, chat_id, "алкоголь")
    tag_id_2 = create_tag(conn, chat_id, "стресс")

    # Привязываем теги к впечатлению
    result = attach_tags_to_impression(conn, impression_id, [tag_id_1, tag_id_2])

    assert result is True, "attach_tags_to_impression должна вернуть True"

    # Проверяем что связи созданы
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM impression_tag_relations WHERE impression_id = ?",
        (impression_id,)
    )
    count = cursor.fetchone()[0]
    assert count == 2, "Должно быть 2 связи"


def test_get_impressions_with_tags(test_db_with_schema):
    """
    Тест: получение впечатлений с привязанными тегами.
    """
    from src.data.impressions_storage import (
        save_impression, create_tag, attach_tags_to_impression,
        get_user_impressions
    )

    conn, db_path = test_db_with_schema
    chat_id = 123

    # Создаем впечатление
    impression_data = {
        'chat_id': chat_id,
        'impression_text': "Тест",
        'impression_date': "2025-10-24",
        'impression_time': "12:00:00",
        'category': None,
        'intensity': None,
        'entry_date': None
    }
    save_impression(conn, impression_data)

    results = get_user_impressions(conn, chat_id)
    impression_id = results[0]['id']

    # Создаем и привязываем теги
    tag_id_1 = create_tag(conn, chat_id, "тег1")
    tag_id_2 = create_tag(conn, chat_id, "тег2")
    attach_tags_to_impression(conn, impression_id, [tag_id_1, tag_id_2])

    # Получаем впечатления с тегами
    results_with_tags = get_user_impressions(conn, chat_id, include_tags=True)

    assert len(results_with_tags) == 1
    assert 'tags' in results_with_tags[0], "Должно быть поле tags"
    assert len(results_with_tags[0]['tags']) == 2, "Должно быть 2 тега"

    tag_names = [t['tag_name'] for t in results_with_tags[0]['tags']]
    assert "тег1" in tag_names
    assert "тег2" in tag_names


def test_get_impressions_by_date_range(test_db_with_schema):
    """
    Тест: получение впечатлений за диапазон дат.
    """
    from src.data.impressions_storage import save_impression, get_user_impressions

    conn, db_path = test_db_with_schema
    chat_id = 123

    # Создаем впечатления за разные даты
    dates = ["2025-10-20", "2025-10-22", "2025-10-24", "2025-10-26"]
    for i, date in enumerate(dates):
        impression_data = {
            'chat_id': chat_id,
            'impression_text': f"Впечатление {i}",
            'impression_date': date,
            'impression_time': "12:00:00",
            'category': None,
            'intensity': None,
            'entry_date': None
        }
        save_impression(conn, impression_data)

    # Получаем впечатления за диапазон 22-24 октября
    results = get_user_impressions(
        conn, chat_id,
        start_date="2025-10-22",
        end_date="2025-10-24"
    )

    assert len(results) == 2, "Должно быть 2 впечатления (22 и 24 октября)"
    dates_in_results = [r['impression_date'] for r in results]
    assert "2025-10-22" in dates_in_results
    assert "2025-10-24" in dates_in_results
    assert "2025-10-20" not in dates_in_results
    assert "2025-10-26" not in dates_in_results


def test_get_impressions_empty(test_db_with_schema):
    """
    Тест: получение впечатлений для пользователя без впечатлений.
    """
    from src.data.impressions_storage import get_user_impressions

    conn, db_path = test_db_with_schema
    chat_id = 123

    results = get_user_impressions(conn, chat_id)

    assert results == [], "Должен вернуться пустой список"


def test_get_impressions_ordered_by_time(test_db_with_schema):
    """
    Тест: впечатления возвращаются упорядоченными по дате и времени (от новых к старым).
    """
    from src.data.impressions_storage import save_impression, get_user_impressions

    conn, db_path = test_db_with_schema
    chat_id = 123

    # Создаем впечатления в разном порядке
    impressions = [
        {
            'chat_id': chat_id,
            'impression_text': "Первое",
            'impression_date': "2025-10-24",
            'impression_time': "10:00:00",
            'category': None,
            'intensity': None,
            'entry_date': None
        },
        {
            'chat_id': chat_id,
            'impression_text': "Третье",
            'impression_date': "2025-10-24",
            'impression_time': "15:00:00",
            'category': None,
            'intensity': None,
            'entry_date': None
        },
        {
            'chat_id': chat_id,
            'impression_text': "Второе",
            'impression_date': "2025-10-24",
            'impression_time': "12:00:00",
            'category': None,
            'intensity': None,
            'entry_date': None
        }
    ]

    for imp in impressions:
        save_impression(conn, imp)

    results = get_user_impressions(conn, chat_id)

    # Проверяем порядок (от новых к старым)
    assert results[0]['impression_text'] == "Третье"  # 15:00
    assert results[1]['impression_text'] == "Второе"  # 12:00
    assert results[2]['impression_text'] == "Первое"  # 10:00
