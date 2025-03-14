"""
Модуль для обработки уведомлений.
Обрабатывает команды для настройки ежедневных уведомлений.
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler,
    JobQueue
)

from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import save_user, get_users_for_notification

# Настройка логгирования
logger = logging.getLogger(__name__)


async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /notify.
    Устанавливает время ежедневных уведомлений.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "Пожалуйста, укажите время для уведомления в формате HH:MM, например: /notify 09:00",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    
    try:
        # Парсинг времени
        time_str = context.args[0]
        hour, minute = map(int, time_str.split(':'))
        
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            await update.message.reply_text(
                "Неверный формат времени. Пожалуйста, используйте HH:MM (от 00:00 до 23:59).",
                reply_markup=MAIN_KEYBOARD
            )
            return ConversationHandler.END
        
        # Сохранение времени уведомления для этого пользователя
        notification_time = f"{hour:02d}:{minute:02d}"
        save_user(chat_id, username, first_name, notification_time=notification_time)
        
        logger.info(f"Пользователь {chat_id} установил уведомления на {notification_time}")
        
        await update.message.reply_text(
            f"Уведомления настроены на {notification_time} каждый день.",
            reply_markup=MAIN_KEYBOARD
        )
    except ValueError:
        await update.message.reply_text(
            "Неверный формат времени. Пожалуйста, используйте HH:MM, например: /notify 09:00",
            reply_markup=MAIN_KEYBOARD
        )
    
    return ConversationHandler.END


async def cancel_notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /cancel_notify.
    Отменяет ежедневные уведомления.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    # Установка времени уведомления в None
    save_user(chat_id, username, first_name, notification_time=None)
    
    logger.info(f"Пользователь {chat_id} отключил уведомления")
    
    await update.message.reply_text(
        "Ежедневные уведомления отключены.",
        reply_markup=MAIN_KEYBOARD
    )
    return ConversationHandler.END


async def send_notifications(context: ContextTypes.DEFAULT_TYPE):
    """
    Проверяет и отправляет уведомления пользователям.
    Вызывается по расписанию.
    
    Args:
        context: контекст бота
    """
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    current_time = f"{current_hour:02d}:{current_minute:02d}"
    
    # Получение пользователей, которым нужно отправить уведомление в текущее время
    users_to_notify = get_users_for_notification(current_time)
    
    for user in users_to_notify:
        chat_id = user['chat_id']
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Напоминание! Пора добавить запись за сегодня. Используйте команду /add для начала.",
                reply_markup=MAIN_KEYBOARD
            )
            logger.info(f"Отправлено уведомление пользователю {chat_id}")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление пользователю {chat_id}: {e}")


def setup_job_queue(job_queue):
    """
    Настраивает планировщик для проверки и отправки уведомлений.

    Args:
        job_queue: планировщик заданий бота (может быть None)
    """
    if job_queue is None:
        logger.warning("JobQueue не настроена. Уведомления не будут отправляться автоматически.")
        return

    # Установка задачи для проверки уведомлений каждую минуту
    job_queue.run_repeating(send_notifications, interval=60, first=10)
    logger.info("Планировщик уведомлений настроен")


def register(application):
    """
    Регистрирует обработчики команд для уведомлений.
    
    Args:
        application: экземпляр приложения бота
    """
    application.add_handler(CommandHandler("notify", notify_command))
    application.add_handler(CommandHandler("cancel_notify", cancel_notify_command))
    
    logger.info("Обработчики уведомлений зарегистрированы")
