"""
Модуль для импорта данных из CSV-файлов.
Обрабатывает загрузку, проверку и импорт CSV-файлов в систему.
"""

import csv
import io
import logging
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters, CallbackQueryHandler
)

from src.config import IMPORT_CSV_FILE, IMPORT_CSV_CONFIRM
from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import save_data
from src.utils.formatters import format_entry_summary
from src.handlers.basic import cancel

# Настройка логгирования
logger = logging.getLogger(__name__)


async def start_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс импорта CSV-файла.
    Запрашивает у пользователя файл для загрузки.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (IMPORT_CSV_FILE)
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} начал процесс импорта CSV")
    
    await update.message.reply_text(
        "Вы начали процесс импорта данных из CSV-файла.\n\n"
        "CSV-файл должен содержать следующие колонки:\n"
        "- date (в формате YYYY-MM-DD)\n"
        "- mood (оценка от 1 до 10)\n"
        "- sleep (оценка от 1 до 10)\n"
        "- balance (оценка от 1 до 10)\n"
        "- mania (оценка от 1 до 10)\n"
        "- depression (оценка от 1 до 10)\n"
        "- anxiety (оценка от 1 до 10)\n"
        "- irritability (оценка от 1 до 10)\n"
        "- productivity (оценка от 1 до 10)\n"
        "- sociability (оценка от 1 до 10)\n"
        "- comment (необязательно)\n\n"
        "Пожалуйста, отправьте файл CSV или /cancel для отмены."
    )
    
    return IMPORT_CSV_FILE


async def process_csv_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает загруженный CSV-файл, проверяет его структуру и данные.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (IMPORT_CSV_CONFIRM или IMPORT_CSV_FILE в случае ошибки)
    """
    chat_id = update.effective_chat.id
    
    # Проверка, что сообщение содержит документ
    if not update.message.document:
        await update.message.reply_text(
            "Пожалуйста, отправьте CSV-файл в виде документа."
        )
        return IMPORT_CSV_FILE
    
    # Проверка, что документ - это CSV
    file = update.message.document
    if not file.file_name.endswith('.csv'):
        await update.message.reply_text(
            "Отправленный файл не является CSV. Пожалуйста, отправьте файл с расширением .csv."
        )
        return IMPORT_CSV_FILE
    
    try:
        # Скачивание файла
        csv_file = await context.bot.get_file(file.file_id)
        csv_bytes = await csv_file.download_as_bytearray()
        csv_io = io.BytesIO(csv_bytes)
        
        # Чтение CSV в pandas DataFrame
        try:
            df = pd.read_csv(csv_io, encoding='utf-8')
        except UnicodeDecodeError:
            # Если UTF-8 не работает, пробуем windows-1251 (для кириллицы)
            csv_io.seek(0)
            df = pd.read_csv(csv_io, encoding='windows-1251')
        
        logger.info(f"Успешно прочитан CSV-файл с {len(df)} строками")
        
        # Проверка обязательных колонок
        required_columns = ['date', 'mood', 'sleep', 'balance', 'mania', 
                            'depression', 'anxiety', 'irritability', 
                            'productivity', 'sociability']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            await update.message.reply_text(
                f"В вашем CSV-файле отсутствуют обязательные колонки: {', '.join(missing_columns)}.\n"
                "Пожалуйста, убедитесь, что файл содержит все необходимые данные и попробуйте снова."
            )
            return IMPORT_CSV_FILE
        
        # Проверка формата даты
        try:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        except Exception as e:
            await update.message.reply_text(
                "Ошибка при обработке колонки 'date'. Убедитесь, что даты в формате ГГГГ-ММ-ДД.\n"
                f"Детали ошибки: {str(e)}"
            )
            return IMPORT_CSV_FILE
        
        # Проверка числовых колонок
        numeric_columns = ['mood', 'sleep', 'balance', 'mania', 'depression',
                          'anxiety', 'irritability', 'productivity', 'sociability']
        
        for col in numeric_columns:
            try:
                df[col] = pd.to_numeric(df[col])
                
                # Проверка диапазона (1-10)
                if df[col].min() < 1 or df[col].max() > 10:
                    await update.message.reply_text(
                        f"Значения в колонке '{col}' должны быть от 1 до 10. "
                        f"Найдены значения вне диапазона: минимум {df[col].min()}, максимум {df[col].max()}."
                    )
                    return IMPORT_CSV_FILE
                
            except Exception as e:
                await update.message.reply_text(
                    f"Ошибка при обработке числовой колонки '{col}'. Убедитесь, что все значения - числа.\n"
                    f"Детали ошибки: {str(e)}"
                )
                return IMPORT_CSV_FILE
        
        # Добавление пустой колонки comment, если её нет
        if 'comment' not in df.columns:
            df['comment'] = None
        
        # Сохранение DataFrame в контексте для последующего использования
        context.user_data['import_df'] = df
        
        # Сохранение имени файла
        context.user_data['import_filename'] = file.file_name
        
        # Отправка сообщения с подтверждением
        await update.message.reply_text(
            f"CSV-файл '{file.file_name}' успешно обработан.\n"
            f"Найдено {len(df)} записей для импорта.\n\n"
            f"Вы хотите импортировать эти данные? Это действие добавит новые записи "
            f"к вашим существующим данным. Введите 'да' для подтверждения или /cancel для отмены."
        )
        
        return IMPORT_CSV_CONFIRM
        
    except Exception as e:
        logger.error(f"Ошибка при обработке CSV-файла: {e}")
        await update.message.reply_text(
            f"Произошла ошибка при обработке файла: {str(e)}\n"
            "Пожалуйста, убедитесь, что файл имеет правильный формат и попробуйте снова."
        )
        return IMPORT_CSV_FILE


async def confirm_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает подтверждение импорта и сохраняет данные.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    chat_id = update.effective_chat.id
    text = update.message.text.lower()
    
    if text != 'да' and text != 'yes':
        await update.message.reply_text(
            "Импорт отменен.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    
    # Получение DataFrame из контекста
    df = context.user_data.get('import_df')
    if df is None:
        await update.message.reply_text(
            "Произошла ошибка: данные для импорта не найдены.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    
    # Импорт записей
    successful_imports = 0
    failed_imports = 0
    
    await update.message.reply_text(
        "Начинаю импорт данных. Это может занять некоторое время для больших файлов..."
    )
    
    # Обработка каждой записи
    for _, row in df.iterrows():
        # Преобразование строки pandas в словарь
        entry = row.to_dict()
        
        # Преобразование числовых значений в строки (как ожидает метод save_data)
        numeric_columns = ['mood', 'sleep', 'balance', 'mania', 'depression',
                          'anxiety', 'irritability', 'productivity', 'sociability']
        
        for col in numeric_columns:
            entry[col] = str(int(entry[col]))
        
        # Сохранение записи
        if save_data(entry, chat_id):
            successful_imports += 1
        else:
            failed_imports += 1
    
    logger.info(f"Пользователь {chat_id} импортировал {successful_imports} записей из CSV")
    
    # Отправка сообщения о результатах
    result_message = (
        f"Импорт завершен!\n\n"
        f"Успешно импортировано: {successful_imports} записей\n"
    )
    
    if failed_imports > 0:
        result_message += f"Не удалось импортировать: {failed_imports} записей\n"
    
    result_message += "\nТеперь вы можете использовать /stats для просмотра статистики или /visualize для создания графиков."
    
    await update.message.reply_text(
        result_message,
        reply_markup=MAIN_KEYBOARD
    )
    
    return ConversationHandler.END


def register(application):
    """
    Регистрирует обработчики для импорта CSV.
    
    Args:
        application: экземпляр приложения бота
    """
    # Создание обработчика разговора для импорта CSV
    import_handler = ConversationHandler(
        entry_points=[CommandHandler("import", start_import)],
        states={
            IMPORT_CSV_FILE: [MessageHandler(filters.Document.ALL, process_csv_file)],
            IMPORT_CSV_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_import)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(import_handler)
    logger.info("Обработчики для импорта CSV зарегистрированы")
