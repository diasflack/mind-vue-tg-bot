"""
Handlers для управления напоминаниями по опросам (Phase 5.2).

Команды:
- /survey_reminders - просмотр настроенных напоминаний
- /set_survey_reminder <название> <время> - установить напоминание
- /remove_survey_reminder <название> - удалить напоминание
"""

import logging
import re
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.data.storage import _get_db_connection
from src.data.survey_notifications_storage import (
    set_survey_reminder,
    remove_survey_reminder,
    get_survey_reminders
)
from src.data.surveys_storage import get_template_by_name

logger = logging.getLogger(__name__)


def _validate_time_format(time_str: str) -> bool:
    """
    Проверяет формат времени HH:MM.

    Args:
        time_str: строка времени

    Returns:
        bool: True если формат корректный
    """
    pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, time_str))


def _get_user_timezone(conn, chat_id: int) -> int:
    """
    Получает смещение часового пояса пользователя.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя

    Returns:
        int: смещение часового пояса (по умолчанию 0)
    """
    cursor = conn.cursor()
    cursor.execute('SELECT timezone_offset FROM users WHERE chat_id = ?', (chat_id,))
    row = cursor.fetchone()
    return row[0] if row and row[0] is not None else 0


async def survey_reminders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает список настроенных напоминаний - /survey_reminders.
    """
    chat_id = update.effective_chat.id

    try:
        conn = _get_db_connection()
        reminders = get_survey_reminders(conn, chat_id)

        if not reminders:
            await update.message.reply_text(
                "ℹ️ У вас пока нет настроенных напоминаний по опросам.\n\n"
                "Используйте команду:\n"
                "/set_survey_reminder <название> <время>\n\n"
                "Пример:\n"
                "/set_survey_reminder Настроение 09:00"
            )
            return

        # Формируем список напоминаний
        timezone = _get_user_timezone(conn, chat_id)
        message = "📋 Ваши напоминания по опросам:\n\n"

        enabled_count = 0
        for reminder in reminders:
            status = "✅ Включено" if reminder['notification_enabled'] else "❌ Отключено"

            # Конвертируем UTC время в локальное
            if reminder['notification_time']:
                from src.data.survey_notifications_storage import _convert_time_from_utc
                local_time = _convert_time_from_utc(reminder['notification_time'], timezone)
            else:
                local_time = "не установлено"

            message += f"📊 **{reminder['survey_name']}**\n"
            message += f"   Время: {local_time}\n"
            message += f"   Статус: {status}\n\n"

            if reminder['notification_enabled']:
                enabled_count += 1

        message += f"Всего активных: {enabled_count}\n\n"
        message += "Управление:\n"
        message += "• /set_survey_reminder <название> <время>\n"
        message += "• /remove_survey_reminder <название>"

        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Ошибка при получении напоминаний: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при получении списка напоминаний."
        )


async def set_reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Устанавливает напоминание для опроса - /set_survey_reminder <название> <время>.

    Аргументы:
        <название>: название опроса
        <время>: время в формате HH:MM
    """
    chat_id = update.effective_chat.id

    # Проверяем аргументы
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Недостаточно аргументов.\n\n"
            "Использование: /set_survey_reminder <название> <время>\n\n"
            "Примеры:\n"
            "/set_survey_reminder Настроение 09:00\n"
            '/set_survey_reminder "Дневник тревоги" 20:00'
        )
        return

    # Парсим аргументы
    # Последний аргумент - это время, остальные - название опроса
    notification_time = context.args[-1]
    survey_name = ' '.join(context.args[:-1])

    # Валидация времени
    if not _validate_time_format(notification_time):
        await update.message.reply_text(
            "❌ Неверный формат времени.\n\n"
            "Используйте формат HH:MM (например, 09:00 или 20:30)"
        )
        return

    try:
        conn = _get_db_connection()

        # Получаем ID опроса
        template = get_template_by_name(conn, survey_name)
        if not template:
            await update.message.reply_text(
                f"❌ Опрос '{survey_name}' не найден.\n\n"
                f"Посмотреть доступные опросы: /surveys"
            )
            return

        template_id = template['id']

        # Получаем timezone пользователя
        timezone = _get_user_timezone(conn, chat_id)

        # Устанавливаем напоминание
        success = set_survey_reminder(
            conn,
            chat_id=chat_id,
            template_id=template_id,
            notification_time=notification_time,
            timezone_offset=timezone
        )

        if success:
            await update.message.reply_text(
                f"✅ Напоминание установлено!\n\n"
                f"📊 Опрос: {survey_name}\n"
                f"⏰ Время: {notification_time}\n\n"
                f"Вы будете получать напоминание каждый день, "
                f"если опрос еще не заполнен."
            )
            logger.info(f"Пользователь {chat_id} установил напоминание для опроса '{survey_name}' на {notification_time}")
        else:
            await update.message.reply_text(
                "❌ Не удалось установить напоминание.\n"
                "Попробуйте позже."
            )

    except Exception as e:
        logger.error(f"Ошибка при установке напоминания: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при установке напоминания."
        )


async def remove_reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Удаляет напоминание для опроса - /remove_survey_reminder <название>.

    Аргументы:
        <название>: название опроса
    """
    chat_id = update.effective_chat.id

    # Проверяем аргументы
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Недостаточно аргументов.\n\n"
            "Использование: /remove_survey_reminder <название>\n\n"
            "Пример:\n"
            "/remove_survey_reminder Настроение"
        )
        return

    # Парсим название опроса
    survey_name = ' '.join(context.args)

    try:
        conn = _get_db_connection()

        # Получаем ID опроса
        template = get_template_by_name(conn, survey_name)
        if not template:
            await update.message.reply_text(
                f"❌ Опрос '{survey_name}' не найден.\n\n"
                f"Посмотреть доступные опросы: /surveys"
            )
            return

        template_id = template['id']

        # Удаляем напоминание
        success = remove_survey_reminder(conn, chat_id=chat_id, template_id=template_id)

        if success:
            await update.message.reply_text(
                f"✅ Напоминание отключено!\n\n"
                f"📊 Опрос: {survey_name}\n\n"
                f"Вы больше не будете получать напоминания об этом опросе."
            )
            logger.info(f"Пользователь {chat_id} отключил напоминание для опроса '{survey_name}'")
        else:
            await update.message.reply_text(
                f"ℹ️ Напоминание для опроса '{survey_name}' не было настроено.\n\n"
                f"Посмотреть активные напоминания: /survey_reminders"
            )

    except Exception as e:
        logger.error(f"Ошибка при удалении напоминания: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при удалении напоминания."
        )


async def send_survey_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Проверяет и отправляет уведомления об опросах.
    Вызывается автоматически по расписанию (каждую минуту).

    Args:
        context: контекст бота
    """
    from datetime import datetime
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    current_time = f"{current_hour:02d}:{current_minute:02d}"

    try:
        conn = _get_db_connection()

        # Получаем опросы для отправки в текущее время
        from src.data.survey_notifications_storage import (
            get_surveys_for_notification,
            is_survey_filled_today
        )

        surveys = get_surveys_for_notification(conn, current_time)

        for survey in surveys:
            chat_id = survey['chat_id']
            template_id = survey['template_id']
            survey_name = survey['survey_name']

            try:
                # Проверяем заполнен ли опрос сегодня
                is_filled = is_survey_filled_today(conn, chat_id, template_id)

                if is_filled:
                    # Опрос уже заполнен, не отправляем напоминание
                    logger.debug(f"Опрос '{survey_name}' уже заполнен пользователем {chat_id}, пропускаем")
                    continue

                # Формируем сообщение
                message = (
                    f"🔔 Напоминание!\n\n"
                    f"Пора заполнить опрос **{survey_name}**.\n\n"
                    f"Используйте команду /fill_survey {survey_name} для заполнения."
                )

                # Кнопки для быстрого действия
                keyboard = [
                    [InlineKeyboardButton(f"📊 Заполнить '{survey_name}'", callback_data=f"fill_survey:{template_id}")],
                    [InlineKeyboardButton("❌ Отключить напоминание", callback_data=f"disable_reminder:{template_id}")]
                ]

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )

                logger.info(f"Отправлено напоминание об опросе '{survey_name}' пользователю {chat_id}")

            except Exception as e:
                logger.error(f"Не удалось отправить напоминание пользователю {chat_id} об опросе '{survey_name}': {e}")

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений об опросах: {e}")


def setup_job_queue(job_queue) -> None:
    """
    Настраивает планировщик для автоматической отправки уведомлений об опросах.

    Args:
        job_queue: планировщик заданий бота (может быть None)
    """
    if job_queue is None:
        logger.warning("JobQueue не настроена. Уведомления об опросах не будут отправляться автоматически.")
        return

    # Установка задачи для проверки уведомлений каждую минуту
    job_queue.run_repeating(send_survey_notifications, interval=60, first=10)
    logger.info("Планировщик уведомлений об опросах настроен")


def register(application) -> None:
    """Регистрирует handlers для управления напоминаниями."""
    application.add_handler(CommandHandler('survey_reminders', survey_reminders_handler))
    application.add_handler(CommandHandler('set_survey_reminder', set_reminder_handler))
    application.add_handler(CommandHandler('remove_survey_reminder', remove_reminder_handler))

    logger.info("Survey notification handlers зарегистрированы")
