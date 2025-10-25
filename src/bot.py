"""
Основной модуль бота.
Создает экземпляр приложения и регистрирует все обработчики.
Оптимизированная версия с улучшенной обработкой событий.
"""

import logging
import asyncio
from telegram.ext import Application

from src.config import TELEGRAM_BOT_TOKEN
from src.data.storage import initialize_storage
from src.handlers import (
    basic, entry, stats, notifications, sharing, visualization, import_csv, delete, analytics,
    impression_handler, impression_viewing, survey_handlers, survey_viewing, survey_create, survey_questions, survey_edit
)

# Настройка логгирования
logger = logging.getLogger(__name__)


async def pre_init(application):
    """
    Выполняется перед инициализацией приложения.
    Удаляет webhook и очищает очередь обновлений.
    """
    try:
        # Удаление webhook и очистка очереди обновлений
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удален, очередь обновлений очищена")
    except Exception as e:
        logger.error(f"Ошибка при удалении webhook: {e}")


async def post_shutdown(application):
    """
    Выполняется после завершения работы приложения.
    Корректно закрывает соединения и сохраняет данные.
    """
    from src.data.storage import flush_all_caches, close_db_connection
    from src.multiprocessing import shutdown_process_pool

    # Сохранение всех кешей
    flush_all_caches()

    # Закрытие соединения с БД
    close_db_connection()

    # Завершение пула процессов
    shutdown_process_pool()

    logger.info("Бот корректно завершил работу")


def create_application():
    """
    Создает и настраивает экземпляр приложения.
    Регистрирует все обработчики и настраивает планировщик задач.

    Returns:
        Application: настроенное приложение бота
    """
    # Проверка наличия токена
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("Токен бота не найден. Установите TELEGRAM_BOT_TOKEN в .env файле.")

    # Инициализация хранилища данных
    initialize_storage()

    # Создание приложения с оптимизированными настройками
    # Используем только параметры, совместимые с текущей версией библиотеки
    builder = Application.builder().token(TELEGRAM_BOT_TOKEN)

    # Добавляем дополнительные параметры только если они поддерживаются
    try:
        builder = builder.concurrent_updates(True)
    except Exception as e:
        logger.warning(f"concurrent_updates не поддерживается: {e}")

    try:
        builder = builder.connect_timeout(10.0)
    except Exception as e:
        logger.warning(f"connect_timeout не поддерживается: {e}")

    try:
        builder = builder.read_timeout(7.0)
    except Exception as e:
        logger.warning(f"read_timeout не поддерживается: {e}")

    try:
        builder = builder.write_timeout(7.0)
    except Exception as e:
        logger.warning(f"write_timeout не поддерживается: {e}")

    # Создаем приложение
    application = builder.build()

    # Функция предварительной инициализации (удаление webhook)
    application.post_init = pre_init
    # Функция после завершения работы
    application.post_shutdown = post_shutdown

    # Регистрация обработчиков
    basic.register(application)
    entry.register(application)
    stats.register(application)
    notifications.register(application)
    sharing.register(application)
    visualization.register(application)
    import_csv.register(application)
    delete.register(application)
    analytics.register(application)
    impression_handler.register(application)
    impression_viewing.register(application)
    survey_handlers.register(application)
    survey_viewing.register(application)
    survey_create.register(application)
    survey_questions.register(application)
    survey_edit.register(application)

    # Настройка планировщика для уведомлений
    if application.job_queue is None:
        logger.warning(
            "JobQueue не доступна. Для включения автоматических уведомлений установите "
            "python-telegram-bot[job-queue]. Уведомления не будут отправляться автоматически."
        )
    else:
        notifications.setup_job_queue(application.job_queue)

    logger.info("Приложение успешно настроено и готово к запуску")
    return application


def run():
    """
    Запускает бота с оптимизированными настройками.
    """
    app = create_application()

    # Запуск бота с очисткой очереди обновлений
    # Используем только совместимые параметры
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"]  # Ограничиваем типы обновлений
    )