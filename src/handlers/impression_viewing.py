"""
Модуль с обработчиками для просмотра впечатлений.
Реализует команды для отображения сохраненных впечатлений.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any
from telegram import Update
from telegram.ext import ContextTypes, Application, CommandHandler

from src.data.storage import _get_db_connection
from src.data.impressions_storage import get_user_impressions

# Настройка логгирования
logger = logging.getLogger(__name__)

# Максимальное количество впечатлений на одно сообщение
MAX_IMPRESSIONS_PER_MESSAGE = 10

# Маппинг категорий на русский язык
CATEGORY_NAMES = {
    'craving': 'Влечение/Тяга',
    'emotion': 'Эмоция',
    'physical': 'Физическое состояние',
    'thoughts': 'Мысли',
    'other': 'Другое'
}


def _format_impression(impression: Dict[str, Any]) -> str:
    """
    Форматирует впечатление для вывода пользователю.

    Args:
        impression: словарь с данными впечатления

    Returns:
        str: отформатированный текст
    """
    # Время без секунд
    time_str = impression['impression_time'][:5]  # HH:MM

    # Базовая информация
    text = f"⏰ {time_str}\n"
    text += f"📝 {impression['impression_text']}\n"

    # Интенсивность (если есть)
    if impression.get('intensity'):
        text += f"🔥 Интенсивность: {impression['intensity']}/10\n"

    # Категория (если есть)
    if impression.get('category'):
        category_ru = CATEGORY_NAMES.get(impression['category'], impression['category'])
        text += f"📂 {category_ru}\n"

    # Теги (если есть)
    if impression.get('tags') and len(impression['tags']) > 0:
        tags_str = " ".join([f"#{tag['tag_name']}" for tag in impression['tags']])
        text += f"🏷️ {tags_str}\n"

    return text


async def show_today_impressions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает впечатления за сегодня.

    Команда: /impressions
    """
    chat_id = update.effective_chat.id

    # Получаем соединение с БД
    conn = _get_db_connection()

    # Получаем сегодняшнюю дату
    today = datetime.now().strftime('%Y-%m-%d')

    # Получаем впечатления за сегодня с тегами
    impressions = get_user_impressions(
        conn,
        chat_id,
        date=today,
        include_tags=True
    )

    if not impressions:
        await update.message.reply_text(
            "📝 Впечатления за сегодня\n\n"
            "У вас пока нет впечатлений за сегодня.\n"
            "Добавьте новое впечатление командой /impression"
        )
        logger.info(f"Пользователь {chat_id} запросил впечатления за сегодня: пусто")
        return

    # Формируем сообщение
    message = f"📝 Впечатления за сегодня ({len(impressions)})\n\n"

    # Добавляем каждое впечатление
    for i, impression in enumerate(impressions, 1):
        message += f"━━━ {i} ━━━\n"
        message += _format_impression(impression)
        message += "\n"

        # Проверяем длину сообщения (ограничение Telegram ~4096 символов)
        if len(message) > 3500 and i < len(impressions):
            # Отправляем текущее сообщение
            await update.message.reply_text(message)
            # Начинаем новое
            message = f"📝 Впечатления за сегодня (продолжение)\n\n"

    # Отправляем последнее сообщение
    await update.message.reply_text(message)

    logger.info(f"Пользователь {chat_id} запросил впечатления за сегодня: {len(impressions)} шт.")


async def show_impressions_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает историю впечатлений.

    Команда: /impressions_history

    Можно добавить фильтры в будущем через аргументы команды.
    """
    chat_id = update.effective_chat.id

    # Получаем соединение с БД
    conn = _get_db_connection()

    # Получаем все впечатления с тегами
    impressions = get_user_impressions(
        conn,
        chat_id,
        include_tags=True
    )

    if not impressions:
        await update.message.reply_text(
            "📚 История впечатлений\n\n"
            "У вас пока нет впечатлений.\n"
            "Добавьте новое впечатление командой /impression"
        )
        logger.info(f"Пользователь {chat_id} запросил историю впечатлений: пусто")
        return

    # Группируем по датам
    impressions_by_date = {}
    for imp in impressions:
        date = imp['impression_date']
        if date not in impressions_by_date:
            impressions_by_date[date] = []
        impressions_by_date[date].append(imp)

    # Формируем сообщение
    message = f"📚 История впечатлений\n"
    message += f"Всего: {len(impressions)} впечатлений за {len(impressions_by_date)} дней\n\n"

    # Сортируем даты (от новых к старым)
    sorted_dates = sorted(impressions_by_date.keys(), reverse=True)

    count = 0
    for date in sorted_dates:
        date_impressions = impressions_by_date[date]

        # Форматируем дату
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        date_formatted = date_obj.strftime('%d.%m.%Y')

        message += f"📅 {date_formatted} ({len(date_impressions)})\n"

        for impression in date_impressions:
            message += _format_impression(impression)
            message += "---\n"

            count += 1

            # Ограничение на количество впечатлений в одном сообщении
            if count >= MAX_IMPRESSIONS_PER_MESSAGE:
                message += f"\n... и еще {len(impressions) - count} впечатлений\n"
                message += "Для просмотра конкретного дня используйте /impressions"
                break

        message += "\n"

        # Проверяем длину сообщения
        if len(message) > 3500:
            await update.message.reply_text(message)
            message = "📚 История впечатлений (продолжение)\n\n"

        if count >= MAX_IMPRESSIONS_PER_MESSAGE:
            break

    # Отправляем последнее сообщение
    if len(message) > 50:  # есть контент
        await update.message.reply_text(message)

    logger.info(f"Пользователь {chat_id} запросил историю впечатлений: {len(impressions)} шт.")


def register(application: Application):
    """
    Регистрирует обработчики просмотра впечатлений в приложении.
    """
    application.add_handler(CommandHandler('impressions', show_today_impressions))
    application.add_handler(CommandHandler('impressions_history', show_impressions_history))
