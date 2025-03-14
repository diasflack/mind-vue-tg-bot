"""
Модуль с обработчиками для добавления новых записей в дневник.
Реализует диалоговый процесс ввода всех показателей.
"""

import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters
)

from src.config import (
    MOOD, SLEEP, COMMENT, BALANCE, MANIA, DEPRESSION, 
    ANXIETY, IRRITABILITY, PRODUCTIVITY, SOCIABILITY
)
from src.utils.keyboards import NUMERIC_KEYBOARD, MAIN_KEYBOARD
from src.data.storage import save_data, save_user
from src.utils.formatters import format_entry_summary
from src.handlers.basic import cancel

# Настройка логгирования
logger = logging.getLogger(__name__)


async def start_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс добавления новой записи.
    Первый шаг - запрос уровня настроения.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (MOOD)
    """
    # Сохранение информации о пользователе
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    save_user(chat_id, username, first_name)
    
    # Инициализация словаря данных пользователя с датой (без времени)
    context.user_data['entry'] = {
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    
    logger.info(f"Пользователь {chat_id} начал добавление новой записи")
    
    await update.message.reply_text(
        "Добавляем новую запись. Дата будет установлена автоматически.\n\n"
        "Оцените ваше настроение от 1 до 10:\n"
        "(Чтобы отменить процесс в любой момент, нажмите /cancel)",
        reply_markup=NUMERIC_KEYBOARD
    )
    return MOOD


async def mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет оценку настроения и запрашивает оценку сна.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (SLEEP)
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return MOOD
    
    logger.debug(f"Пользователь {chat_id} установил настроение: {text}")
    context.user_data['entry']['mood'] = text
    
    await update.message.reply_text(
        "Оцените качество вашего сна от 1 до 10:",
        reply_markup=NUMERIC_KEYBOARD
    )
    return SLEEP


async def sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет оценку сна и запрашивает комментарий к записи.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (COMMENT)
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return SLEEP
    
    logger.debug(f"Пользователь {chat_id} установил качество сна: {text}")
    context.user_data['entry']['sleep'] = text
    
    await update.message.reply_text(
        "Введите комментарий к записи (можно пропустить, отправив символ '-'):\n"
        "(Чтобы отменить процесс, нажмите /cancel)",
        reply_markup=ReplyKeyboardRemove()
    )
    return COMMENT


async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет комментарий к записи и запрашивает ровность настроения.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (BALANCE)
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Сохранение комментария (или None, если введен символ '-')
    if text == '-':
        context.user_data['entry']['comment'] = None
        logger.debug(f"Пользователь {chat_id} пропустил комментарий")
    else:
        context.user_data['entry']['comment'] = text
        logger.debug(f"Пользователь {chat_id} добавил комментарий")
    
    await update.message.reply_text(
        "Оцените ровность настроения от 1 до 10:",
        reply_markup=NUMERIC_KEYBOARD
    )
    return BALANCE


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет оценку ровности настроения и запрашивает уровень мании.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (MANIA)
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return BALANCE
    
    logger.debug(f"Пользователь {chat_id} установил ровность настроения: {text}")
    context.user_data['entry']['balance'] = text
    
    await update.message.reply_text(
        "Оцените уровень мании от 1 до 10:",
        reply_markup=NUMERIC_KEYBOARD
    )
    return MANIA


async def mania(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет оценку уровня мании и запрашивает уровень депрессии.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (DEPRESSION)
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return MANIA
    
    logger.debug(f"Пользователь {chat_id} установил уровень мании: {text}")
    context.user_data['entry']['mania'] = text
    
    await update.message.reply_text(
        "Оцените уровень депрессии от 1 до 10:",
        reply_markup=NUMERIC_KEYBOARD
    )
    return DEPRESSION


async def depression(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет оценку уровня депрессии и запрашивает уровень тревоги.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (ANXIETY)
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return DEPRESSION
    
    logger.debug(f"Пользователь {chat_id} установил уровень депрессии: {text}")
    context.user_data['entry']['depression'] = text
    
    await update.message.reply_text(
        "Оцените уровень тревоги от 1 до 10:",
        reply_markup=NUMERIC_KEYBOARD
    )
    return ANXIETY


async def anxiety(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет оценку уровня тревоги и запрашивает уровень раздражительности.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (IRRITABILITY)
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return ANXIETY
    
    logger.debug(f"Пользователь {chat_id} установил уровень тревоги: {text}")
    context.user_data['entry']['anxiety'] = text
    
    await update.message.reply_text(
        "Оцените уровень раздражительности от 1 до 10:",
        reply_markup=NUMERIC_KEYBOARD
    )
    return IRRITABILITY


async def irritability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет оценку уровня раздражительности и запрашивает уровень работоспособности.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (PRODUCTIVITY)
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return IRRITABILITY
    
    logger.debug(f"Пользователь {chat_id} установил уровень раздражительности: {text}")
    context.user_data['entry']['irritability'] = text
    
    await update.message.reply_text(
        "Оцените вашу работоспособность от 1 до 10:",
        reply_markup=NUMERIC_KEYBOARD
    )
    return PRODUCTIVITY


async def productivity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет оценку работоспособности и запрашивает уровень общительности.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: следующее состояние диалога (SOCIABILITY)
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return PRODUCTIVITY
    
    logger.debug(f"Пользователь {chat_id} установил уровень работоспособности: {text}")
    context.user_data['entry']['productivity'] = text
    
    await update.message.reply_text(
        "Оцените вашу общительность от 1 до 10:",
        reply_markup=NUMERIC_KEYBOARD
    )
    return SOCIABILITY


async def sociability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Сохраняет оценку общительности и завершает ввод записи.
    Сохраняет все данные в зашифрованный файл.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return SOCIABILITY
    
    logger.debug(f"Пользователь {chat_id} установил уровень общительности: {text}")
    context.user_data['entry']['sociability'] = text

    # Сохранение полной записи для этого пользователя
    if not save_data(context.user_data['entry'], chat_id):
        logger.info(f"Произошла ошибка при сохранении данных для пользователя {chat_id}")
    else:
        logger.info(f"Запись успешно сохранена для пользователя {chat_id}")

    # Генерация сводки записи для отображения пользователю
    summary = format_entry_summary(context.user_data['entry'])
    
    await update.message.reply_text(summary, reply_markup=MAIN_KEYBOARD)
    
    # Очистка данных пользователя
    context.user_data.clear()
    
    return ConversationHandler.END


def register(application):
    """
    Регистрирует обработчики команд и сообщений для процесса добавления записей.
    
    Args:
        application: экземпляр приложения бота
    """
    # Создание обработчика разговора для процесса добавления записи
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", start_entry)],
        states={
            MOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, mood)],
            SLEEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, sleep)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment)],
            BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, balance)],
            MANIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, mania)],
            DEPRESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, depression)],
            ANXIETY: [MessageHandler(filters.TEXT & ~filters.COMMAND, anxiety)],
            IRRITABILITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, irritability)],
            PRODUCTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, productivity)],
            SOCIABILITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, sociability)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    logger.info("Обработчики для добавления записей зарегистрированы")
