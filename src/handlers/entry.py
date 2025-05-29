"""
Модуль с обработчиками для добавления новых записей в дневник.
Реализует диалоговый процесс ввода всех показателей.
"""

import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters, Application
)

from src.config import (
    MOOD, SLEEP, COMMENT, BALANCE, MANIA, DEPRESSION,
    ANXIETY, IRRITABILITY, PRODUCTIVITY, SOCIABILITY,
    DATE_SELECTION, MANUAL_DATE_INPUT
)
from src.utils.keyboards import NUMERIC_KEYBOARD, MAIN_KEYBOARD
from src.data.storage import save_data, save_user, get_user_entries
from src.utils.formatters import format_entry_summary
from src.utils.date_helpers import get_today
from src.utils.conversation_manager import register_conversation, end_conversation, end_all_conversations

# Настройка логгирования
logger = logging.getLogger(__name__)

# Имя обработчика для менеджера диалогов
HANDLER_NAME = "entry_handler"

# Глобальный объект для хранения ссылки на обработчик разговора
entry_conversation_handler = None

async def custom_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Локальный обработчик отмены для этого диалога.
    """
    chat_id = update.effective_chat.id
    logger.info(f"Отмена диалога добавления записи для пользователя {chat_id}")

    # Завершение диалога в менеджере
    end_conversation(chat_id, HANDLER_NAME)

    # Очистка данных пользователя
    if 'entry' in context.user_data:
        context.user_data.pop('entry')

    await update.message.reply_text(
        "Добавление записи отменено.",
        reply_markup=MAIN_KEYBOARD
    )

    return ConversationHandler.END


async def start_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс добавления новой записи.
    Первый шаг - запрос уровня настроения.
    """
    # Завершаем все активные диалоги пользователя
    chat_id = update.effective_chat.id
    end_all_conversations(chat_id)

    # Регистрируем новый активный диалог
    register_conversation(chat_id, HANDLER_NAME, MOOD)

    # Сохранение информации о пользователе
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    save_user(chat_id, username, first_name)

    # Получение текущей даты
    today = get_today()

    # Проверка наличия записи за сегодня
    entries = get_user_entries(chat_id)
    today_entry = None
    for entry in entries:
        if entry.get('date') == today:
            today_entry = entry
            break

    # Инициализация словаря данных пользователя с датой
    context.user_data['entry'] = {'date': today}

    # Подготовка сообщения о замене существующей записи
    replace_message = ""
    if today_entry:
        replace_message = "У вас уже есть запись за сегодня. Новая запись заменит существующую.\n\n"

    logger.info(f"Пользователь {chat_id} начал добавление новой записи за {today}")

    await update.message.reply_text(
        f"{replace_message}Добавляем новую запись за {today}.\n\n"
        "Оцените ваше настроение от 1 до 10:\n"
        "(Чтобы отменить процесс в любой момент, нажмите /cancel)",
        reply_markup=NUMERIC_KEYBOARD
    )

    return MOOD



# Имя обработчика для диалога с выбором даты
HANDLER_DATE_NAME = "entry_date_handler"

# Глобальный объект для хранения ссылки на обработчик разговора с датой
entry_date_conversation_handler = None


async def start_entry_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс добавления новой записи с выбором даты.
    Первый шаг - выбор даты для записи.
    """
    # Завершаем все активные диалоги пользователя
    chat_id = update.effective_chat.id
    end_all_conversations(chat_id)

    # Регистрируем новый активный диалог
    register_conversation(chat_id, HANDLER_DATE_NAME, DATE_SELECTION)

    # Сохранение информации о пользователе
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    save_user(chat_id, username, first_name)

    # Инициализация словаря данных пользователя без даты
    context.user_data['entry'] = {}

    logger.info(f"Пользователь {chat_id} начал добавление записи с выбором даты")

    # Импортируем клавиатуру для выбора даты
    from src.utils.keyboards import get_date_selection_keyboard

    await update.message.reply_text(
        "Выберите дату для новой записи:",
        reply_markup=get_date_selection_keyboard()
    )

    return DATE_SELECTION


async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор даты из inline клавиатуры.
    """
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_DATE_NAME, MANUAL_DATE_INPUT)

    # Импортируем необходимые функции
    from src.utils.date_helpers import get_yesterday, get_days_ago, format_date_for_user

    # Определяем выбранную дату
    callback_data = query.data
    selected_date = None

    if callback_data == "date_yesterday":
        selected_date = get_yesterday()
    elif callback_data == "date_2days":
        selected_date = get_days_ago(2)
    elif callback_data == "date_3days":
        selected_date = get_days_ago(3)
    elif callback_data == "date_week":
        selected_date = get_days_ago(7)
    elif callback_data == "date_manual":
        # Переходим к ручному вводу даты
        await query.edit_message_text(
            "Введите дату в формате ДД.ММ.ГГГГ (например: 25.05.2025):\n"
            "Поддерживаемые форматы:\n"
            "• 25.05.2025\n"
            "• 25.05.25\n"
            "• 25.05 (текущий год)\n"
            "• 25/05/2025\n"
            "• 2025-05-25\n\n"
            "(Чтобы отменить процесс, нажмите /cancel)"
        )
        return MANUAL_DATE_INPUT

    if selected_date:
        # Сохраняем выбранную дату и переходим к вводу показателей
        context.user_data['entry']['date'] = selected_date
        
        # Проверяем, есть ли уже запись за эту дату
        from src.data.storage import get_user_entries
        entries = get_user_entries(chat_id)
        entry_exists = False
        for entry in entries:
            if entry.get('date') == selected_date:
                entry_exists = True
                break

        # Переходим к состоянию MOOD
        register_conversation(chat_id, HANDLER_DATE_NAME, MOOD)

        # Подготовка сообщения о замене существующей записи
        replace_message = ""
        if entry_exists:
            formatted_date = format_date_for_user(selected_date, include_day_name=True)
            replace_message = f"У вас уже есть запись за {formatted_date}. Новая запись заменит существующую.\n\n"

        logger.info(f"Пользователь {chat_id} выбрал дату для записи: {selected_date}")

        formatted_date = format_date_for_user(selected_date, include_day_name=True)
        
        # Сначала редактируем сообщение без клавиатуры
        await query.edit_message_text(
            f"{replace_message}Добавляем новую запись за {formatted_date}.\n\n"
            "Оцените ваше настроение от 1 до 10:\n"
            "(Чтобы отменить процесс в любой момент, нажмите /cancel)"
        )
        
        # Затем отправляем клавиатуру отдельным сообщением
        await update.effective_chat.send_message(
            "Выберите оценку:",
            reply_markup=NUMERIC_KEYBOARD
        )

        return MOOD

    # Если что-то пошло не так
    await query.edit_message_text("Произошла ошибка при выборе даты. Попробуйте еще раз.")
    return ConversationHandler.END


async def manual_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ручной ввод даты пользователем.
    """
    chat_id = update.effective_chat.id
    date_input = update.message.text.strip()

    # Импортируем необходимые функции
    from src.utils.date_helpers import parse_user_date, is_valid_entry_date, format_date_for_user
    from src.data.storage import get_user_entries

    # Парсим введенную дату
    parsed_date = parse_user_date(date_input)
    
    if not parsed_date:
        await update.message.reply_text(
            "Неверный формат даты. Пожалуйста, введите дату в одном из поддерживаемых форматов:\n"
            "• 25.05.2025\n"
            "• 25.05.25\n"
            "• 25.05 (текущий год)\n"
            "• 25/05/2025\n"
            "• 2025-05-25\n\n"
            "Попробуйте еще раз:"
        )
        return MANUAL_DATE_INPUT

    # Проверяем валидность даты для записи
    if not is_valid_entry_date(parsed_date):
        await update.message.reply_text(
            "Эта дата недоступна для записей.\n"
            "Нельзя добавлять записи на будущие даты или слишком старые даты.\n\n"
            "Пожалуйста, введите другую дату:"
        )
        return MANUAL_DATE_INPUT

    # Сохраняем дату и переходим к вводу показателей
    context.user_data['entry']['date'] = parsed_date

    # Проверяем, есть ли уже запись за эту дату
    entries = get_user_entries(chat_id)
    entry_exists = False
    for entry in entries:
        if entry.get('date') == parsed_date:
            entry_exists = True
            break

    # Переходим к состоянию MOOD
    register_conversation(chat_id, HANDLER_DATE_NAME, MOOD)

    # Подготовка сообщения о замене существующей записи
    replace_message = ""
    if entry_exists:
        formatted_date = format_date_for_user(parsed_date, include_day_name=True)
        replace_message = f"У вас уже есть запись за {formatted_date}. Новая запись заменит существующую.\n\n"

    logger.info(f"Пользователь {chat_id} ввел дату для записи: {parsed_date}")

    formatted_date = format_date_for_user(parsed_date, include_day_name=True)
    await update.message.reply_text(
        f"{replace_message}Добавляем новую запись за {formatted_date}.\n\n"
        "Оцените ваше настроение от 1 до 10:\n"
        "(Чтобы отменить процесс в любой момент, нажмите /cancel)",
        reply_markup=NUMERIC_KEYBOARD
    )

    return MOOD


async def custom_cancel_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Локальный обработчик отмены для диалога с выбором даты.
    """
    chat_id = update.effective_chat.id
    logger.info(f"Отмена диалога добавления записи с датой для пользователя {chat_id}")

    # Завершение диалога в менеджере
    end_conversation(chat_id, HANDLER_DATE_NAME)

    # Очистка данных пользователя
    if 'entry' in context.user_data:
        context.user_data.pop('entry')

    await update.message.reply_text(
        "Добавление записи отменено.",
        reply_markup=MAIN_KEYBOARD
    )

    return ConversationHandler.END


# Дублированные функции для обработчика с выбором даты
# Эти функции идентичны оригинальным, но используют HANDLER_DATE_NAME

async def mood_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет оценку настроения и запрашивает оценку сна (для диалога с датой)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_DATE_NAME, SLEEP)

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


async def sleep_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет оценку сна и запрашивает комментарий к записи (для диалога с датой)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_DATE_NAME, COMMENT)

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


async def comment_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет комментарий к записи и запрашивает ровность настроения (для диалога с датой)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_DATE_NAME, BALANCE)

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


async def balance_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет оценку ровности настроения и запрашивает уровень мании (для диалога с датой)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_DATE_NAME, MANIA)

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


async def mania_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет оценку уровня мании и запрашивает уровень депрессии (для диалога с датой)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_DATE_NAME, DEPRESSION)

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


async def depression_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет оценку уровня депрессии и запрашивает уровень тревоги (для диалога с датой)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_DATE_NAME, ANXIETY)

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


async def anxiety_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет оценку уровня тревоги и запрашивает уровень раздражительности (для диалога с датой)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_DATE_NAME, IRRITABILITY)

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


async def irritability_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет оценку уровня раздражительности и запрашивает уровень работоспособности (для диалога с датой)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_DATE_NAME, PRODUCTIVITY)

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


async def productivity_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет оценку работоспособности и запрашивает уровень общительности (для диалога с датой)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_DATE_NAME, SOCIABILITY)

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


async def sociability_with_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет оценку общительности и завершает ввод записи (для диалога с датой)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Завершение диалога в менеджере диалогов
    end_conversation(chat_id, HANDLER_DATE_NAME)

    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return SOCIABILITY

    logger.debug(f"Пользователь {chat_id} установил уровень общительности: {text}")
    context.user_data['entry']['sociability'] = text

    # Получаем дату записи из контекста
    entry_date = context.user_data['entry'].get('date')
    
    # Проверяем, есть ли уже запись за эту дату
    from src.data.storage import get_user_entries
    entries = get_user_entries(chat_id)
    entry_replaced = False
    for entry in entries:
        if entry.get('date') == entry_date:
            entry_replaced = True
            break

    # Сохранение полной записи для этого пользователя
    if not save_data(context.user_data['entry'], chat_id):
        logger.info(f"Произошла ошибка при сохранении данных для пользователя {chat_id}")
    else:
        logger.info(f"Запись успешно сохранена для пользователя {chat_id} за дату {entry_date}")

    # Генерация сводки записи для отображения пользователю
    summary = format_entry_summary(context.user_data['entry'])

    # Добавление сообщения о замене, если была заменена существующая запись
    if entry_replaced:
        from src.utils.date_helpers import format_date_for_user
        formatted_date = format_date_for_user(entry_date, include_day_name=True)
        replaced_message = f"Предыдущая запись за {formatted_date} была заменена новой.\n\n"
        summary = replaced_message + summary

    await update.message.reply_text(summary, reply_markup=MAIN_KEYBOARD)

    # Очистка данных пользователя
    context.user_data.clear()

    return ConversationHandler.END


def register(application: Application):
    """
    Регистрирует обработчики команд и сообщений для процесса добавления записей.
    """
    global entry_conversation_handler, entry_date_conversation_handler

    # Создаем новые обработчики для всех состояний с улучшенными фильтрами
    # Обратите внимание на ~filters.TEXT в фильтрах - это предотвращает перехват всех текстовых сообщений

    # Каждый обработчик теперь проверяет, что пользователь находится в нужном состоянии
    # Фильтр для каждого состояния проверяет только числа от 1 до 10 или конкретный формат ввода
    mood_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), mood)
    sleep_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), sleep)
    comment_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, comment)
    balance_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), balance)
    mania_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), mania)
    depression_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), depression)
    anxiety_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), anxiety)
    irritability_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), irritability)
    productivity_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), productivity)
    sociability_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), sociability)

    # Обработчики для диалога с выбором даты
    mood_date_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), mood_with_date)
    sleep_date_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), sleep_with_date)
    comment_date_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, comment_with_date)
    balance_date_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), balance_with_date)
    mania_date_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), mania_with_date)
    depression_date_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), depression_with_date)
    anxiety_date_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), anxiety_with_date)
    irritability_date_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), irritability_with_date)
    productivity_date_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), productivity_with_date)
    sociability_date_handler = MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.Regex(r'^([1-9]|10)$'), sociability_with_date)

    # Обработчики для выбора даты
    date_selection_handler = CallbackQueryHandler(select_date, pattern=r'^date_(yesterday|2days|3days|week|manual)$')
    manual_date_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, manual_date_input)

    # Создание обработчика разговора для процесса добавления записи (стандартный)
    entry_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("add", start_entry)],
        states={
            MOOD: [mood_handler],
            SLEEP: [sleep_handler],
            COMMENT: [comment_handler],
            BALANCE: [balance_handler],
            MANIA: [mania_handler],
            DEPRESSION: [depression_handler],
            ANXIETY: [anxiety_handler],
            IRRITABILITY: [irritability_handler],
            PRODUCTIVITY: [productivity_handler],
            SOCIABILITY: [sociability_handler],
        },
        fallbacks=[CommandHandler("cancel", custom_cancel)],
        name=HANDLER_NAME,
        persistent=False,  # Не сохраняем состояние между перезапусками
        allow_reentry=True,  # Позволяем повторный вход
    )

    # Создание обработчика разговора для процесса добавления записи с выбором даты
    entry_date_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("add_date", start_entry_with_date)],
        states={
            DATE_SELECTION: [date_selection_handler],
            MANUAL_DATE_INPUT: [manual_date_handler],
            MOOD: [mood_date_handler],
            SLEEP: [sleep_date_handler],
            COMMENT: [comment_date_handler],
            BALANCE: [balance_date_handler],
            MANIA: [mania_date_handler],
            DEPRESSION: [depression_date_handler],
            ANXIETY: [anxiety_date_handler],
            IRRITABILITY: [irritability_date_handler],
            PRODUCTIVITY: [productivity_date_handler],
            SOCIABILITY: [sociability_date_handler],
        },
        fallbacks=[CommandHandler("cancel", custom_cancel_date)],
        name=HANDLER_DATE_NAME,
        persistent=False,  # Не сохраняем состояние между перезапусками
        allow_reentry=True,  # Позволяем повторный вход
    )

    # Удаляем старые обработчики если они есть
    for handler in application.handlers.get(0, [])[:]:
        if isinstance(handler, ConversationHandler) and getattr(handler, 'name', None) in [HANDLER_NAME, HANDLER_DATE_NAME]:
            application.remove_handler(handler)
            logger.info(f"Удален старый обработчик диалога {getattr(handler, 'name', 'unknown')}")

    # Добавляем новые обработчики
    application.add_handler(entry_conversation_handler)
    application.add_handler(entry_date_conversation_handler)
    logger.info("Обработчики для добавления записей зарегистрированы")



async def mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет оценку настроения и запрашивает оценку сна."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_NAME, SLEEP)

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
    """Сохраняет оценку сна и запрашивает комментарий к записи."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_NAME, COMMENT)

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
    """Сохраняет комментарий к записи и запрашивает ровность настроения."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_NAME, BALANCE)

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
    """Сохраняет оценку ровности настроения и запрашивает уровень мании."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_NAME, MANIA)

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
    """Сохраняет оценку уровня мании и запрашивает уровень депрессии."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_NAME, DEPRESSION)

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
    """Сохраняет оценку уровня депрессии и запрашивает уровень тревоги."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_NAME, ANXIETY)

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
    """Сохраняет оценку уровня тревоги и запрашивает уровень раздражительности."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_NAME, IRRITABILITY)

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
    """Сохраняет оценку уровня раздражительности и запрашивает уровень работоспособности."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_NAME, PRODUCTIVITY)

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
    """Сохраняет оценку работоспособности и запрашивает уровень общительности."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, HANDLER_NAME, SOCIABILITY)

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
    """Сохраняет оценку общительности и завершает ввод записи."""
    text = update.message.text
    chat_id = update.effective_chat.id

    # Завершение диалога в менеджере диалогов
    end_conversation(chat_id, HANDLER_NAME)

    # Валидация ввода (должно быть число от 1 до 10)
    if not text.isdigit() or int(text) < 1 or int(text) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите число от 1 до 10:",
            reply_markup=NUMERIC_KEYBOARD
        )
        return SOCIABILITY

    logger.debug(f"Пользователь {chat_id} установил уровень общительности: {text}")
    context.user_data['entry']['sociability'] = text

    # Проверяем, есть ли уже запись за сегодня
    today = get_today()
    entries = get_user_entries(chat_id)
    entry_replaced = False
    for entry in entries:
        if entry.get('date') == today:
            entry_replaced = True
            break

    # Сохранение полной записи для этого пользователя
    if not save_data(context.user_data['entry'], chat_id):
        logger.info(f"Произошла ошибка при сохранении данных для пользователя {chat_id}")
    else:
        logger.info(f"Запись успешно сохранена для пользователя {chat_id}")

    # Генерация сводки записи для отображения пользователю
    summary = format_entry_summary(context.user_data['entry'])

    # Добавление сообщения о замене, если была заменена существующая запись
    if entry_replaced:
        replaced_message = "Предыдущая запись за сегодня была заменена новой.\n\n"
        summary = replaced_message + summary

    await update.message.reply_text(summary, reply_markup=MAIN_KEYBOARD)

    # Очистка данных пользователя
    context.user_data.clear()

    return ConversationHandler.END