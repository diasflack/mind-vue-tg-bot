#!/usr/bin/env python
"""
Telegram Mood Tracker Bot - точка входа.
Запускает основное приложение Telegram-бота для отслеживания настроения.
Оптимизированная версия с поддержкой многопроцессорности.
"""

import logging
import signal
import sys
from src.bot import run
from src.config import initialize_environment
from src.data.storage import initialize_storage, close_db_connection, flush_all_caches
from src.multiprocessing import initialize_process_pool, shutdown_process_pool

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    """
    Обработчик сигналов для корректного завершения работы.
    """
    logger.info("Получен сигнал завершения, выполняем корректное завершение...")

    # Сохранение кешей в базу данных
    flush_all_caches()

    # Закрытие соединения с базой данных
    close_db_connection()

    # Завершение пула процессов
    shutdown_process_pool()

    logger.info("Бот корректно завершил работу")
    sys.exit(0)


def main():
    """Основная функция запуска бота."""
    try:
        # Настройка обработчика сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Инициализация окружения (проверка/создание переменных окружения)
        logger.info("Инициализация окружения...")
        secret_salt, system_salt = initialize_environment()

        # Обновление глобальных переменных в модуле config
        import src.config as config
        config.SECRET_SALT = secret_salt
        config.SYSTEM_SALT = system_salt

        logger.info("Окружение успешно инициализировано")

        # Инициализация хранилища данных
        logger.info("Инициализация хранилища данных...")
        initialize_storage()

        # Инициализация пула процессов
        logger.info("Инициализация пула процессов...")
        initialize_process_pool()

        # Запуск бота
        logger.info("Запуск бота для отслеживания настроения...")
        run()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()