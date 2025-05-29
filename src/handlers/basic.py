"""
Модуль с базовыми обработчиками команд (/start, /help, /id).
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, CallbackQueryHandler

from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import save_user, get_user_entries
from src.utils.formatters import format_entry_list
from src.utils.conversation_manager import end_all_conversations, dump_all_conversations, has_active_conversations

# Настройка логгирования
logger = logging.getLogger(__name__)

# Префикс для callback-данных, чтобы их было легко идентифицировать
HELP_PREFIX = "help_"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start.
    Приветствует пользователя и объясняет основные функции бота.
    """
    # Завершаем все активные диалоги пользователя перед началом нового
    chat_id = update.effective_chat.id
    end_all_conversations(chat_id)

    # Сохранение информации о пользователе
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
    # Завершаем все активные диалоги пользователя перед началом нового
    chat_id = update.effective_chat.id
    end_all_conversations(chat_id)

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
                "• /add - добавить новую запись за сегодня (я проведу вас через все шаги)\n"
                "• /add_date - добавить запись за другую дату (можно выбрать прошедшую дату)\n"
                "• /import - импортировать данные из CSV-файла\n"
                "• /recent - показать последние записи\n\n"
                "🗓️ Команда /add_date позволяет:\n"
                "• Быстро выбрать вчера, 2-7 дней назад, неделю назад\n"
                "• Ввести дату вручную в удобных форматах (25.05.2025, 25.05.25, 25.05)\n"
                "• Нельзя добавлять записи на будущие даты\n\n"
                "Примечание: При повторном добавлении записи за ту же дату, новая запись заменит предыдущую. "
                "Это удобно для корректировки показателей."
            )
        elif action == "analytics":
            category_text = (
                "📊 Аналитика и визуализация\n\n"
                "• /stats - показать статистику по вашим записям\n"
                "• /visualize - построить различные графики на основе ваших данных\n"
                "• /analytics - выявить паттерны и зависимости в ваших данных\n"
                "• /recent - показать последние записи\n\n"
                "Для получения наиболее точного анализа рекомендуется иметь не менее 7 записей."
            )
        elif action == "data_management":
            category_text = (
                "🗂️ Управление данными\n\n"
                "• /download - скачать ваш дневник в формате CSV\n"
                "• /delete - удалить записи (все или за определенную дату)\n"
                "• /recent - показать последние записи\n\n"
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
                "• /add - добавить новую запись за сегодня\n"
                "• /add_date - добавить запись за другую дату\n"
                "• /cancel - отменить текущую операцию или диалог\n"
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
                "• /cancel_notify - отключить уведомления\n"
                "• /recent - показать последние записи"
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
    # Завершаем все активные диалоги пользователя перед началом нового
    chat_id = update.effective_chat.id
    end_all_conversations(chat_id)

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
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} использовал команду /cancel")

    # Вывод всех активных диалогов для отладки
    dump_all_conversations()

    # Проверка есть ли активные диалоги перед отменой
    has_active = has_active_conversations(chat_id)

    # Завершаем все активные диалоги
    ended_conversations = end_all_conversations(chat_id)

    # Вывод всех активных диалогов после отмены для отладки
    dump_all_conversations()

    # Очистка данных пользователя
    context.user_data.clear()

    # Формируем сообщение в зависимости от наличия активных диалогов
    if ended_conversations:
        message = "❌ Все активные команды отменены."
        logger.info(f"Отменены команды: {ended_conversations}")
    else:
        if has_active:
            message = "❌ Все активные команды отменены."
            logger.info("Активные команды были, но не найдены в менеджере")
        else:
            message = "ℹ️ Нет активных команд для отмены."
            logger.info("Активные команды не найдены")

    await update.message.reply_text(
        message,
        reply_markup=MAIN_KEYBOARD
    )

    return ConversationHandler.END


async def recent_entries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /recent.
    Отображает недавние записи пользователя.
    """
    # Завершаем все активные диалоги пользователя перед началом нового
    chat_id = update.effective_chat.id
    end_all_conversations(chat_id)

    logger.info(f"Пользователь {chat_id} запросил недавние записи")

    # Получение записей пользователя
    entries = get_user_entries(chat_id)

    if not entries:
        await update.message.reply_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # Форматирование и отправка списка последних записей
    formatted_entries = format_entry_list(entries)

    await update.message.reply_text(
        formatted_entries,
        reply_markup=MAIN_KEYBOARD
    )


async def setup_commands(application):
    """
    Устанавливает список команд для меню бота.
    """
    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("help", "Показать справку"),
        BotCommand("add", "Добавить новую запись"),
        BotCommand("cancel", "Отменить активную команду"),
        BotCommand("stats", "Показать статистику"),
        BotCommand("recent", "Показать последние записи"),
        BotCommand("visualize", "Построить графики"),
        BotCommand("analytics", "Выявить паттерны"),
        BotCommand("download", "Скачать дневник в CSV"),
        BotCommand("delete", "Удалить записи"),
        BotCommand("notify", "Настроить уведомления"),
        BotCommand("cancel_notify", "Отключить уведомления"),
        BotCommand("id", "Показать ваш ID"),
        BotCommand("send", "Отправить дневник другому"),
        BotCommand("view_shared", "Просмотреть полученный дневник")
    ]

    await application.bot.set_my_commands(commands)
    logger.info("Установлены команды для меню бота")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик ошибок для приложения.
    """
    logger.error(f"Произошла ошибка при обработке обновления: {context.error}")

    # Если обновление доступно, можно получить chat_id
    if update:
        chat_id = update.effective_chat.id if update.effective_chat else None

        if chat_id:
            # В случае ошибки завершаем все активные диалоги пользователя
            logger.info(f"Завершение всех диалогов пользователя {chat_id} из-за ошибки")
            end_all_conversations(chat_id)

            # Уведомление пользователя о проблеме
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Произошла ошибка при обработке запроса. Пожалуйста, попробуйте снова.",
                    reply_markup=MAIN_KEYBOARD
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке: {e}")


def register(application):
    """
    Регистрирует обработчики в приложении.
    """
    # Добавление обработчиков простых команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("id", get_user_id))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("recent", recent_entries))

    # Добавляем обработчик callback-запросов для справки
    application.add_handler(CallbackQueryHandler(handle_help_callback, pattern=f"^{HELP_PREFIX}"))

    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    # Установка команд меню бота при запуске
    application.post_init = setup_commands

    logger.info("Базовые обработчики зарегистрированы")