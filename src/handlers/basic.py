"""
Модуль с базовыми обработчиками команд (/start, /help, /id).
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, CallbackQueryHandler

from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import save_user

# Настройка логгирования
logger = logging.getLogger(__name__)

# Префикс для callback-данных, чтобы их было легко идентифицировать
HELP_PREFIX = "help_"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start.
    Приветствует пользователя и объясняет основные функции бота.
    """
    # Сохранение информации о пользователе
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    save_user(chat_id, username, first_name)

    logger.info(f"Новый пользователь начал сессию: {username} (ID: {chat_id})")

    # Создание welcome-сообщения с форматированием
    welcome_message = (
        "🌈 Добро пожаловать в Трекер Настроения! 🌈\n\n"
        "Я помогу вам отслеживать ваше настроение и другие психологические показатели "
        "с акцентом на приватности и безопасности ваших данных.\n\n"
        "📊 Основные возможности:\n"
        "• Ежедневная оценка настроения и других показателей\n"
        "• Визуализация данных с помощью графиков\n"
        "• Выявление паттернов и зависимостей\n"
        "• Безопасное хранение с шифрованием\n"
        "• Возможность обмена данными с другими пользователями\n\n"
        "🔐 Безопасность: Ваши данные автоматически шифруются с использованием вашего "
        "Telegram ID. Вам не нужно запоминать отдельный пароль.\n\n"
        "Используйте /help для просмотра всех доступных команд или /add для "
        "добавления первой записи. Я проведу вас через все шаги!"
    )

    await update.message.reply_text(
        welcome_message,
        reply_markup=MAIN_KEYBOARD
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /help.
    Отображает категории команд и позволяет пользователю выбрать категорию для подробной информации.
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} запросил справку")

    # Создание кнопок для выбора категории команд с эмодзи
    keyboard = [
        [InlineKeyboardButton("📝 Добавление данных", callback_data=f"{HELP_PREFIX}data_entry")],
        [InlineKeyboardButton("📊 Аналитика и визуализация", callback_data=f"{HELP_PREFIX}analytics")],
        [InlineKeyboardButton("🗂️ Управление данными", callback_data=f"{HELP_PREFIX}data_management")],
        [InlineKeyboardButton("🔄 Обмен данными", callback_data=f"{HELP_PREFIX}sharing")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data=f"{HELP_PREFIX}settings")],
        [InlineKeyboardButton("📋 Полный список команд", callback_data=f"{HELP_PREFIX}all")],
        [InlineKeyboardButton("❌ Закрыть", callback_data=f"{HELP_PREFIX}close")]
    ]

    # Создание заголовка
    help_header = "🔍 Справка по командам\n\nВыберите категорию, чтобы узнать больше о доступных функциях:"

    # Логирование того, что мы собираемся отправить
    logger.info(f"Отправка справочного сообщения с {len(keyboard)} кнопками")

    # Отправка сообщения
    await update.message.reply_text(
        help_header,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Общий обработчик всех callback запросов для справки.
    """
    query = update.callback_query

    # Проверяем, что это действительно callback для справки
    if not query.data.startswith(HELP_PREFIX):
        return

    # Удаляем префикс для удобства обработки
    action = query.data[len(HELP_PREFIX):]

    # Логируем полученный callback для отладки
    logger.info(f"Получен callback справки: {action}")

    # Сначала отвечаем на callback, чтобы убрать часы загрузки
    await query.answer()

    # Обрабатываем команду "назад"
    if action == "back":
        logger.info("Обработка команды 'назад'")

        keyboard = [
            [InlineKeyboardButton("📝 Добавление данных", callback_data=f"{HELP_PREFIX}data_entry")],
            [InlineKeyboardButton("📊 Аналитика и визуализация", callback_data=f"{HELP_PREFIX}analytics")],
            [InlineKeyboardButton("🗂️ Управление данными", callback_data=f"{HELP_PREFIX}data_management")],
            [InlineKeyboardButton("🔄 Обмен данными", callback_data=f"{HELP_PREFIX}sharing")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data=f"{HELP_PREFIX}settings")],
            [InlineKeyboardButton("📋 Полный список команд", callback_data=f"{HELP_PREFIX}all")],
            [InlineKeyboardButton("❌ Закрыть", callback_data=f"{HELP_PREFIX}close")]
        ]

        header = "🔍 Справка по командам\n\nВыберите категорию, чтобы узнать больше о доступных функциях:"

        await query.message.edit_text(
            header,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Обрабатываем команду "закрыть"
    elif action == "close":
        logger.info("Обработка команды 'закрыть'")
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")

    # Обрабатываем все остальные категории
    else:
        logger.info(f"Обработка категории '{action}'")

        # Определяем текст справки в зависимости от категории
        if action == "data_entry":
            category_text = (
                "📝 Добавление данных\n\n"
                "• /add - добавить новую запись (я проведу вас через все шаги)\n"
                "• /import - импортировать данные из CSV-файла\n\n"
                "Примечание: В один день может быть только одна запись. Если вы добавите новую запись "
                "в тот же день, она заменит предыдущую."
            )
        elif action == "analytics":
            category_text = (
                "📊 Аналитика и визуализация\n\n"
                "• /stats - показать статистику по вашим записям\n"
                "• /visualize - построить различные графики на основе ваших данных\n"
                "• /analytics - выявить паттерны и зависимости в ваших данных\n\n"
                "Для получения наиболее точного анализа рекомендуется иметь не менее 7 записей."
            )
        elif action == "data_management":
            category_text = (
                "🗂️ Управление данными\n\n"
                "• /download - скачать ваш дневник в формате CSV\n"
                "• /delete - удалить записи (все или за определенную дату)\n\n"
                "Внимание: Удаление данных необратимо. Рекомендуется регулярно скачивать копию данных."
            )
        elif action == "sharing":
            category_text = (
                "🔄 Обмен данными\n\n"
                "• /send - отправить ваш дневник другому пользователю\n"
                "• /view_shared - просмотреть полученный дневник\n"
                "• /id - показать ваш ID для получения дневников от других\n\n"
                "При обмене данными используется дополнительное шифрование для обеспечения безопасности."
            )
        elif action == "settings":
            category_text = (
                "⚙️ Настройки\n\n"
                "• /notify HH:MM - настроить ежедневные уведомления в указанное время\n"
                "• /cancel_notify - отключить уведомления\n\n"
                "Формат времени: часы:минуты в 24-часовом формате, например, 09:00 или 21:30."
            )
        elif action == "all":
            category_text = (
                "📋 Полный список команд\n\n"
                "• /start - начать работу с ботом\n"
                "• /help - показать это сообщение\n"
                "• /add - добавить новую запись\n"
                "• /cancel - отменить текущую операцию\n"
                "• /stats - показать статистику\n"
                "• /visualize - построить графики\n"
                "• /analytics - выявить паттерны и закономерности\n"
                "• /download - скачать дневник в CSV\n"
                "• /import - импортировать из CSV\n"
                "• /delete - удалить записи\n"
                "• /send - отправить дневник другому\n"
                "• /view_shared - просмотреть полученный дневник\n"
                "• /id - показать ваш ID\n"
                "• /notify HH:MM - настроить уведомления\n"
                "• /cancel_notify - отключить уведомления"
            )
        else:
            category_text = "Неизвестная категория. Пожалуйста, выберите из предложенных."

        # Создание кнопки возврата
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к категориям", callback_data=f"{HELP_PREFIX}back")],
            [InlineKeyboardButton("❌ Закрыть", callback_data=f"{HELP_PREFIX}close")]
        ]

        # Отправка ответа
        await query.message.edit_text(
            category_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /id.
    Отправляет пользователю его ID для обмена дневниками.
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} запросил свой ID")

    await update.message.reply_text(
        f"🆔 Ваш ID: {chat_id}\n\n"
        "Вы можете поделиться этим ID с другими пользователями, "
        "чтобы они могли отправить вам свой дневник через команду /send.",
        reply_markup=MAIN_KEYBOARD
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /cancel.
    Отменяет любой текущий диалог с пользователем.
    """
    logger.info(f"Пользователь {update.effective_chat.id} отменил операцию")

    await update.message.reply_text(
        "❌ Действие отменено.",
        reply_markup=MAIN_KEYBOARD
    )

    # Очистка данных пользователя
    context.user_data.clear()

    return ConversationHandler.END


def register(application):
    """
    Регистрирует обработчики в приложении.
    """
    # Добавление обработчиков простых команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("id", get_user_id))
    application.add_handler(CommandHandler("cancel", cancel))

    # Добавляем обработчик callback-запросов для справки
    application.add_handler(CallbackQueryHandler(handle_help_callback, pattern=f"^{HELP_PREFIX}"))

    logger.info("Базовые обработчики зарегистрированы")