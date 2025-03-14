"""
Модуль для обработки аналитики и выявления паттернов.
Обрабатывает команды для анализа накопленных данных.
"""

import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler
)

from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import get_user_entries
from src.analytics.pattern_detection import format_analytics_summary

# Настройка логгирования
logger = logging.getLogger(__name__)


async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /analytics.
    Выполняет анализ данных пользователя и отображает инсайты.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} запросил аналитику паттернов")
    
    # Отправка промежуточного сообщения
    status_message = await update.message.reply_text(
        "Анализирую данные... Это может занять несколько секунд."
    )
    
    # Получение записей пользователя
    entries = get_user_entries(chat_id)
    
    if not entries:
        # Если нет данных, удаляем статусное сообщение и отвечаем
        try:
            await status_message.delete()
        except Exception as e:
            logger.error(f"Не удалось удалить статусное сообщение: {e}")

        await update.message.reply_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    try:
        # Форматирование результатов аналитики
        analytics_text = format_analytics_summary(entries)

        # Удаление промежуточного сообщения
        try:
            await status_message.delete()
        except Exception as e:
            logger.error(f"Не удалось удалить статусное сообщение: {e}")

        # Отправка результатов аналитики
        await update.message.reply_text(
            analytics_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_KEYBOARD
        )

        # Явно очищаем пользовательские данные после завершения
        if 'analytics_data' in context.user_data:
            del context.user_data['analytics_data']

        logger.info(f"Успешно отправлена аналитика пользователю {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка при анализе данных: {e}")

        try:
            await status_message.delete()
        except Exception:
            pass

        await update.message.reply_text(
            f"Произошла ошибка при анализе данных: {str(e)}",
            reply_markup=MAIN_KEYBOARD
        )

    return ConversationHandler.END


def register(application):
    """
    Регистрирует обработчики команд для аналитики.

    Args:
        application: экземпляр приложения бота
    """
    application.add_handler(CommandHandler("analytics", analytics_command))

    logger.info("Обработчики аналитики зарегистрированы")