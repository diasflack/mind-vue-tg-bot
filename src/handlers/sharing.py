"""
Модуль для обработки обмена данными между пользователями.
Обрабатывает команды для отправки и просмотра дневников.
"""

import io
import json
import logging
import secrets
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters, CallbackQueryHandler
)

from src.config import (
    SEND_DIARY_USER_ID, SEND_DIARY_START_DATE,
    SHARE_PASSWORD_ENTRY
)
from src.utils.keyboards import MAIN_KEYBOARD, get_date_range_keyboard
from src.data.storage import get_user_data_file, get_user_entries
from src.data.encryption import encrypt_for_sharing
from src.handlers.basic import cancel

# Настройка логгирования
logger = logging.getLogger(__name__)


async def send_diary_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс отправки дневника другому пользователю.
    Запрашивает ID получателя.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (SEND_DIARY_USER_ID)
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} начал процесс отправки дневника")
    
    # Проверка наличия записей у пользователя
    user_file = get_user_data_file(chat_id)
    entries = get_user_entries(chat_id)
    
    if not entries:
        await update.message.reply_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Чтобы отправить ваш дневник другому пользователю, мне нужен ID этого пользователя.\n"
        "Попросите этого пользователя выполнить команду /id и отправить вам полученный номер.\n\n"
        "Введите ID пользователя, которому хотите отправить дневник:",
        reply_markup=ReplyKeyboardRemove()
    )
    return SEND_DIARY_USER_ID


async def send_diary_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ID получателя и запрашивает диапазон дат.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (SEND_DIARY_START_DATE)
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Попытка преобразовать ввод в целое число
    try:
        recipient_id = int(text)
        context.user_data['recipient_id'] = recipient_id
        logger.info(f"Пользователь {chat_id} указал получателя: {recipient_id}")
        
        # Создание кнопок выбора диапазона дат
        keyboard = get_date_range_keyboard()
        
        await update.message.reply_text(
            "Выберите период, за который хотите отправить данные:",
            reply_markup=keyboard
        )
        return SEND_DIARY_START_DATE
    
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите корректный числовой ID пользователя.\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
        )
        return SEND_DIARY_USER_ID


async def process_date_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбранный диапазон дат и отправляет зашифрованный дневник получателю.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    recipient_id = context.user_data.get('recipient_id')
    
    # Сохранение выбранного диапазона дат
    context.user_data['selected_date_range'] = query.data
    logger.debug(f"Пользователь {chat_id} выбрал диапазон: {query.data}")
    
    # Генерация случайного одноразового пароля для обмена
    sharing_password = ''.join(
        secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') 
        for _ in range(10)
    )
    context.user_data['sharing_password'] = sharing_password
    
    # Получение записей пользователя
    entries = get_user_entries(chat_id)
    
    if not entries:
        await query.message.reply_text(
            "Не удалось получить или расшифровать записи.", 
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    
    # Обработка диапазона дат
    date_range = context.user_data['selected_date_range']
    
    # Преобразование в DataFrame для фильтрации
    import pandas as pd
    entries_df = pd.DataFrame(entries)
    
    if date_range == "date_range_all":
        # Использовать все данные
        filtered_df = entries_df
    else:
        # Извлечение дат из данных обратного вызова
        _, start_date, end_date = date_range.split('_', 2)
        
        # Преобразование дат в datetime для сравнения
        if 'date' in entries_df.columns:
            entries_df['date'] = pd.to_datetime(entries_df['date'])
            filtered_df = entries_df[(entries_df['date'] >= start_date) & (entries_df['date'] <= end_date)]
        else:
            filtered_df = entries_df
    
    if len(filtered_df) == 0:
        await query.message.reply_text(
            "За выбранный период нет данных для отправки.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    
    # Повторная шифровка отфильтрованных данных с одноразовым паролем для получателя
    all_entries = filtered_df.to_dict('records')
    encrypted_for_sharing = encrypt_for_sharing(all_entries, sharing_password)
    
    # Создание пользовательского формата для зашифрованного файла
    encrypted_package = {
        'encrypted_data': encrypted_for_sharing,
        'sender_id': chat_id,
        'format_version': '1.0'
    }
    
    # Преобразование в JSON, затем в байты
    encrypted_bytes = io.BytesIO()
    encrypted_bytes.write(json.dumps(encrypted_package).encode('utf-8'))
    encrypted_bytes.seek(0)
    
    try:
        # Получение информации об отправителе
        sender_info = ""
        if query.from_user.username:
            sender_info = f" от @{query.from_user.username}"
        elif query.from_user.first_name:
            sender_info = f" от {query.from_user.first_name}"
        
        # Отправка зашифрованного файла получателю
        await context.bot.send_document(
            chat_id=recipient_id,
            document=encrypted_bytes,
            filename="shared_encrypted_diary.json",
            caption=f"Зашифрованный дневник настроения{sender_info}. Для просмотра используйте команду /view_shared."
        )
        
        await query.message.reply_text(
            f"Дневник успешно отправлен указанному пользователю!\n\n"
            f"Сообщите получателю пароль '{sharing_password}' для доступа к данным. "
            f"Этот пароль будет нужен получателю при использовании команды /view_shared.",
            reply_markup=MAIN_KEYBOARD
        )
        logger.info(f"Пользователь {chat_id} успешно отправил дневник пользователю {recipient_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке дневника: {str(e)}")
        await query.message.reply_text(
            f"Не удалось отправить дневник. Возможно, указан неверный ID пользователя или пользователь заблокировал бота.\n\nОшибка: {str(e)}",
            reply_markup=MAIN_KEYBOARD
        )
    
    return ConversationHandler.END


async def view_shared_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс просмотра полученного дневника.
    Запрашивает пароль для расшифровки.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (SHARE_PASSWORD_ENTRY)
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} начал процесс просмотра полученного дневника")
    
    # Запрос пересылки файла дневника
    await update.message.reply_text(
        "Для просмотра полученного дневника, пожалуйста, перешлите мне файл дневника, "
        "который вам отправили.\n\n"
        "После этого вам потребуется ввести пароль, который вам сообщил отправитель.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Запрос пароля
    await update.message.reply_text(
        "Пожалуйста, введите пароль для расшифровки полученного дневника:"
    )
    return SHARE_PASSWORD_ENTRY


async def process_shared_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает пароль для просмотра общего дневника.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    # В полной реализации здесь будет расшифровка загруженного файла
    # и отображение содержимого дневника
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} ввел пароль для расшифровки дневника")
    
    await update.message.reply_text(
        "Функция просмотра общих дневников требует обработки загруженных файлов, "
        "что выходит за рамки этого примера. В полной реализации здесь будет "
        "расшифровка и отображение общего дневника с использованием введенного пароля.",
        reply_markup=MAIN_KEYBOARD
    )
    return ConversationHandler.END


def register(application):
    """
    Регистрирует обработчики команд для обмена данными.
    
    Args:
        application: экземпляр приложения бота
    """
    # Регистрация обработчика для отправки дневника
    send_diary_handler = ConversationHandler(
        entry_points=[CommandHandler("send", send_diary_start)],
        states={
            SEND_DIARY_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_diary_user_id)],
            SEND_DIARY_START_DATE: [CallbackQueryHandler(process_date_range, pattern=r"^date_range_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )
    application.add_handler(send_diary_handler)
    
    # Регистрация обработчика для просмотра полученного дневника
    view_shared_handler = ConversationHandler(
        entry_points=[CommandHandler("view_shared", view_shared_start)],
        states={
            SHARE_PASSWORD_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_shared_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(view_shared_handler)
    
    # Регистрация обработчика для кнопок выбора диапазона дат
    application.add_handler(CallbackQueryHandler(process_date_range, pattern=r"^date_range_"))
    
    logger.info("Обработчики обмена данными зарегистрированы")
