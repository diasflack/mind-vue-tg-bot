"""
Модуль для обработки уведомлений.
Обрабатывает команды для настройки ежедневных уведомлений.
"""

import logging
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler,
    CallbackQueryHandler, MessageHandler, filters
)


from src.utils.conversation_manager import register_conversation, end_conversation, end_all_conversations
from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import save_user, get_users_for_notification, has_entry_for_date
from src.utils.date_helpers import get_today, is_valid_time_format, local_to_utc

from src.config import (
    SELECTING_TIMEZONE, TYPING_TIME
)

# Настройка логгирования
logger = logging.getLogger(__name__)

# Имя обработчика для менеджера диалогов
HANDLER_NAME = "notification_handler"


async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
        Обработчик команды /notify.
        Устанавливает время ежедневных уведомлений.
    """

    # Завершаем все активные диалоги пользователя
    chat_id = update.effective_chat.id
    end_all_conversations(chat_id)

    # Регистрируем новый активный диалог
    register_conversation(chat_id, HANDLER_NAME, SELECTING_TIMEZONE)

    logger.info(f"Пользователь {chat_id} начал процесс настройки нотификаций")

    def get_utc_inline_keyboard():
        buttons = []
        for i in range(-12, 15):
            sign = '+' if i >= 0 else ''
            label = f"UTC{sign}{i}:00"
            buttons.append(InlineKeyboardButton(label, callback_data=f"tz:{label}"))
        rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
        return InlineKeyboardMarkup(rows)

    await update.message.reply_text(
        "Пожалуйста, выберите ваш часовой пояс:",
        reply_markup=get_utc_inline_keyboard()
    )

    return SELECTING_TIMEZONE


async def timezone_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Сохраняем часовой пояс во временное хранилище (context.user_data)
    tz_label = query.data.replace("tz:", "")
    match = re.match(r"UTC([+-]\d+):\d+", tz_label)
    offset_hours = int(match.group(1))
    context.user_data["timezone"] = offset_hours

    await query.edit_message_text(
        f"Вы выбрали часовой пояс {tz_label}.\n\n"
        "Теперь введите время, когда вы хотите получать уведомления (формат HH:MM):"
    )

    return TYPING_TIME


async def time_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    time_str = update.message.text.strip()

    if not is_valid_time_format(time_str):
        await update.message.reply_text(
            "⛔ Неверный формат времени. Пожалуйста, используйте HH:MM (например, 09:30)."
        )
        return TYPING_TIME

    try:
        local_time = datetime.strptime(time_str, "%H:%M").time()
        offset = int(context.user_data.get("timezone"))

        if offset is None:
            await update.message.reply_text("Произошла ошибка: часовой пояс не найден. Начните сначала с /notify.")
            return ConversationHandler.END

        # Преобразуем в UTC
        utc_time_str = local_to_utc(local_time, offset)

        # Сохраняем время в UTC
        save_user(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            notification_time=utc_time_str
        )

        await update.message.reply_text(
            f"✅ Уведомления настроены на {time_str} (UTC{offset:+}) каждый день.\n"
            f"Будут отправляться в {utc_time_str} по UTC.",
            reply_markup=MAIN_KEYBOARD
        )

    except Exception as e:
        await update.message.reply_text("Произошла ошибка при обработке времени.")
        logger.error(f"Не настроить уведомление {chat_id}: {e}")

    end_conversation(chat_id, HANDLER_NAME)
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


async def send_notification_to_user(context: ContextTypes.DEFAULT_TYPE, chat_id: int, custom_message: str = None):
    """
    Отправляет уведомление конкретному пользователю принудительно.

    Args:
        context: контекст бота
        chat_id: ID чата пользователя
        custom_message: пользовательское сообщение (опционально)
    
    Returns:
        bool: True если уведомление отправлено успешно, False - если нет
    """
    try:
        today = get_today()
        
        # Проверка, есть ли уже запись за сегодня
        has_entry_today = has_entry_for_date(chat_id, today)

        # Выбор соответствующего сообщения
        if custom_message:
            message = custom_message
        elif has_entry_today:
            message = (
                "🔔 Принудительное напоминание! У вас уже есть запись за сегодня. "
                "Вы можете обновить её, используя команду /add, или "
                "просмотреть недавние записи с помощью команды /recent."
            )
        else:
            message = (
                "🔔 Принудительное напоминание! Пора добавить запись за сегодня. "
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
        
        logger.info(f"Принудительно отправлено уведомление пользователю {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"Не удалось принудительно отправить уведомление пользователю {chat_id}: {e}")
        return False


async def send_notifications_to_all(context: ContextTypes.DEFAULT_TYPE, custom_message: str = None):
    """
    Отправляет уведомления всем пользователям с настроенными уведомлениями принудительно.

    Args:
        context: контекст бота
        custom_message: пользовательское сообщение (опционально)
    
    Returns:
        dict: статистика отправки {"sent": int, "failed": int, "total": int}
    """
    # Получение всех пользователей с настроенными уведомлениями
    from src.data.storage import get_all_users_with_notifications
    
    users_with_notifications = get_all_users_with_notifications()
    
    sent_count = 0
    failed_count = 0
    total_count = len(users_with_notifications)
    
    for user in users_with_notifications:
        chat_id = user['chat_id']
        success = await send_notification_to_user(context, chat_id, custom_message)
        if success:
            sent_count += 1
        else:
            failed_count += 1
    
    logger.info(f"Принудительная рассылка завершена: {sent_count}/{total_count} успешно, {failed_count} ошибок")
    
    return {
        "sent": sent_count,
        "failed": failed_count, 
        "total": total_count
    }


async def force_notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда для пользователя для получения уведомления прямо сейчас.
    Использование: /force_notify [текст сообщения]

    Args:
        update: объект с информацией о сообщении
        context: контекст бота

    Returns:
        int: состояние ConversationHandler.END
    """
    chat_id = update.effective_chat.id
    
    # Получаем пользовательское сообщение, если оно есть
    custom_message = None
    if context.args:
        custom_message = " ".join(context.args)
    
    # Отправляем уведомление
    success = await send_notification_to_user(context, chat_id, custom_message)
    
    if success:
        await update.message.reply_text(
            "✅ Уведомление отправлено!",
            reply_markup=MAIN_KEYBOARD
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось отправить уведомление. Попробуйте позже.",
            reply_markup=MAIN_KEYBOARD
        )
    
    return ConversationHandler.END


async def admin_notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Административная команда для отправки уведомлений.
    Использование: 
    /admin_notify all [сообщение] - всем пользователям
    /admin_notify user <chat_id> [сообщение] - конкретному пользователю

    Args:
        update: объект с информацией о сообщении
        context: контекст бота

    Returns:
        int: состояние ConversationHandler.END
    """
    chat_id = update.effective_chat.id
    
    # TOD: Добавить проверку прав администратора
    # Для примера считаем, что любой может использовать (в продакшене нужна проверка)
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Использование:\n"
            "/admin_notify all [сообщение] - всем пользователям\n"
            "/admin_notify user <chat_id> [сообщение] - конкретному пользователю",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    
    target = context.args[0].lower()
    
    if target == "all":
        # Отправка всем пользователям
        custom_message = None
        if len(context.args) > 1:
            custom_message = " ".join(context.args[1:])
        
        await update.message.reply_text("🔄 Начинаю рассылку уведомлений всем пользователям...")
        
        stats = await send_notifications_to_all(context, custom_message)
        
        await update.message.reply_text(
            f"📊 Рассылка завершена:\n"
            f"✅ Отправлено: {stats['sent']}\n"
            f"❌ Ошибок: {stats['failed']}\n"
            f"📈 Всего: {stats['total']}",
            reply_markup=MAIN_KEYBOARD
        )
        
    elif target == "user":
        # Отправка конкретному пользователю
        if len(context.args) < 2:
            await update.message.reply_text(
                "Укажите chat_id пользователя: /admin_notify user <chat_id> [сообщение]",
                reply_markup=MAIN_KEYBOARD
            )
            return ConversationHandler.END
        
        try:
            target_chat_id = int(context.args[1])
        except ValueError:
            await update.message.reply_text(
                "Неверный формат chat_id. Используйте числовой ID.",
                reply_markup=MAIN_KEYBOARD
            )
            return ConversationHandler.END
        
        custom_message = None
        if len(context.args) > 2:
            custom_message = " ".join(context.args[2:])
        
        success = await send_notification_to_user(context, target_chat_id, custom_message)
        
        if success:
            await update.message.reply_text(
                f"✅ Уведомление отправлено пользователю {target_chat_id}",
                reply_markup=MAIN_KEYBOARD
            )
        else:
            await update.message.reply_text(
                f"❌ Не удалось отправить уведомление пользователю {target_chat_id}",
                reply_markup=MAIN_KEYBOARD
            )
    else:
        await update.message.reply_text(
            "Неизвестная команда. Используйте 'all' или 'user'.",
            reply_markup=MAIN_KEYBOARD
        )
    
    return ConversationHandler.END


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
        # Начинаем процесс добавления записи
        try:
            # Создаем имитацию объекта Message для обработчика
            # Используем context.bot.send_message для создания новых сообщений
            from telegram import Message, User, Chat
            
            # Получаем данные пользователя и чата
            user = update.effective_user
            chat = update.effective_chat
            
            # Создаем правильный метод reply_text с использованием context.bot
            async def send_message_func(text, reply_markup=None, parse_mode=None):
                return await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            
            # Создаем объект сообщения для имитации команды /add
            fake_message = type('MockMessage', (), {
                'chat': chat,
                'from_user': user,
                'reply_text': send_message_func,  # Используем правильную функцию отправки
                'message_id': query.message.message_id,
                'date': query.message.date
            })()
            
            # Создаем объект Update для имитации команды
            fake_update = type('MockUpdate', (), {
                'message': fake_message,
                'effective_chat': chat,
                'effective_user': user,
                'callback_query': None
            })()
            
            # Очищаем аргументы команды
            context.args = []
            
            # Вызываем обработчик добавления записи
            from src.handlers.entry import start_entry
            await start_entry(fake_update, context)
            
        except Exception as e:
            logger.error(f"Ошибка при запуске добавления записи из уведомления: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="Произошла ошибка при запуске добавления записи. Попробуйте использовать команду /add напрямую.",
                reply_markup=MAIN_KEYBOARD
            )

    elif action == "notify_stats":
        # Загружаем статистику
        try:
            # Создаем имитацию объекта Message для обработчика
            from telegram import Message, User, Chat
            
            # Получаем данные пользователя и чата
            user = update.effective_user
            chat = update.effective_chat
            
            # Создаем правильный метод reply_text с использованием context.bot
            async def send_message_func(text, reply_markup=None, parse_mode=None):
                return await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            
            # Создаем объект сообщения для имитации команды /stats
            fake_message = type('MockMessage', (), {
                'chat': chat,
                'from_user': user,
                'reply_text': send_message_func,  # Используем правильную функцию отправки
                'message_id': query.message.message_id,
                'date': query.message.date
            })()
            
            # Создаем объект Update для имитации команды
            fake_update = type('MockUpdate', (), {
                'message': fake_message,
                'effective_chat': chat,
                'effective_user': user,
                'callback_query': None
            })()
            
            # Вызываем обработчик статистики
            from src.handlers.stats import stats
            await stats(fake_update, context)
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке статистики из уведомления: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="Произошла ошибка при загрузке статистики. Попробуйте использовать команду /stats напрямую.",
                reply_markup=MAIN_KEYBOARD
            )

    elif action == "notify_disable":
        # Отключение уведомлений
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        save_user(chat_id, username, first_name, notification_time=None)

        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Ежедневные уведомления отключены.",
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
    notification_conversation = ConversationHandler(
        entry_points=[CommandHandler("notify", notify_command)],
        states={
            SELECTING_TIMEZONE: [CallbackQueryHandler(timezone_selected, pattern=r"^tz:")],
            TYPING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_entered)],
        },
        fallbacks=[CommandHandler("cancel", cancel_notify_command)],
        name=HANDLER_NAME,
        persistent=False,
    )

    application.add_handler(notification_conversation)

    application.add_handler(CommandHandler("cancel_notify", cancel_notify_command))
    
    # Новые команды для принудительной отправки уведомлений
    application.add_handler(CommandHandler("force_notify", force_notify_command))
    # application.add_handler(CommandHandler("admin_notify", admin_notify_command))

    # Добавляем обработчик для кнопок в уведомлениях
    application.add_handler(CallbackQueryHandler(notification_callback, pattern=r"^notify_"))

    logger.info("Обработчики уведомлений зарегистрированы")
