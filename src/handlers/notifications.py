"""
Модуль для обработки уведомлений.
Обрабатывает команды для настройки ежедневных уведомлений.
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler,
    CallbackQueryHandler
)

from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import save_user, get_users_for_notification, has_entry_for_date
from src.utils.date_helpers import get_today, is_valid_time_format

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

        if not is_valid_time_format(time_str):
            await update.message.reply_text(
                "Неверный формат времени. Пожалуйста, используйте HH:MM (от 00:00 до 23:59).",
                reply_markup=MAIN_KEYBOARD
            )
            return ConversationHandler.END

        # Сохранение времени уведомления для этого пользователя
        save_user(chat_id, username, first_name, notification_time=time_str)

        logger.info(f"Пользователь {chat_id} установил уведомления на {time_str}")

        await update.message.reply_text(
            f"🔔 Уведомления настроены на {time_str} каждый день.\n\n"
            "Я буду напоминать вам о необходимости добавить запись за день. "
            "Вы всегда можете использовать команду /add для внесения нескольких "
            "записей в течение дня (последняя запись заменит предыдущие за этот день).",
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
        "❌ Ежедневные уведомления отключены.",
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
    today = get_today()

    # Получение пользователей, которым нужно отправить уведомление в текущее время
    users_to_notify = get_users_for_notification(current_time)

    for user in users_to_notify:
        chat_id = user['chat_id']
        try:
            # Проверка, есть ли уже запись за сегодня
            has_entry_today = has_entry_for_date(chat_id, today)

            # Выбор соответствующего сообщения
            if has_entry_today:
                message = (
                    "🔔 Напоминание! У вас уже есть запись за сегодня. "
                    "Вы можете обновить её, используя команду /add, или "
                    "просмотреть недавние записи с помощью команды /recent."
                )
            else:
                message = (
                    "🔔 Напоминание! Пора добавить запись за сегодня. "
                    "Используйте команду /add для начала."
                )

            # Кнопки для быстрого доступа к действиям
            keyboard = [
                [InlineKeyboardButton("📝 Добавить/обновить запись", callback_data="notify_add")],
                [InlineKeyboardButton("📊 Посмотреть статистику", callback_data="notify_stats")],
                [InlineKeyboardButton("❌ Отключить уведомления", callback_data="notify_disable")]
            ]

            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            logger.info(f"Отправлено уведомление пользователю {chat_id}")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление пользователю {chat_id}: {e}")


async def notification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает нажатия на кнопки в уведомлениях.

    Args:
        update: объект с информацией о callback query
        context: контекст бота
    """
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    action = query.data

    if action == "notify_add":
        # Отправка команды /add
        await query.message.reply_text(
            "Начинаем добавление новой записи. Для отмены нажмите /cancel."
        )
        # Имитация команды /add
        context.args = []
        from src.handlers.entry import start_entry
        await start_entry(update, context)

    elif action == "notify_stats":
        # Отправка команды /stats
        await query.message.reply_text(
            "Загружаю вашу статистику..."
        )
        # Имитация команды /stats
        from src.handlers.stats import stats
        await stats(update, context)

    elif action == "notify_disable":
        # Отключение уведомлений
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        save_user(chat_id, username, first_name, notification_time=None)

        await query.message.reply_text(
            "❌ Ежедневные уведомления отключены.",
            reply_markup=MAIN_KEYBOARD
        )

        logger.info(f"Пользователь {chat_id} отключил уведомления через кнопку в уведомлении")


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

    # Добавляем обработчик для кнопок в уведомлениях
    application.add_handler(CallbackQueryHandler(notification_callback, pattern=r"^notify_"))

    logger.info("Обработчики уведомлений зарегистрированы")