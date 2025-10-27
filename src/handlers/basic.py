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
        [InlineKeyboardButton("📋 Опросы", callback_data=f"{HELP_PREFIX}surveys")],
        [InlineKeyboardButton("💭 Впечатления", callback_data=f"{HELP_PREFIX}impressions")],
        [InlineKeyboardButton("📤 Экспорт данных", callback_data=f"{HELP_PREFIX}export")],
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
            [InlineKeyboardButton("📋 Опросы", callback_data=f"{HELP_PREFIX}surveys")],
            [InlineKeyboardButton("💭 Впечатления", callback_data=f"{HELP_PREFIX}impressions")],
            [InlineKeyboardButton("📤 Экспорт данных", callback_data=f"{HELP_PREFIX}export")],
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
                "*Основная аналитика:*\n"
                "• /stats - статистика по записям настроения\n"
                "• /visualize - построить графики\n"
                "• /analytics - выявить паттерны и зависимости\n"
                "• /recent - показать последние записи\n\n"
                "*Расширенная аналитика:*\n"
                "• /combined_analytics [период] - объединенная аналитика настроений, впечатлений и опросов\n"
                "• /impression_analytics [опции] - детальная аналитика впечатлений\n"
                "• /survey_stats <название> - статистика по конкретному опросу\n\n"
                "Для точного анализа рекомендуется иметь не менее 7 записей."
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
                "*Уведомления о настроении:*\n"
                "• /notify HH:MM - настроить ежедневные уведомления в указанное время\n"
                "• /cancel_notify - отключить уведомления\n\n"
                "*Напоминания об опросах:*\n"
                "• /survey_reminders - управление напоминаниями\n"
                "• /set_reminder <название> <время> - установить напоминание\n"
                "• /remove_reminder <название> - удалить напоминание\n\n"
                "Формат времени: часы:минуты в 24-часовом формате, например, 09:00 или 21:30."
            )
        elif action == "surveys":
            category_text = (
                "📋 Опросы\n\n"
                "*Работа с опросами:*\n"
                "• /surveys - список доступных опросов\n"
                "• /my_surveys - мои созданные опросы\n"
                "• /create_survey - создать новый опрос\n"
                "• /survey_stats <название> - статистика по опросу\n\n"
                "*Избранные опросы (быстрый доступ):*\n"
                "• /favorites - показать избранные опросы\n"
                "• /add_favorite <название> - добавить опрос в избранное\n"
                "• /remove_favorite <название> - удалить из избранного\n\n"
                "*Управление:*\n"
                "• /edit_survey <название> - редактировать опрос\n"
                "• /delete_survey <название> - удалить опрос\n"
                "• /activate_survey <название> - активировать опрос\n"
                "• /deactivate_survey <название> - деактивировать опрос"
            )
        elif action == "impressions":
            category_text = (
                "💭 Впечатления\n\n"
                "*Просмотр впечатлений:*\n"
                "• /impressions - сегодняшние впечатления\n"
                "• /impressions_history - история всех впечатлений\n"
                "• /add_impression - добавить новое впечатление\n\n"
                "*Аналитика:*\n"
                "• /impression_analytics [опции] - подробная аналитика\n"
                "  Опции: --period N, --category <тип>, --detailed\n\n"
                "*Связывание с записями:*\n"
                "• /link_impression <id> - привязать впечатление к записи\n"
                "• /unlink_impression <id> - отвязать впечатление\n\n"
                "Связанные впечатления автоматически отображаются в /recent."
            )
        elif action == "export":
            category_text = (
                "📤 Экспорт данных\n\n"
                "*Экспорт впечатлений:*\n"
                "• /export_impressions [csv|json] - экспорт всех впечатлений\n"
                "  Опции: --from YYYY-MM-DD, --to YYYY-MM-DD\n\n"
                "*Экспорт ответов опросов:*\n"
                "• /export_survey <название> [csv|json] - экспорт ответов конкретного опроса\n"
                "  Опции: --from YYYY-MM-DD, --to YYYY-MM-DD\n\n"
                "*Полный экспорт:*\n"
                "• /export_all - экспорт всех данных (впечатления + опросы) в ZIP-архиве\n\n"
                "Форматы: CSV (таблицы) или JSON (программный доступ)."
            )
        elif action == "all":
            category_text = (
                "📋 Полный список команд\n\n"
                "*Основные:*\n"
                "/start /help /cancel /id /recent\n\n"
                "*Записи настроения:*\n"
                "/add /add_date /stats /delete\n\n"
                "*Аналитика:*\n"
                "/visualize /analytics /combined_analytics\n\n"
                "*Опросы:*\n"
                "/surveys /my_surveys /create_survey /survey_stats\n"
                "/favorites /add_favorite /remove_favorite\n"
                "/edit_survey /delete_survey /activate_survey /deactivate_survey\n\n"
                "*Впечатления:*\n"
                "/impressions /impressions_history /add_impression\n"
                "/impression_analytics /link_impression /unlink_impression\n\n"
                "*Экспорт:*\n"
                "/export_impressions /export_survey /export_all\n\n"
                "*Уведомления:*\n"
                "/notify /cancel_notify /survey_reminders\n"
                "/set_reminder /remove_reminder\n\n"
                "*Обмен данными:*\n"
                "/download /import /send /view_shared\n\n"
                "Используйте /help и выберите категорию для подробной информации."
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

    # Обогащаем записи привязанными впечатлениями
    try:
        from src.data.storage import _get_db_connection
        from src.utils.formatters import enrich_entries_with_impressions

        conn = _get_db_connection()
        entries = enrich_entries_with_impressions(entries, chat_id, conn)
    except Exception as e:
        logger.warning(f"Не удалось обогатить записи впечатлениями: {e}")

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
        # Основные команды
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("help", "Показать справку"),
        BotCommand("add", "Добавить новую запись"),
        BotCommand("cancel", "Отменить активную команду"),

        # Записи настроения
        BotCommand("recent", "Показать последние записи"),
        BotCommand("stats", "Показать статистику"),
        BotCommand("delete", "Удалить записи"),

        # Визуализация и аналитика
        BotCommand("visualize", "Построить графики"),
        BotCommand("analytics", "Выявить паттерны"),
        BotCommand("combined_analytics", "Объединенная аналитика"),

        # Опросы
        BotCommand("surveys", "Доступные опросы"),
        BotCommand("my_surveys", "Мои опросы"),
        BotCommand("create_survey", "Создать опрос"),
        BotCommand("survey_stats", "Статистика опроса"),

        # Избранные опросы (Phase 5.3)
        BotCommand("favorites", "Избранные опросы"),
        BotCommand("add_favorite", "Добавить в избранное"),
        BotCommand("remove_favorite", "Удалить из избранного"),

        # Напоминания об опросах (Phase 5.2)
        BotCommand("survey_reminders", "Напоминания об опросах"),
        BotCommand("set_reminder", "Установить напоминание"),
        BotCommand("remove_reminder", "Удалить напоминание"),

        # Впечатления
        BotCommand("impressions", "Сегодняшние впечатления"),
        BotCommand("impressions_history", "История впечатлений"),
        BotCommand("add_impression", "Добавить впечатление"),
        BotCommand("impression_analytics", "Аналитика впечатлений"),

        # Связывание впечатлений (Phase 5.1)
        BotCommand("link_impression", "Привязать впечатление"),
        BotCommand("unlink_impression", "Отвязать впечатление"),

        # Экспорт данных (Phase 5.4)
        BotCommand("export_impressions", "Экспорт впечатлений"),
        BotCommand("export_survey", "Экспорт ответов опроса"),
        BotCommand("export_all", "Экспорт всех данных"),

        # Уведомления
        BotCommand("notify", "Настроить уведомления"),
        BotCommand("cancel_notify", "Отключить уведомления"),

        # Прочее
        BotCommand("download", "Скачать дневник в CSV"),
        BotCommand("id", "Показать ваш ID"),
        BotCommand("send", "Отправить дневник другому"),
        BotCommand("view_shared", "Просмотреть полученный дневник")
    ]

    await application.bot.set_my_commands(commands)
    logger.info(f"Установлено {len(commands)} команд для меню бота")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик ошибок для приложения.
    """
    logger.exception(f"Произошла ошибка при обработке обновления: {context.error}")

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