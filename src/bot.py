"""
Основной модуль бота.
Создает экземпляр приложения и регистрирует все обработчики.
"""

import logging
from telegram.ext import Application

from src.config import TELEGRAM_BOT_TOKEN
from src.data.storage import initialize_files
from src.handlers import (
    basic, entry, stats, notifications, sharing, visualization, import_csv, delete, analytics
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

    # Инициализация файлов данных
    initialize_files()

    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Функция предварительной инициализации (удаление webhook)
    application.post_init = pre_init
    application.post_shutdown = lambda app: logger.info("Бот остановлен")

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
    Запускает бота.
    """
    app = create_application()

    # Запуск бота с очисткой очереди обновлений
    app.run_polling(drop_pending_updates=True)