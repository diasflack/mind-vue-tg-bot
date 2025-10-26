"""
Handlers для добавления и управления вопросами в пользовательских шаблонах (Phase 3.2).

Команды:
- /add_question <название_шаблона> - добавить вопрос к шаблону
"""

import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from src.config import ADD_QUESTION_TYPE, ADD_QUESTION_TEXT, ADD_QUESTION_CONFIG
from src.data.storage import _get_db_connection
from src.data.surveys_storage import (
    get_user_templates,
    get_template_questions,
    add_question_to_template
)

logger = logging.getLogger(__name__)

# Константы
MIN_QUESTION_LENGTH = 10
MAX_QUESTION_LENGTH = 500
MAX_QUESTIONS = 30

# Типы вопросов и их описания
QUESTION_TYPES = {
    'text': '📝 Текст',
    'numeric': '🔢 Число',
    'yes_no': '✅ Да/Нет',
    'time': '🕐 Время',
    'choice': '☑️ Выбор',
    'scale': '📊 Шкала'
}

# Типы которые требуют конфигурацию
TYPES_NEED_CONFIG = {'numeric', 'choice', 'scale'}


async def add_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Начало добавления вопроса - /add_question <название_шаблона>.
    Проверяет шаблон и показывает выбор типа вопроса.
    """
    chat_id = update.effective_chat.id

    # Проверяем что указано название шаблона
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название шаблона.\n\n"
            "Использование: /add_question <название>\n\n"
            "Посмотреть свои шаблоны: /my_surveys"
        )
        return ConversationHandler.END

    template_name = ' '.join(context.args)

    try:
        conn = _get_db_connection()

        # Ищем шаблон пользователя
        templates = get_user_templates(conn, chat_id)
        template = next((t for t in templates if t['name'] == template_name), None)

        if not template:
            await update.message.reply_text(
                f"❌ Шаблон *{template_name}* не найден.\n\n"
                f"Посмотреть свои шаблоны: /my_surveys",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        # Проверяем лимит вопросов
        questions = get_template_questions(conn, template['id'])
        if len(questions) >= MAX_QUESTIONS:
            await update.message.reply_text(
                f"❌ Достигнут лимит вопросов ({MAX_QUESTIONS}) для шаблона *{template_name}*.\n\n"
                f"Удалите ненужные вопросы перед добавлением новых.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        # Сохраняем данные в контекст
        context.user_data['template_id'] = template['id']
        context.user_data['template_name'] = template_name

        # Показываем выбор типа вопроса
        keyboard = []
        for qtype, label in QUESTION_TYPES.items():
            keyboard.append([InlineKeyboardButton(label, callback_data=f"qtype_{qtype}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"➕ *Добавление вопроса к '{template_name}'*\n\n"
            f"Вопросов в шаблоне: {len(questions)}/{MAX_QUESTIONS}\n\n"
            f"Выберите тип вопроса:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return ADD_QUESTION_TYPE

    except Exception as e:
        logger.error(f"Ошибка при начале добавления вопроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже."
        )
        return ConversationHandler.END


async def select_question_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработка выбора типа вопроса.
    """
    query = update.callback_query
    await query.answer()

    # Извлекаем тип из callback_data
    question_type = query.data.replace("qtype_", "")

    # Сохраняем тип в контекст
    context.user_data['question_type'] = question_type

    # Подсказки для каждого типа
    hints = {
        'text': 'Пользователь сможет ввести любой текст.',
        'numeric': 'Пользователь введет число (вы зададите диапазон).',
        'yes_no': 'Пользователь выберет Да или Нет.',
        'time': 'Пользователь введет время в формате ЧЧ:ММ.',
        'choice': 'Пользователь выберет один или несколько вариантов.',
        'scale': 'Пользователь выберет значение на шкале.'
    }

    await query.edit_message_text(
        f"✅ Выбран тип: *{QUESTION_TYPES[question_type]}*\n\n"
        f"{hints.get(question_type, '')}\n\n"
        f"Теперь введите текст вопроса ({MIN_QUESTION_LENGTH}-{MAX_QUESTION_LENGTH} символов):\n\n"
        f"_Для отмены используйте /cancel_",
        parse_mode='Markdown'
    )

    return ADD_QUESTION_TEXT


async def receive_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получает текст вопроса и валидирует его.
    """
    question_text = update.message.text.strip()

    # Валидация длины
    if len(question_text) < MIN_QUESTION_LENGTH:
        await update.message.reply_text(
            f"❌ Текст вопроса слишком короткий.\n"
            f"Минимум {MIN_QUESTION_LENGTH} символов."
        )
        return ADD_QUESTION_TEXT

    if len(question_text) > MAX_QUESTION_LENGTH:
        await update.message.reply_text(
            f"❌ Текст вопроса слишком длинный.\n"
            f"Максимум {MAX_QUESTION_LENGTH} символов."
        )
        return ADD_QUESTION_TEXT

    # Сохраняем текст
    context.user_data['question_text'] = question_text
    question_type = context.user_data['question_type']

    # Для типов требующих конфигурацию - запрашиваем её
    if question_type in TYPES_NEED_CONFIG:
        await update.message.reply_text(
            _get_config_prompt(question_type),
            parse_mode='Markdown'
        )
        return ADD_QUESTION_CONFIG

    # Для простых типов - сразу сохраняем
    return await _save_question(update, context, None)


async def configure_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получает и валидирует конфигурацию для вопроса.
    """
    question_type = context.user_data['question_type']
    config_text = update.message.text.strip()

    # Парсим и валидируем конфигурацию
    config, error = _parse_config(question_type, config_text)

    if error:
        await update.message.reply_text(
            f"❌ {error}\n\n"
            f"{_get_config_prompt(question_type)}",
            parse_mode='Markdown'
        )
        return ADD_QUESTION_CONFIG

    # Сохраняем вопрос с конфигурацией
    return await _save_question(update, context, config)


async def _save_question(update: Update, context: ContextTypes.DEFAULT_TYPE, config: dict) -> int:
    """
    Сохраняет вопрос в БД.
    """
    chat_id = update.effective_chat.id
    template_id = context.user_data['template_id']
    template_name = context.user_data['template_name']
    question_text = context.user_data['question_text']
    question_type = context.user_data['question_type']

    try:
        conn = _get_db_connection()

        # Подготавливаем данные вопроса
        question_data = {
            'question_text': question_text,
            'question_type': question_type,
            'config': json.dumps(config) if config else None,
            'is_required': True
        }

        # Сохраняем вопрос
        question_id = add_question_to_template(conn, template_id, chat_id, question_data)

        if question_id is None:
            await update.message.reply_text(
                "❌ Не удалось добавить вопрос.\n"
                "Возможно, достигнут лимит вопросов."
            )
            return ConversationHandler.END

        # Получаем актуальное количество вопросов
        questions = get_template_questions(conn, template_id)

        await update.message.reply_text(
            f"✅ *Вопрос добавлен!*\n\n"
            f"📝 {question_text}\n"
            f"Тип: {QUESTION_TYPES[question_type]}\n\n"
            f"Вопросов в шаблоне: {len(questions)}/{MAX_QUESTIONS}\n\n"
            f"Добавить еще вопрос:\n"
            f"/add_question {template_name}\n\n"
            f"Активировать шаблон:\n"
            f"/activate_survey {template_name}\n\n"
            f"Посмотреть все вопросы:\n"
            f"/my_surveys",
            parse_mode='Markdown'
        )

        # Очищаем контекст
        for key in ['template_id', 'template_name', 'question_type', 'question_text']:
            context.user_data.pop(key, None)

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка сохранения вопроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении вопроса.\n"
            "Попробуйте позже."
        )
        return ConversationHandler.END


def _get_config_prompt(question_type: str) -> str:
    """
    Возвращает подсказку для ввода конфигурации.
    """
    if question_type == 'numeric':
        return (
            "🔢 *Настройка числового вопроса*\n\n"
            "Введите минимальное и максимальное значение через пробел.\n\n"
            "_Пример:_ `0 100`\n"
            "(числа от 0 до 100)"
        )
    elif question_type == 'choice':
        return (
            "☑️ *Настройка вопроса с выбором*\n\n"
            "Первая строка: `single` (один вариант) или `multiple` (несколько)\n"
            "Далее каждый вариант на новой строке (2-10 вариантов).\n\n"
            "_Пример:_\n"
            "`single`\n"
            "`Вариант 1`\n"
            "`Вариант 2`\n"
            "`Вариант 3`"
        )
    elif question_type == 'scale':
        return (
            "📊 *Настройка шкалы*\n\n"
            "Введите минимум, максимум и шаг через пробел.\n\n"
            "_Пример:_ `1 10 1`\n"
            "(шкала от 1 до 10 с шагом 1)"
        )
    return ""


def _parse_config(question_type: str, config_text: str) -> tuple:
    """
    Парсит и валидирует конфигурацию.

    Returns:
        (config_dict, error_message)
    """
    try:
        if question_type == 'numeric':
            parts = config_text.split()
            if len(parts) != 2:
                return None, "Введите два числа через пробел (минимум и максимум)."

            min_val = float(parts[0])
            max_val = float(parts[1])

            if min_val >= max_val:
                return None, "Минимум должен быть меньше максимума."

            return {'min': min_val, 'max': max_val}, None

        elif question_type == 'choice':
            lines = [line.strip() for line in config_text.split('\n') if line.strip()]

            if len(lines) < 2:
                return None, "Укажите тип выбора и хотя бы один вариант."

            choice_type = lines[0].lower()
            if choice_type not in ['single', 'multiple']:
                return None, "Первая строка должна быть 'single' или 'multiple'."

            options = lines[1:]
            if len(options) < 2:
                return None, "Минимум 2 варианта ответа."

            if len(options) > 10:
                return None, "Максимум 10 вариантов ответа."

            return {'type': choice_type, 'options': options}, None

        elif question_type == 'scale':
            parts = config_text.split()
            if len(parts) != 3:
                return None, "Введите три числа через пробел (минимум, максимум, шаг)."

            min_val = float(parts[0])
            max_val = float(parts[1])
            step = float(parts[2])

            if min_val >= max_val:
                return None, "Минимум должен быть меньше максимума."

            if step <= 0:
                return None, "Шаг должен быть больше нуля."

            if step > (max_val - min_val):
                return None, "Шаг не может быть больше диапазона."

            return {'min': min_val, 'max': max_val, 'step': step}, None

    except ValueError:
        return None, "Некорректный формат. Проверьте что используете числа."

    return None, "Неизвестный тип вопроса."


async def cancel_add_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отменяет процесс добавления вопроса.
    """
    # Очищаем контекст
    for key in ['template_id', 'template_name', 'question_type', 'question_text']:
        context.user_data.pop(key, None)

    await update.message.reply_text(
        "❌ Добавление вопроса отменено."
    )

    return ConversationHandler.END


def register(application) -> None:
    """
    Регистрирует handlers для добавления вопросов.
    """
    # ConversationHandler для добавления вопроса
    add_question_conv = ConversationHandler(
        entry_points=[CommandHandler('add_question', add_question_start)],
        states={
            ADD_QUESTION_TYPE: [
                CallbackQueryHandler(select_question_type, pattern='^qtype_')
            ],
            ADD_QUESTION_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question_text)
            ],
            ADD_QUESTION_CONFIG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, configure_question)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_add_question)],
        name="add_question_conversation",
        persistent=False
    )

    application.add_handler(add_question_conv)

    logger.info("Survey question handlers зарегистрированы")
