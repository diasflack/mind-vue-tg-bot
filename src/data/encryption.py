"""
Модуль для шифрования и расшифровки данных.
Обеспечивает безопасное хранение информации пользователей.
Оптимизированная версия с кешированием ключей и сниженной нагрузкой.
"""

import base64
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
import datetime
import functools
import threading

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import src.config

# Настройка логгирования
logger = logging.getLogger(__name__)

# Количество итераций PBKDF2. Снижено для повышения производительности
# Можно настроить баланс между безопасностью и скоростью
PBKDF2_ITERATIONS = 25000  # Снижено с 100000 для повышения производительности

# Кеш ключей для избежания повторной дорогостоящей деривации ключей
# Структура: {chat_id: {"key": bytes, "timestamp": datetime}}
_key_cache = {}
_key_cache_lock = threading.RLock()  # RLock для потокобезопасного доступа

# Срок хранения ключей в кеше (в секундах)
KEY_CACHE_TTL = 3600  # 1 час


# Класс для конвертации объектов datetime в строки при JSON сериализации
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        # Проверка на pandas Timestamp если pandas импортирован
        try:
            import pandas as pd
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()
        except ImportError:
            pass
        return super(DateTimeEncoder, self).default(obj)


def _cleanup_key_cache():
    """
    Очищает устаревшие ключи из кеша.
    """
    now = datetime.datetime.now()
    expired_keys = []

    with _key_cache_lock:
        for chat_id, cache_data in _key_cache.items():
            if now - cache_data["timestamp"] > datetime.timedelta(seconds=KEY_CACHE_TTL):
                expired_keys.append(chat_id)

        for chat_id in expired_keys:
            del _key_cache[chat_id]

    if expired_keys:
        logger.debug(f"Очищено {len(expired_keys)} устаревших ключей из кеша")


def generate_user_key(chat_id: int) -> bytes:
    """
    Генерирует уникальный и стабильный ключ шифрования для пользователя
    на основе его Telegram ID. Использует кеширование для повышения производительности.

    Args:
        chat_id: ID пользователя в Telegram

    Returns:
        bytes: ключ шифрования
    """
    # Проверка кеша перед генерацией нового ключа
    with _key_cache_lock:
        if chat_id in _key_cache:
            # Обновляем timestamp для используемого ключа
            _key_cache[chat_id]["timestamp"] = datetime.datetime.now()
            logger.debug(f"Ключ для пользователя {chat_id} взят из кеша")
            return _key_cache[chat_id]["key"]

    # Если запускаем генерацию ключа, очищаем старые ключи из кеша
    _cleanup_key_cache()

    if src.config.SECRET_SALT is None or src.config.SYSTEM_SALT is None:
        raise ValueError("Соли шифрования не инициализированы")

    # Создание уникальной базовой строки с использованием chat_id и секретной соли
    base_string = f"telegram-mood-tracker-{chat_id}-{hashlib.sha256(src.config.SECRET_SALT).hexdigest()}"

    # Генерация ключа с использованием PBKDF2 с системной солью
    # Обратите внимание на сниженное количество итераций для повышения производительности
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=src.config.SYSTEM_SALT,
        iterations=PBKDF2_ITERATIONS,  # Уменьшено количество итераций
    )

    # Генерация ключа
    key = base64.urlsafe_b64encode(kdf.derive(base_string.encode()))

    # Сохранение в кеше
    with _key_cache_lock:
        _key_cache[chat_id] = {"key": key, "timestamp": datetime.datetime.now()}
        logger.debug(f"Сгенерирован и кеширован новый ключ для пользователя {chat_id}")

    return key


def encrypt_data(data: Dict[str, Any], chat_id: int) -> str:
    """
    Шифрует данные с использованием ключа на основе Telegram ID пользователя.

    Args:
        data: данные для шифрования
        chat_id: ID пользователя в Telegram

    Returns:
        str: зашифрованные данные в формате base64
    """
    try:
        # Получение ключа пользователя (через кеш)
        key = generate_user_key(chat_id)

        # Создание шифра Fernet с ключом
        cipher = Fernet(key)

        # Преобразование данных в JSON и их шифрование
        data_json = json.dumps(data, cls=DateTimeEncoder).encode('utf-8')
        encrypted_data = cipher.encrypt(data_json)

        # Возврат зашифрованных данных
        return base64.b64encode(encrypted_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка шифрования данных: {e}")
        raise


def decrypt_data(encrypted_data: str, chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Расшифровывает данные с использованием ключа на основе Telegram ID пользователя.

    Args:
        encrypted_data: зашифрованные данные в формате base64
        chat_id: ID пользователя в Telegram

    Returns:
        Dict[str, Any] или None: расшифрованные данные или None в случае ошибки
    """
    try:
        # Получение ключа пользователя (через кеш)
        key = generate_user_key(chat_id)

        # Создание шифра Fernet с ключом
        cipher = Fernet(key)

        # Расшифровка данных
        decrypted_data = cipher.decrypt(base64.b64decode(encrypted_data))

        # Парсинг JSON
        return json.loads(decrypted_data.decode('utf-8'))
    except Exception as e:
        # В случае ошибки расшифровки возвращается None
        logger.error(f"Ошибка расшифровки данных: {e}")
        return None


# Использование более легкого шифрования для sharing данных
# При обмене данными критичнее скорость, чем максимальная защита
def encrypt_for_sharing(data: List[Dict[str, Any]], password: str) -> str:
    """
    Шифрует данные с одноразовым паролем для обмена.
    Использует меньшее количество итераций для повышения производительности.

    Args:
        data: данные для шифрования
        password: пароль для шифрования

    Returns:
        str: зашифрованные данные в формате base64
    """
    if src.config.SYSTEM_SALT is None:
        raise ValueError("Системная соль не инициализирована")

    try:
        # Генерация ключа из пароля с меньшим количеством итераций
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=src.config.SYSTEM_SALT,
            iterations=10000,  # Меньше итераций для шеринга (было 100000)
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))

        # Создание шифра Fernet с ключом
        cipher = Fernet(key)

        # Преобразование данных в JSON и их шифрование
        data_json = json.dumps(data, cls=DateTimeEncoder).encode('utf-8')
        encrypted_data = cipher.encrypt(data_json)

        # Возврат зашифрованных данных
        return base64.b64encode(encrypted_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка шифрования данных для обмена: {e}")
        raise


def decrypt_shared_data(encrypted_data: str, password: str) -> Optional[List[Dict[str, Any]]]:
    """
    Расшифровывает данные, которыми поделились, с использованием одноразового пароля.
    Использует меньшее количество итераций для повышения производительности.

    Args:
        encrypted_data: зашифрованные данные в формате base64
        password: пароль для расшифровки

    Returns:
        List[Dict[str, Any]] или None: расшифрованные данные или None в случае ошибки
    """
    if src.config.SYSTEM_SALT is None:
        raise ValueError("Системная соль не инициализирована")

    try:
        # Генерация ключа из пароля с меньшим количеством итераций
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=src.config.SYSTEM_SALT,
            iterations=10000,  # Меньше итераций для шеринга (было 100000)
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))

        # Создание шифра Fernet с ключом
        cipher = Fernet(key)

        # Расшифровка данных
        decrypted_data = cipher.decrypt(base64.b64decode(encrypted_data))

        # Парсинг JSON
        return json.loads(decrypted_data.decode('utf-8'))
    except Exception as e:
        # В случае ошибки расшифровки возвращается None
        logger.error(f"Ошибка расшифровки общих данных: {e}")
        return None