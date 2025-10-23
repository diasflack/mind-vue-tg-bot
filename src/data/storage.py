"""
Модуль для работы с хранилищем данных.
Обеспечивает сохранение и загрузку данных пользователей.
Оптимизированная версия с использованием SQLite и кешированием.
"""

import os
import logging
import sqlite3
import json
import threading
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
from datetime import datetime, timedelta

from src.config import DATA_FOLDER
from src.data.encryption import encrypt_data, decrypt_data

# Настройка логгирования
logger = logging.getLogger(__name__)

# Пути к файлам БД
DB_FILE = os.path.join(DATA_FOLDER, "mood_tracker.db")

# Размер кеша записей пользователя (максимальное количество наборов данных в кеше)
MAX_CACHE_SIZE = 5

# Время жизни кеша в секундах (30 минут)
CACHE_TTL = 1800

# Кеш для данных пользователей
# Структура: {chat_id: {"data": list_of_entries, "timestamp": datetime, "modified": bool}}
_entries_cache = {}
_cache_lock = threading.RLock()

# Соединение с базой данных (инициализируется при первом использовании)
_db_connection = None
_db_lock = threading.RLock()


def _get_db_connection() -> sqlite3.Connection:
    """
    Получает соединение с базой данных SQLite.
    Инициализирует базу при первом вызове.

    Returns:
        sqlite3.Connection: соединение с базой данных
    """
    global _db_connection, DB_FILE

    with _db_lock:
        if _db_connection is None:
            # Создаем директорию для данных, если её нет
            if not os.path.exists(DATA_FOLDER):
                os.makedirs(DATA_FOLDER)
                logger.info(f"Создана директория для данных: {DATA_FOLDER}")

            # Инициализируем соединение
            _db_connection = sqlite3.connect(DB_FILE, check_same_thread=False)

            # Включаем поддержку внешних ключей
            _db_connection.execute("PRAGMA foreign_keys = ON")

            # Инициализируем таблицы, если их нет
            _initialize_db(_db_connection)

            logger.info(f"Соединение с базой данных инициализировано: {DB_FILE}")

        return _db_connection


def _initialize_db(conn: sqlite3.Connection) -> None:
    """
    Инициализирует таблицы базы данных, если они не существуют.

    Args:
        conn: соединение с базой данных
    """
    # Создание таблицы пользователей
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        notification_time TEXT
    )
    ''')

    # Создание таблицы записей
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

    # Создание индексов для ускорения запросов
    conn.execute('CREATE INDEX IF NOT EXISTS idx_entries_chat_id ON entries(chat_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date)')

    # ИСПРАВЛЕНИЕ: Добавляем индекс на notification_time для оптимизации запросов уведомлений
    # Это ускоряет проверку пользователей для отправки уведомлений (выполняется каждые 60 секунд)
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_users_notification_time
        ON users(notification_time)
        WHERE notification_time IS NOT NULL
    ''')

    # Фиксация изменений
    conn.commit()


def _extract_chat_id_from_csv_filename(filename: str) -> int:
    """
    Извлекает chat_id из имени CSV-файла формата 'user_<chat_id>_data.csv'.

    Args:
        filename: имя CSV-файла

    Returns:
        int: извлеченный chat_id
    """
    return int(filename.split('_')[1])


def _is_user_already_migrated(cursor: sqlite3.Cursor, chat_id: int) -> bool:
    """
    Проверяет, были ли уже мигрированы записи пользователя.

    Args:
        cursor: курсор базы данных
        chat_id: ID чата пользователя

    Returns:
        bool: True если пользователь уже мигрирован, False иначе
    """
    cursor.execute("SELECT COUNT(*) FROM entries WHERE chat_id = ?", (chat_id,))
    return cursor.fetchone()[0] > 0


def _ensure_migrated_user_exists(cursor: sqlite3.Cursor, chat_id: int) -> None:
    """
    Создает пользователя для миграции, если он не существует.

    Args:
        cursor: курсор базы данных
        chat_id: ID чата пользователя
    """
    cursor.execute(
        "INSERT OR IGNORE INTO users (chat_id, username, first_name) VALUES (?, ?, ?)",
        (chat_id, f"migrated_user_{chat_id}", f"Migrated User {chat_id}")
    )


def _migrate_single_csv_file(csv_file: str, cursor: sqlite3.Cursor, conn: sqlite3.Connection) -> None:
    """
    Мигрирует один CSV-файл в базу данных.

    Args:
        csv_file: имя CSV-файла
        cursor: курсор базы данных
        conn: соединение с базой данных
    """
    # Извлечение chat_id из имени файла
    chat_id = _extract_chat_id_from_csv_filename(csv_file)

    # Проверка, есть ли уже записи для этого пользователя в БД
    if _is_user_already_migrated(cursor, chat_id):
        logger.info(f"Записи пользователя {chat_id} уже мигрированы в SQLite")
        return

    # Создаем пользователя, если его нет (для foreign key constraint)
    _ensure_migrated_user_exists(cursor, chat_id)

    # Чтение CSV-файла
    csv_path = os.path.join(DATA_FOLDER, csv_file)
    df = pd.read_csv(csv_path)

    # Подготовка данных для batch insert (значительно быстрее для больших CSV)
    entries_data = [
        (chat_id, row['date'], row['encrypted_data'])
        for _, row in df.iterrows()
    ]

    # Batch insert всех записей одним запросом (executemany)
    cursor.executemany(
        "INSERT OR IGNORE INTO entries (chat_id, date, encrypted_data) VALUES (?, ?, ?)",
        entries_data
    )

    conn.commit()
    logger.info(f"Мигрировано {len(df)} записей пользователя {chat_id} из CSV в SQLite (batch operation)")

    # Создаем резервную копию CSV-файла перед миграцией
    backup_path = csv_path + '.bak'
    os.rename(csv_path, backup_path)
    logger.info(f"Создана резервная копия CSV-файла: {backup_path}")


def _migrate_csv_to_sqlite() -> None:
    """
    Мигрирует данные из CSV-файлов в SQLite.
    Выполняется при первом запуске после обновления.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Получение списка CSV-файлов пользователей
    csv_files = [f for f in os.listdir(DATA_FOLDER) if f.startswith('user_') and f.endswith('_data.csv')]

    for csv_file in csv_files:
        try:
            _migrate_single_csv_file(csv_file, cursor, conn)
        except Exception as e:
            logger.error(f"Ошибка при миграции CSV-файла {csv_file}: {e}")
            conn.rollback()

    logger.info("Миграция данных из CSV в SQLite завершена")


def initialize_storage():
    """
    Инициализирует хранилище данных.
    Создает базу данных, если она не существует, и мигрирует данные из CSV.
    """
    # Инициализация базы данных
    conn = _get_db_connection()

    # Миграция данных из CSV, если нужно
    _migrate_csv_to_sqlite()

    logger.info("Хранилище данных инициализировано")


def _cleanup_cache():
    """
    Очищает устаревшие данные из кеша.
    """
    now = datetime.now()
    expired_keys = []

    with _cache_lock:
        # Находим устаревшие ключи
        for chat_id, cache_data in _entries_cache.items():
            if now - cache_data["timestamp"] > timedelta(seconds=CACHE_TTL):
                # Если данные были изменены, сохраняем их перед удалением
                if cache_data.get("modified", False):
                    _flush_cache_to_db(chat_id)
                expired_keys.append(chat_id)

        # Удаляем устаревшие ключи
        for chat_id in expired_keys:
            del _entries_cache[chat_id]

    if expired_keys:
        logger.debug(f"Очищено {len(expired_keys)} устаревших наборов данных из кеша")


def _flush_cache_to_db(chat_id: int) -> None:
    """
    Сохраняет кешированные данные в базу данных.

    Args:
        chat_id: ID пользователя в Telegram
    """
    with _cache_lock:
        if chat_id not in _entries_cache or not _entries_cache[chat_id].get("modified", False):
            return

        entries = _entries_cache[chat_id]["data"]

        # Нет изменений для сохранения
        if not entries:
            _entries_cache[chat_id]["modified"] = False
            return

        conn = _get_db_connection()
        cursor = conn.cursor()

        try:
            # Начинаем транзакцию
            cursor.execute("BEGIN")

            # Обновляем каждую запись
            for entry in entries:
                date = entry['date']

                # Шифрование данных
                encrypted_data = encrypt_data(entry, chat_id)

                # Обновление или вставка записи (UPSERT)
                cursor.execute("""
                    INSERT INTO entries (chat_id, date, encrypted_data)
                    VALUES (?, ?, ?)
                    ON CONFLICT(chat_id, date)
                    DO UPDATE SET encrypted_data = excluded.encrypted_data
                """, (chat_id, date, encrypted_data))

            # Фиксируем транзакцию
            conn.commit()

            # Обновляем статус кеша
            _entries_cache[chat_id]["modified"] = False
            logger.debug(f"Данные пользователя {chat_id} сохранены в БД")

        except Exception as e:
            # Откатываем транзакцию в случае ошибки
            conn.rollback()
            logger.error(f"Ошибка при сохранении данных пользователя {chat_id}: {e}")


def save_data(data: Dict[str, Any], chat_id: int) -> bool:
    """
    Сохраняет данные в кеш и периодически сохраняет их в базу данных.
    Если запись с такой датой уже существует, она будет перезаписана.

    Args:
        data: данные для сохранения
        chat_id: ID пользователя в Telegram

    Returns:
        bool: True, если данные успешно сохранены
    """
    logger.debug(f"Сохранение данных для пользователя {chat_id}")

    try:
        # Обновление кеша
        with _cache_lock:
            # Чистим устаревшие кеши перед добавлением новых данных
            _cleanup_cache()

            if chat_id in _entries_cache:
                entries = _entries_cache[chat_id]["data"]

                # Проверяем наличие записи с той же датой и обновляем её
                for i, entry in enumerate(entries):
                    if entry['date'] == data['date']:
                        entries[i] = data
                        break
                else:
                    # Если записи с такой датой нет, добавляем новую
                    entries.append(data)

                # Помечаем кеш как измененный
                _entries_cache[chat_id]["modified"] = True
                # Обновляем временную метку
                _entries_cache[chat_id]["timestamp"] = datetime.now()
            else:
                # Создаем новый кеш для пользователя
                _entries_cache[chat_id] = {
                    "data": [data],
                    "timestamp": datetime.now(),
                    "modified": True
                }

            # Если размер кеша превышает лимит, сохраняем данные в БД
            if len(_entries_cache) > MAX_CACHE_SIZE:
                _flush_cache_to_db(chat_id)

        # Обеспечиваем наличие пользователя в базе данных
        ensure_user_exists(chat_id)

        # Немедленное сохранение в БД для важных данных
        _flush_cache_to_db(chat_id)

        logger.info(f"Данные успешно сохранены для пользователя {chat_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка при сохранении данных для пользователя {chat_id}: {e}")
        return False


def get_user_entries(chat_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Получает расшифрованные записи пользователя с фильтрацией по датам.
    Использует кеширование для повышения производительности.

    Args:
        chat_id: ID пользователя в Telegram
        start_date: начальная дата фильтрации (опционально)
        end_date: конечная дата фильтрации (опционально)

    Returns:
        List[Dict[str, Any]]: список расшифрованных записей
    """
    logger.debug(f"Получение записей пользователя {chat_id}")

    # Проверяем наличие данных в кеше
    with _cache_lock:
        if chat_id in _entries_cache:
            # Данные есть в кеше
            cached_entries = _entries_cache[chat_id]["data"]

            # Если кеш был изменен, но данные не фильтруются, мы можем вернуть кеш
            if not start_date and not end_date:
                # Обновляем временную метку
                _entries_cache[chat_id]["timestamp"] = datetime.now()
                logger.debug(f"Возвращено {len(cached_entries)} записей из кеша для пользователя {chat_id}")
                return cached_entries.copy()

    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Формирование запроса с учетом фильтров
        query = "SELECT date, encrypted_data FROM entries WHERE chat_id = ?"
        params = [chat_id]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        # Добавляем сортировку по дате
        query += " ORDER BY date DESC"

        # Выполнение запроса
        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Расшифровка записей
        decrypted_entries = []
        for date, encrypted_data in rows:
            try:
                entry = decrypt_data(encrypted_data, chat_id)
                if entry:
                    decrypted_entries.append(entry)
                else:
                    logger.warning(f"Не удалось расшифровать запись за {date} для пользователя {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка при расшифровке записи за {date}: {e}")

        # Если не было фильтрации, обновляем кеш
        if not start_date and not end_date:
            with _cache_lock:
                _entries_cache[chat_id] = {
                    "data": decrypted_entries.copy(),
                    "timestamp": datetime.now(),
                    "modified": False
                }

        logger.info(f"Успешно получено {len(decrypted_entries)} записей для пользователя {chat_id}")
        return decrypted_entries

    except Exception as e:
        logger.error(f"Ошибка при получении записей для пользователя {chat_id}: {e}")
        return []


def delete_all_entries(chat_id: int) -> bool:
    """
    Удаляет все записи пользователя.

    Args:
        chat_id: ID пользователя в Telegram

    Returns:
        bool: True, если данные успешно удалены
    """
    logger.info(f"Удаление всех записей пользователя {chat_id}")

    try:
        # Очистка кеша пользователя
        with _cache_lock:
            if chat_id in _entries_cache:
                del _entries_cache[chat_id]

        # Удаление записей из БД
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM entries WHERE chat_id = ?", (chat_id,))
        conn.commit()

        rows_deleted = cursor.rowcount
        logger.info(f"Удалено {rows_deleted} записей пользователя {chat_id}")

        return True

    except Exception as e:
        logger.error(f"Ошибка при удалении записей пользователя {chat_id}: {e}")
        return False


def delete_entry_by_date(chat_id: int, date: str) -> bool:
    """
    Удаляет запись пользователя за указанную дату.

    Args:
        chat_id: ID пользователя в Telegram
        date: дата в формате YYYY-MM-DD

    Returns:
        bool: True, если запись успешно удалена
    """
    logger.info(f"Удаление записи за {date} пользователя {chat_id}")

    try:
        # Обновление кеша (если есть)
        with _cache_lock:
            if chat_id in _entries_cache:
                entries = _entries_cache[chat_id]["data"]
                # Удаляем запись из кеша
                _entries_cache[chat_id]["data"] = [e for e in entries if e['date'] != date]
                _entries_cache[chat_id]["modified"] = True
                _entries_cache[chat_id]["timestamp"] = datetime.now()

        # Удаление записи из БД
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM entries WHERE chat_id = ? AND date = ?", (chat_id, date))
        conn.commit()

        success = cursor.rowcount > 0

        if success:
            logger.info(f"Запись за {date} пользователя {chat_id} успешно удалена")
        else:
            logger.info(f"Запись за {date} пользователя {chat_id} не найдена")

        return success

    except Exception as e:
        logger.error(f"Ошибка при удалении записи за {date} пользователя {chat_id}: {e}")
        return False


def has_entry_for_date(chat_id: int, date: str) -> bool:
    """
    Проверяет, существует ли запись для указанной даты.

    Args:
        chat_id: ID пользователя в Telegram
        date: дата в формате YYYY-MM-DD

    Returns:
        bool: True, если запись существует
    """
    # Проверка в кеше
    with _cache_lock:
        if chat_id in _entries_cache:
            for entry in _entries_cache[chat_id]["data"]:
                if entry['date'] == date:
                    return True

    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM entries WHERE chat_id = ? AND date = ? LIMIT 1", (chat_id, date))
        result = cursor.fetchone() is not None

        return result

    except Exception as e:
        logger.error(f"Ошибка при проверке записи за {date} пользователя {chat_id}: {e}")
        return False


def ensure_user_exists(chat_id: int, username: Optional[str] = None, first_name: Optional[str] = None) -> None:
    """
    Убеждается, что пользователь существует в базе данных.
    Если нет - создаёт запись пользователя.

    Args:
        chat_id: ID пользователя в Telegram
        username: имя пользователя (опционально)
        first_name: имя (опционально)
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Проверяем наличие пользователя
    cursor.execute("SELECT 1 FROM users WHERE chat_id = ?", (chat_id,))
    if cursor.fetchone() is None:
        # Добавляем пользователя
        cursor.execute(
            "INSERT INTO users (chat_id, username, first_name) VALUES (?, ?, ?)",
            (chat_id, username, first_name)
        )
        conn.commit()
        logger.info(f"Создан новый пользователь с ID {chat_id}")
    elif username is not None or first_name is not None:
        # Обновляем данные существующего пользователя
        update_fields = []
        params = []

        if username is not None:
            update_fields.append("username = ?")
            params.append(username)

        if first_name is not None:
            update_fields.append("first_name = ?")
            params.append(first_name)

        if update_fields:
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE chat_id = ?"
            params.append(chat_id)

            cursor.execute(query, params)
            conn.commit()
            logger.debug(f"Обновлены данные пользователя {chat_id}")


def save_user(chat_id: int, username: Optional[str], first_name: Optional[str], notification_time: Optional[str] = None) -> bool:
    """
    Сохраняет или обновляет информацию о пользователе.

    ВАЖНО: Если notification_time=None, поле будет установлено в NULL (отключение уведомлений).

    Args:
        chat_id: ID пользователя в Telegram
        username: имя пользователя (опционально)
        first_name: имя (опционально)
        notification_time: время уведомления в формате HH:MM (опционально, None для отключения)

    Returns:
        bool: True, если данные успешно сохранены
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Проверяем, существует ли пользователь
        cursor.execute("SELECT 1 FROM users WHERE chat_id = ?", (chat_id,))
        if cursor.fetchone() is None:
            # Добавляем нового пользователя
            cursor.execute(
                "INSERT INTO users (chat_id, username, first_name, notification_time) VALUES (?, ?, ?, ?)",
                (chat_id, username, first_name, notification_time)
            )
        else:
            # ИСПРАВЛЕНИЕ: Всегда обновляем notification_time, даже если она None
            # Это позволяет корректно отключать уведомления
            cursor.execute(
                "UPDATE users SET username = ?, first_name = ?, notification_time = ? WHERE chat_id = ?",
                (username, first_name, notification_time, chat_id)
            )

        conn.commit()
        logger.info(f"Данные пользователя {chat_id} успешно сохранены (notification_time={notification_time})")

        return True

    except Exception as e:
        logger.error(f"Ошибка при сохранении данных пользователя {chat_id}: {e}")
        return False


def get_users_for_notification(current_time: str) -> List[Dict[str, Any]]:
    """
    Получает список пользователей, которым нужно отправить уведомление
    в указанное время.

    Args:
        current_time: текущее время в формате HH:MM

    Returns:
        List[Dict[str, Any]]: список пользователей для уведомления
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT chat_id, username, first_name, notification_time FROM users WHERE notification_time = ?",
            (current_time,)
        )

        # Преобразование в список словарей
        users = []
        for row in cursor.fetchall():
            users.append({
                'chat_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'notification_time': row[3]
            })

        logger.info(f"Найдено {len(users)} пользователей для уведомления в {current_time}")
        return users

    except Exception as e:
        logger.error(f"Ошибка при получении пользователей для уведомления: {e}")
        return []


def get_all_users_with_notifications() -> List[Dict[str, Any]]:
    """
    Получает список всех пользователей, у которых настроены уведомления.

    Returns:
        List[Dict[str, Any]]: список всех пользователей с настроенными уведомлениями
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT chat_id, username, first_name, notification_time FROM users WHERE notification_time IS NOT NULL"
        )

        # Преобразование в список словарей
        users = []
        for row in cursor.fetchall():
            users.append({
                'chat_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'notification_time': row[3]
            })

        logger.info(f"Найдено {len(users)} пользователей с настроенными уведомлениями")
        return users

    except Exception as e:
        logger.error(f"Ошибка при получении пользователей с уведомлениями: {e}")
        return []



def get_entry_count_by_day(chat_id: int) -> Dict[str, int]:
    """
    Возвращает словарь с количеством записей по датам.

    Args:
        chat_id: ID пользователя в Telegram

    Returns:
        Dict[str, int]: словарь {дата: количество записей}
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT date, COUNT(*) FROM entries WHERE chat_id = ? GROUP BY date",
            (chat_id,)
        )

        date_counts = {row[0]: row[1] for row in cursor.fetchall()}
        return date_counts

    except Exception as e:
        logger.error(f"Ошибка при получении статистики записей для пользователя {chat_id}: {e}")
        return {}


def flush_all_caches():
    """
    Сохраняет все кешированные данные в БД.
    Полезно перед выключением бота.
    """
    with _cache_lock:
        for chat_id in list(_entries_cache.keys()):
            if _entries_cache[chat_id].get("modified", False):
                _flush_cache_to_db(chat_id)

    logger.info("Все кеши сохранены в БД")


def close_db_connection():
    """
    Закрывает соединение с базой данных.
    Полезно перед выключением бота.
    """
    global _db_connection

    # Сначала сохраняем все кеши
    flush_all_caches()

    with _db_lock:
        if _db_connection is not None:
            _db_connection.close()
            _db_connection = None
            logger.info("Соединение с базой данных закрыто")