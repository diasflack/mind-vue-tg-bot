"""
Модуль для обработки удаления записей.
Обрабатывает команды для удаления записей по дате или всех записей.
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters, CallbackQueryHandler
)

from src.config import DELETE_ENTRY_CONFIRM, DELETE_ENTRY_DATE
from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import delete_all_entries, delete_entry_by_date
from src.handlers.basic import cancel

# Настройка логгирования
logger = logging.getLogger(__name__)


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /delete.
    Выводит кнопки для выбора режима удаления.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (DELETE_ENTRY_CONFIRM)
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} вызвал команду удаления записей")
    
    # Создаем кнопки для выбора режима удаления
    keyboard = [
        [InlineKeyboardButton("Удалить все записи", callback_data="delete_all")],
        [InlineKeyboardButton("Удалить запись за определенную дату", callback_data="delete_by_date")],
        [InlineKeyboardButton("Отмена", callback_data="delete_cancel")]
    ]
    
    await update.message.reply_text(
        "Выберите режим удаления записей:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return DELETE_ENTRY_CONFIRM


async def delete_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор режима удаления.
    
    Args:
        update: объект с информацией о callback query
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога
    """
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    choice = query.data
    
    if choice == "delete_all":
        # Запрос подтверждения удаления всех записей
        keyboard = [
            [InlineKeyboardButton("Да, удалить все", callback_data="confirm_delete_all")],
            [InlineKeyboardButton("Отмена", callback_data="delete_cancel")]
        ]
        
        await query.message.edit_text(
            "Вы уверены, что хотите удалить ВСЕ записи? Это действие нельзя отменить!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return DELETE_ENTRY_CONFIRM
    
    elif choice == "delete_by_date":
        # Запрос даты для удаления записи
        await query.message.edit_text(
            "Введите дату записи, которую хотите удалить, в формате ГГГГ-ММ-ДД (например, 2023-12-25):"
        )
        
        return DELETE_ENTRY_DATE
    
    elif choice == "delete_cancel" or choice == "confirm_delete_cancel":
        # Отмена удаления
        await query.message.edit_text(
            "Удаление отменено.",
            reply_markup=None
        )
        
        await query.message.reply_text(
            "Вы можете продолжить работу с ботом.",
            reply_markup=MAIN_KEYBOARD
        )
        
        return ConversationHandler.END
    
    elif choice == "confirm_delete_all":
        # Подтверждено удаление всех записей
        result = delete_all_entries(chat_id)
        
        if result:
            await query.message.edit_text(
                "Все записи успешно удалены.",
                reply_markup=None
            )
        else:
            await query.message.edit_text(
                "Произошла ошибка при удалении записей, или у вас еще нет записей.",
                reply_markup=None
            )
        
        await query.message.reply_text(
            "Вы можете продолжить работу с ботом.",
            reply_markup=MAIN_KEYBOARD
        )
        
        return ConversationHandler.END
    
    # В случае неизвестного выбора
    await query.message.edit_text(
        "Неизвестная команда. Удаление отменено.",
        reply_markup=None
    )
    
    await query.message.reply_text(
        "Вы можете продолжить работу с ботом.",
        reply_markup=MAIN_KEYBOARD
    )
    
    return ConversationHandler.END


async def delete_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод даты для удаления записи.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    chat_id = update.effective_chat.id
    date_text = update.message.text.strip()
    
    # Проверка формата даты
    try:
        date_obj = datetime.strptime(date_text, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%Y-%m-%d')
    except ValueError:
        await update.message.reply_text(
            "Неверный формат даты. Пожалуйста, используйте формат ГГГГ-ММ-ДД (например, 2023-12-25).",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    
    # Попытка удаления записи
    result = delete_entry_by_date(chat_id, formatted_date)
    
    if result:
        await update.message.reply_text(
            f"Запись за {formatted_date} успешно удалена.",
            reply_markup=MAIN_KEYBOARD
        )
    else:
        await update.message.reply_text(
            f"Запись за {formatted_date} не найдена или произошла ошибка при удалении.",
            reply_markup=MAIN_KEYBOARD
        )
    
    return ConversationHandler.END


def register(application):
    """
    Регистрирует обработчики команд для удаления записей.
    
    Args:
        application: экземпляр приложения бота
    """
    # Создание обработчика разговора для удаления записей
    delete_handler = ConversationHandler(
        entry_points=[CommandHandler("delete", delete_command)],
        states={
            DELETE_ENTRY_CONFIRM: [CallbackQueryHandler(delete_choice, pattern=r"^delete_|^confirm_delete_")],
            DELETE_ENTRY_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_by_date)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(delete_handler)
    logger.info("Обработчики удаления записей зарегистрированы")
