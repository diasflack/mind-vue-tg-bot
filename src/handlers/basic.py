"""
Модуль с базовыми обработчиками команд (/start, /help, /id).
"""

import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler

from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import save_user

# Настройка логгирования
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start.
    Приветствует пользователя и объясняет основные функции бота.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    # Сохранение информации о пользователе
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    save_user(chat_id, username, first_name)
    
    logger.info(f"Новый пользователь начал сессию: {username} (ID: {chat_id})")
    
    await update.message.reply_text(
        'Привет! Я бот для безопасного отслеживания дневных показателей.\n\n'
        'Ваши данные будут автоматически зашифрованы с использованием вашего Telegram ID. '
        'Вам не нужно запоминать отдельный пароль для доступа к вашим записям.\n\n'
        'Используй кнопку /add для добавления новой записи (я проведу тебя через все пункты)\n'
        'Используй /notify HH:MM для настройки ежедневных уведомлений в указанное время.',
        reply_markup=MAIN_KEYBOARD
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message with all available commands."""
    await update.message.reply_text(
        'Команды:\n'
        '/start - начать работу с ботом\n'
        '/help - показать это сообщение\n'
        '/add - добавить новую запись (я буду спрашивать каждый показатель отдельно)\n'
        '/cancel - отменить процесс создания записи (во время добавления)\n'
        '/stats - показать статистику\n'
        '/visualize - построить графики на основе ваших данных\n'  # Add this line
        '/download - скачать ваш дневник в формате CSV\n'
        '/send - отправить ваш дневник другому пользователю\n'
        '/view_shared - просмотреть дневник, которым с вами поделились\n'
        '/id - показать ваш ID для получения дневников от других\n'
        '/notify HH:MM - настроить ежедневные уведомления\n'
        '/cancel_notify - отменить уведомления\n',
        reply_markup=MAIN_KEYBOARD
    )
    return ConversationHandler.END


async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /id.
    Отправляет пользователю его ID для обмена дневниками.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} запросил свой ID")
    
    await update.message.reply_text(
        f"Ваш ID: {chat_id}\n\n"
        "Вы можете поделиться этим ID с другими пользователями, "
        "чтобы они могли отправить вам свой дневник.",
        reply_markup=MAIN_KEYBOARD
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /cancel.
    Отменяет любой текущий диалог с пользователем.
    
    Args:
        update: объект с информацией о сообщении
        context: контекст бота
        
    Returns:
        int: состояние ConversationHandler.END
    """
    logger.info(f"Пользователь {update.effective_chat.id} отменил операцию")
    
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=MAIN_KEYBOARD
    )
    
    # Очистка данных пользователя
    context.user_data.clear()
    
    return ConversationHandler.END


def register(application):
    """
    Регистрирует обработчики в приложении.
    
    Args:
        application: экземпляр приложения бота
    """
    # Добавление обработчиков простых команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("id", get_user_id))
    application.add_handler(CommandHandler("cancel", cancel))
    
    logger.info("Базовые обработчики зарегистрированы")
