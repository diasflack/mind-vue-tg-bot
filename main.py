#!/usr/bin/env python
"""
Telegram Mood Tracker Bot - точка входа.
Запускает основное приложение Telegram-бота для отслеживания настроения.
"""

import logging
from src.bot import create_application
from src.config import initialize_environment

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция запуска бота."""
    try:
        # Инициализация окружения (проверка/создание переменных окружения)
        logger.info("Инициализация окружения...")
        secret_salt, system_salt = initialize_environment()

        # Обновление глобальных переменных в модуле config
        import src.config as config
        config.SECRET_SALT = secret_salt
        config.SYSTEM_SALT = system_salt

        logger.info("Окружение успешно инициализировано")

        # Создание и запуск приложения
        logger.info("Запуск бота для отслеживания настроения...")
        app = create_application()
        app.run_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    main()
