"""
Модуль для обработки статистики и визуализации данных.
Обрабатывает команды для отображения и выгрузки статистики.
Оптимизированная версия для работы с SQLite и старыми версиями telegram-bot.
"""

import io
import logging
import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler

from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import get_user_entries
from src.utils.formatters import format_stats_summary

# Настройка логгирования
logger = logging.getLogger(__name__)


def prepare_csv_from_entries(entries):
    """
    Подготавливает CSV-данные из записей пользователя.

    Args:
        entries: список записей пользователя

    Returns:
        io.BytesIO: объект с CSV-данными в байтовом формате
    """
    # Преобразование в DataFrame для экспорта
    entries_df = pd.DataFrame(entries)

    # Преобразование DataFrame в байты CSV
    csv_bytes = io.BytesIO()
    entries_df.to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)

    return csv_bytes


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /stats.
    Отображает статистику по записям пользователя.

    Args:
        update: объект с информацией о сообщении
        context: контекст бота

    Returns:
        int: состояние ConversationHandler.END
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} запросил статистику")

    # Отправляем сообщение о начале обработки
    status_message = await update.message.reply_text(
        "Обрабатываю данные, это может занять несколько секунд..."
    )

    # Получение записей пользователя через оптимизированный API
    entries = get_user_entries(chat_id)

    if not entries:
        await status_message.delete()
        await update.message.reply_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    # Преобразование в DataFrame для анализа
    entries_df = pd.DataFrame(entries)

    # Форматирование статистики
    stats_text = format_stats_summary(entries_df)

    # Удаляем сообщение о статусе
    await status_message.delete()

    # Отправляем статистику
    await update.message.reply_text(stats_text, reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


async def download_diary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /download.
    Отправляет пользователю его дневник в формате CSV.

    Args:
        update: объект с информацией о сообщении
        context: контекст бота

    Returns:
        int: состояние ConversationHandler.END
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} запросил скачивание дневника")

    # Отправляем сообщение о начале обработки
    status_message = await update.message.reply_text(
        "Подготавливаю ваш дневник для скачивания..."
    )

    # Получение расшифрованных записей пользователя через оптимизированный API
    entries = get_user_entries(chat_id)

    if not entries:
        await status_message.delete()
        await update.message.reply_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    try:
        # Подготовка CSV-данных (без использования run_in_executor)
        csv_bytes = prepare_csv_from_entries(entries)

        # Удаляем сообщение о статусе
        await status_message.delete()

        # Отправка файла пользователю
        await context.bot.send_document(
            chat_id=chat_id,
            document=csv_bytes,
            filename="my_mood_diary.csv",
            caption="Ваш дневник настроения (расшифрованный)"
        )

        await update.message.reply_text(
            "Файл с вашим дневником отправлен.",
            reply_markup=MAIN_KEYBOARD
        )

    except Exception as e:
        logger.error(f"Ошибка при подготовке CSV для пользователя {chat_id}: {e}")

        # Удаляем сообщение о статусе
        try:
            await status_message.delete()
        except:
            pass

        await update.message.reply_text(
            "Произошла ошибка при подготовке дневника для скачивания. Пожалуйста, попробуйте позже.",
            reply_markup=MAIN_KEYBOARD
        )

    return ConversationHandler.END


def register(application):
    """
    Регистрирует обработчики команд для статистики.

    Args:
        application: экземпляр приложения бота
    """
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("download", download_diary))

    logger.info("Обработчики статистики зарегистрированы")