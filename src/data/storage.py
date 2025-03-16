"""
Модуль для работы с хранилищем данных.
Обеспечивает сохранение и загрузку данных пользователей.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union
import pandas as pd

from src.config import DATA_FOLDER, USERS_FILE
from src.data.encryption import encrypt_data, decrypt_data

# Настройка логгирования
logger = logging.getLogger(__name__)


def initialize_files():
    """
    Инициализирует файлы данных и директории, если они не существуют.
    """
    # Создание папки для данных пользователей, если она не существует
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        logger.info(f"Создана директория для данных пользователей: {DATA_FOLDER}")
    
    # Создание файла пользователей, если он не существует
    if not os.path.exists(USERS_FILE):
        columns = ['chat_id', 'username', 'first_name', 'notification_time']
        pd.DataFrame(columns=columns).to_csv(USERS_FILE, index=False)
        logger.info(f"Создан файл пользователей: {USERS_FILE}")


def get_user_data_file(chat_id: int) -> str:
    """
    Возвращает путь к файлу с данными конкретного пользователя.
    
    Args:
        chat_id: ID пользователя в Telegram
        
    Returns:
        str: путь к файлу данных пользователя
    """
    return os.path.join(DATA_FOLDER, f"user_{chat_id}_data.csv")


def save_data(data: Dict[str, Any], chat_id: int) -> bool:
    """
    Сохраняет зашифрованные данные в файл пользователя.
    Если запись с такой датой уже существует, она будет перезаписана.

    Args:
        data: данные для сохранения
        chat_id: ID пользователя в Telegram

    Returns:
        bool: True, если данные успешно сохранены
    """
    user_file = get_user_data_file(chat_id)
    logger.info(f"Сохранение данных для пользователя {chat_id} в файл {user_file}")

    try:
        # Шифрование данных с использованием Telegram ID пользователя
        encrypted_data = encrypt_data(data, chat_id)
        logger.debug(f"Данные успешно зашифрованы")

        # Преобразование в формат, совместимый с dataframe
        row_data = {
            'date': data['date'],  # Дата не шифруется для возможности фильтрации
            'encrypted_data': encrypted_data
        }

        if os.path.exists(user_file):
            logger.debug(f"Файл {user_file} существует, проверяем наличие записи на эту дату")
            # Чтение существующего файла
            df = pd.read_csv(user_file)

            # Проверка на наличие записи с такой же датой
            if data['date'] in df['date'].values:
                logger.info(f"Найдена существующая запись на дату {data['date']}, она будет перезаписана")
                # Удаление старой записи
                df = df[df['date'] != data['date']]

            # Добавление новой записи
            df = pd.concat([df, pd.DataFrame([row_data])], ignore_index=True)
            df.to_csv(user_file, index=False)
            logger.debug(f"Всего записей в файле после добавления: {len(df)}")
        else:
            logger.debug(f"Файл {user_file} не существует, создаем новый файл")
            # Создание нового DataFrame с текущими данными
            df = pd.DataFrame([row_data])
            df.to_csv(user_file, index=False)
            logger.debug(f"Создан новый файл с 1 записью")

        # Проверка, что файл действительно существует после сохранения
        if os.path.exists(user_file):
            file_size = os.path.getsize(user_file)
            logger.info(f"Данные успешно сохранены для пользователя {chat_id}. Размер файла: {file_size} байт")
            return True
        else:
            logger.error(f"Файл {user_file} не был создан после попытки сохранения")
            return False

    except Exception as e:
        logger.error(f"Ошибка при сохранении данных для пользователя {chat_id}: {e}")
        return False


def get_user_entries(chat_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Получает расшифрованные записи пользователя с фильтрацией по датам.

    Args:
        chat_id: ID пользователя в Telegram
        start_date: начальная дата фильтрации (опционально)
        end_date: конечная дата фильтрации (опционально)

    Returns:
        List[Dict[str, Any]]: список расшифрованных записей
    """
    user_file = get_user_data_file(chat_id)

    if not os.path.exists(user_file):
        logger.info(f"Файл данных для пользователя {chat_id} не найден")
        return []

    try:
        df = pd.read_csv(user_file)

        if len(df) == 0:
            logger.info(f"У пользователя {chat_id} нет записей")
            return []

        # Фильтрация по датам, если указаны
        if start_date and 'date' in df.columns:
            df = df[df['date'] >= start_date]

        if end_date and 'date' in df.columns:
            df = df[df['date'] <= end_date]

        # Расшифровка всех записей
        decrypted_entries = []
        for _, row in df.iterrows():
            try:
                entry = decrypt_data(row['encrypted_data'], chat_id)
                if entry:
                    decrypted_entries.append(entry)
                else:
                    logger.warning(f"Не удалось расшифровать запись для пользователя {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка при расшифровке записи: {e}")

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
    user_file = get_user_data_file(chat_id)

    if not os.path.exists(user_file):
        logger.info(f"Файл данных для пользователя {chat_id} не найден")
        return False

    try:
        # Создаем пустой DataFrame с теми же колонками
        df = pd.read_csv(user_file)
        empty_df = pd.DataFrame(columns=df.columns)
        empty_df.to_csv(user_file, index=False)

        logger.info(f"Все записи для пользователя {chat_id} успешно удалены")
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении данных для пользователя {chat_id}: {e}")
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
    user_file = get_user_data_file(chat_id)

    if not os.path.exists(user_file):
        logger.info(f"Файл данных для пользователя {chat_id} не найден")
        return False

    try:
        df = pd.read_csv(user_file)

        if date not in df['date'].values:
            logger.info(f"Запись на дату {date} для пользователя {chat_id} не найдена")
            return False

        # Удаляем запись с указанной датой
        df = df[df['date'] != date]
        df.to_csv(user_file, index=False)

        logger.info(f"Запись на дату {date} для пользователя {chat_id} успешно удалена")
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении записи на дату {date} для пользователя {chat_id}: {e}")
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
    user_file = get_user_data_file(chat_id)

    if not os.path.exists(user_file):
        return False

    try:
        df = pd.read_csv(user_file)
        return date in df['date'].values
    except Exception as e:
        logger.error(f"Ошибка при проверке записи на дату {date} для пользователя {chat_id}: {e}")
        return False


def save_user(chat_id: int, username: Optional[str], first_name: Optional[str], notification_time: Optional[str] = None) -> bool:
    """
    Сохраняет или обновляет информацию о пользователе.

    Args:
        chat_id: ID пользователя в Telegram
        username: имя пользователя (опционально)
        first_name: имя (опционально)
        notification_time: время уведомления в формате HH:MM (опционально)

    Returns:
        bool: True, если данные успешно сохранены
    """
    try:
        if os.path.exists(USERS_FILE):
            df = pd.read_csv(USERS_FILE)

            # Проверка, существует ли пользователь
            if chat_id in df['chat_id'].values:
                # Обновление существующего пользователя
                df.loc[df['chat_id'] == chat_id, 'username'] = username
                df.loc[df['chat_id'] == chat_id, 'first_name'] = first_name

                if notification_time is not None:
                    df.loc[df['chat_id'] == chat_id, 'notification_time'] = notification_time
            else:
                # Добавление нового пользователя
                new_user = {
                    'chat_id': chat_id,
                    'username': username,
                    'first_name': first_name,
                    'notification_time': notification_time
                }
                df = pd.concat([df, pd.DataFrame([new_user])], ignore_index=True)

            df.to_csv(USERS_FILE, index=False)
        else:
            # Создание нового файла пользователей с этим пользователем
            initialize_files()
            new_user = {
                'chat_id': chat_id,
                'username': username,
                'first_name': first_name,
                'notification_time': notification_time
            }
            pd.DataFrame([new_user]).to_csv(USERS_FILE, index=False)

        logger.info(f"Данные пользователя {chat_id} успешно сохранены")
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
    if not os.path.exists(USERS_FILE):
        logger.warning(f"Файл пользователей {USERS_FILE} не найден")
        return []

    try:
        df = pd.read_csv(USERS_FILE)

        # Фильтрация пользователей, у которых время уведомления совпадает с текущим
        users_to_notify = df[df['notification_time'] == current_time]

        if len(users_to_notify) == 0:
            return []

        # Преобразование в список словарей
        users_list = users_to_notify.to_dict('records')
        logger.info(f"Найдено {len(users_list)} пользователей для уведомления в {current_time}")

        return users_list
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей для уведомления: {e}")
        return []


def get_entry_count_by_day(chat_id: int) -> Dict[str, int]:
    """
    Возвращает словарь с количеством записей по датам.

    Args:
        chat_id: ID пользователя в Telegram

    Returns:
        Dict[str, int]: словарь {дата: количество записей}
    """
    user_file = get_user_data_file(chat_id)

    if not os.path.exists(user_file):
        return {}

    try:
        df = pd.read_csv(user_file)
        date_counts = df['date'].value_counts().to_dict()
        return date_counts
    except Exception as e:
        logger.error(f"Ошибка при получении статистики записей для пользователя {chat_id}: {e}")
        return {}