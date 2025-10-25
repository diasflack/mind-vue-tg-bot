"""
Handlers для привязки впечатлений к записям дня (Phase 5.1).

Команды:
- /link_impression <id> <дата> - привязать впечатление к записи
- /unlink_impression <id> - отвязать впечатление
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.data.storage import _get_db_connection
from src.data.impressions_storage import (
    link_impression_to_entry,
    unlink_impression,
    get_impression_by_id
)

logger = logging.getLogger(__name__)


async def link_impression_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Привязывает впечатление к записи дня - /link_impression <id> <дата>.

    Args:
        <id>: ID впечатления
        <дата>: дата записи в формате YYYY-MM-DD
    """
    chat_id = update.effective_chat.id

    # Проверяем аргументы
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Недостаточно аргументов.\n\n"
            "Использование: /link_impression <id> <дата>\n\n"
            "Пример: /link_impression 5 2025-10-25"
        )
        return

    # Парсим ID
    try:
        impression_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Невалидный ID впечатления.\n\n"
            "ID должен быть числом."
        )
        return

    # Парсим дату
    entry_date = context.args[1]
    try:
        datetime.strptime(entry_date, '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text(
            "❌ Невалидная дата.\n\n"
            "Формат даты: YYYY-MM-DD (например, 2025-10-25)"
        )
        return

    try:
        conn = _get_db_connection()

        # Проверяем существование впечатления
        impression = get_impression_by_id(conn, impression_id, chat_id)
        if not impression:
            await update.message.reply_text(
                f"❌ Впечатление с ID {impression_id} не найдено.\n\n"
                f"Посмотреть ваши впечатления: /impressions"
            )
            return

        # Привязываем
        success = link_impression_to_entry(conn, impression_id, chat_id, entry_date)

        if success:
            await update.message.reply_text(
                f"✅ Впечатление привязано к записи от {entry_date}.\n\n"
                f"💭 _{impression['text']}_\n\n"
                f"Посмотреть запись: /recent"
            )
        else:
            await update.message.reply_text(
                f"❌ Не удалось привязать впечатление.\n\n"
                f"Возможно, запись от {entry_date} не существует.\n\n"
                f"Посмотреть записи: /recent"
            )

    except Exception as e:
        logger.error(f"Ошибка при привязке впечатления {impression_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при привязке впечатления.\n"
            "Попробуйте позже."
        )


async def unlink_impression_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отвязывает впечатление от записи дня - /unlink_impression <id>.

    Args:
        <id>: ID впечатления
    """
    chat_id = update.effective_chat.id

    # Проверяем аргументы
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Недостаточно аргументов.\n\n"
            "Использование: /unlink_impression <id>\n\n"
            "Пример: /unlink_impression 5"
        )
        return

    # Парсим ID
    try:
        impression_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Невалидный ID впечатления.\n\n"
            "ID должен быть числом."
        )
        return

    try:
        conn = _get_db_connection()

        # Проверяем существование впечатления
        impression = get_impression_by_id(conn, impression_id, chat_id)
        if not impression:
            await update.message.reply_text(
                f"❌ Впечатление с ID {impression_id} не найдено.\n\n"
                f"Посмотреть ваши впечатления: /impressions"
            )
            return

        # Отвязываем
        success = unlink_impression(conn, impression_id, chat_id)

        if success:
            await update.message.reply_text(
                f"✅ Впечатление отвязано от записи.\n\n"
                f"💭 _{impression['text']}_"
            )
        else:
            await update.message.reply_text(
                f"❌ Не удалось отвязать впечатление.\n"
                f"Попробуйте позже."
            )

    except Exception as e:
        logger.error(f"Ошибка при отвязке впечатления {impression_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при отвязке впечатления.\n"
            "Попробуйте позже."
        )


def register(application) -> None:
    """Регистрирует handlers для привязки впечатлений."""
    application.add_handler(CommandHandler('link_impression', link_impression_handler))
    application.add_handler(CommandHandler('unlink_impression', unlink_impression_handler))

    logger.info("Impression link handlers зарегистрированы")
