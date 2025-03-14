"""
Модуль для шифрования и расшифровки данных.
Обеспечивает безопасное хранение информации пользователей.
"""

import base64
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import src.config

# Настройка логгирования
logger = logging.getLogger(__name__)


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


def generate_user_key(chat_id: int) -> bytes:
    """
    Генерирует уникальный и стабильный ключ шифрования для пользователя
    на основе его Telegram ID.

    Args:
        chat_id: ID пользователя в Telegram

    Returns:
        bytes: ключ шифрования
    """
    if src.config.SECRET_SALT is None or src.config.SYSTEM_SALT is None:
        raise ValueError("Соли шифрования не инициализированы")

    # Создание уникальной базовой строки с использованием chat_id и секретной соли
    base_string = f"telegram-mood-tracker-{chat_id}-{hashlib.sha256(src.config.SECRET_SALT).hexdigest()}"

    # Генерация ключа с использованием PBKDF2 с системной солью
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=src.config.SYSTEM_SALT,
        iterations=100000,
    )

    # Генерация и возврат ключа
    return base64.urlsafe_b64encode(kdf.derive(base_string.encode()))


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
        # Получение ключа пользователя
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
        # Получение ключа пользователя
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


def encrypt_for_sharing(data: List[Dict[str, Any]], password: str) -> str:
    """
    Шифрует данные с одноразовым паролем для обмена.

    Args:
        data: данные для шифрования
        password: пароль для шифрования

    Returns:
        str: зашифрованные данные в формате base64
    """
    if src.config.SYSTEM_SALT is None:
        raise ValueError("Системная соль не инициализирована")

    try:
        # Генерация ключа из пароля
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=src.config.SYSTEM_SALT,  # Использование системной соли для простоты
            iterations=100000,
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

    Args:
        encrypted_data: зашифрованные данные в формате base64
        password: пароль для расшифровки

    Returns:
        List[Dict[str, Any]] или None: расшифрованные данные или None в случае ошибки
    """
    if src.config.SYSTEM_SALT is None:
        raise ValueError("Системная соль не инициализирована")

    try:
        # Генерация ключа из пароля
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=src.config.SYSTEM_SALT,  # Использование системной соли для простоты
            iterations=100000,
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