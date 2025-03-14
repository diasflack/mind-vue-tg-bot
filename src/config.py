"""
Конфигурационный модуль для бота.
Управляет загрузкой переменных окружения, созданием директорий,
инициализацией ключей шифрования.
"""

import os
import base64
import secrets
import logging
from pathlib import Path
from dotenv import load_dotenv

# Настройка логгирования
logger = logging.getLogger(__name__)

# Загрузка переменных окружения из .env
load_dotenv()

# Основные пути к файлам и папкам
DATA_FOLDER = os.getenv('DATA_FOLDER', 'user_data')
USERS_FILE = os.getenv('USERS_FILE', 'users.csv')

# Токен бота
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Константы для диалоговых состояний
# Определение состояний диалогов для ConversationHandler
(
    MOOD, SLEEP, COMMENT, BALANCE,
    MANIA, DEPRESSION, ANXIETY,
    IRRITABILITY, PRODUCTIVITY, SOCIABILITY,
    SEND_DIARY_USER_ID, SEND_DIARY_START_DATE,
    SHARE_PASSWORD_SETUP, SHARE_PASSWORD_ENTRY,
    IMPORT_CSV_FILE, IMPORT_CSV_CONFIRM,
    DELETE_ENTRY_CONFIRM, DELETE_ENTRY_DATE
) = range(18)


def initialize_environment():
    """
    Инициализирует переменные окружения и ключи шифрования.
    Создает .env файл, если он не существует или не содержит нужных переменных.
    Возвращает кортеж из соли для секретов и системной соли.
    """
    env_file = Path('.env')

    # Проверка наличия токена бота
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен бота не найден. Установите TELEGRAM_BOT_TOKEN в .env файле.")
        raise ValueError("Токен бота не найден. Установите TELEGRAM_BOT_TOKEN в .env файле.")

    # Генерация секретных солей если они не существуют в .env файле
    env_vars = {}
    env_vars['TELEGRAM_BOT_TOKEN'] = TELEGRAM_BOT_TOKEN

    if not os.getenv('SECRET_SALT'):
        # Генерация новой секретной соли
        env_vars['SECRET_SALT'] = base64.b64encode(secrets.token_bytes(16)).decode('utf-8')
        logger.info("Сгенерирована новая SECRET_SALT и сохранена в .env")
    else:
        env_vars['SECRET_SALT'] = os.getenv('SECRET_SALT')

    if not os.getenv('SYSTEM_SALT'):
        # Генерация новой системной соли
        env_vars['SYSTEM_SALT'] = base64.b64encode(secrets.token_bytes(16)).decode('utf-8')
        logger.info("Сгенерирована новая SYSTEM_SALT и сохранена в .env")
    else:
        env_vars['SYSTEM_SALT'] = os.getenv('SYSTEM_SALT')

    # Обновление .env файла с новыми значениями
    if not os.getenv('SECRET_SALT') or not os.getenv('SYSTEM_SALT'):
        with open(env_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

        # Перезагрузка переменных окружения
        load_dotenv(override=True)

    # Получение солей из переменных окружения
    secret_salt = base64.b64decode(os.getenv('SECRET_SALT'))
    system_salt = base64.b64decode(os.getenv('SYSTEM_SALT'))

    # Создание директорий для данных если они не существуют
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        logger.info(f"Создана директория для данных: {DATA_FOLDER}")

    return secret_salt, system_salt


# Соли для шифрования - будут инициализированы позже
SECRET_SALT = None
SYSTEM_SALT = None