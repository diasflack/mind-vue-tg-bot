"""
Модуль с обработчиками для заполнения опросов.
Реализует диалоговый процесс заполнения опросов с разными типами вопросов.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Tuple
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters, Application
)

from src.config import SURVEY_ANSWER
from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import _get_db_connection
from src.data.surveys_storage import (
    get_available_templates,
    get_template_by_name,
    get_template_questions,
    save_survey_response
)
from src.utils.conversation_manager import register_conversation, end_conversation

logger = logging.getLogger(__name__)

HANDLER_NAME = "survey_fill"


async def list_surveys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает список доступных опросов - команда /surveys.
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} запросил список опросов")

    conn = _get_db_connection()
    templates = get_available_templates(conn, only_active=True)

    if not templates:
        await update.message.reply_text(
            "📋 Нет доступных опросов.",
            reply_markup=MAIN_KEYBOARD
        )
        return

    message = "📋 Доступные опросы:\n\n"

    for template in templates:
        icon = template.get('icon', '📝')
        name = template['name']
        description = template.get('description', '')

        message += f"{icon} *{name}*\n"
        if description:
            message += f"_{description}_\n"
        message += f"Заполнить: `/fill {name}`\n\n"

    message += "\n💡 Для заполнения опроса используйте команду `/fill <название>`"

    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=MAIN_KEYBOARD
    )


async def start_fill_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает заполнение опроса - команда /fill <название>.
    """
    chat_id = update.effective_chat.id

    # Проверяем наличие аргументов
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название опроса.\n\n"
            "Пример: `/fill КПТ дневник`\n\n"
            "Посмотреть доступные опросы: /surveys",
            parse_mode='Markdown',
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    # Соединяем аргументы в название опроса
    survey_name = ' '.join(context.args)

    logger.info(f"Пользователь {chat_id} начинает заполнение опроса '{survey_name}'")

    # Получаем шаблон опроса
    conn = _get_db_connection()
    template = get_template_by_name(conn, survey_name)

    if not template:
        await update.message.reply_text(
            f"❌ Опрос '{survey_name}' не найден.\n\n"
            "Посмотреть доступные опросы: /surveys",
            parse_mode='Markdown',
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    # Получаем вопросы шаблона
    questions = get_template_questions(conn, template['id'])

    if not questions:
        await update.message.reply_text(
            f"❌ В опросе '{survey_name}' нет вопросов.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    # Регистрируем начало диалога
    register_conversation(chat_id, HANDLER_NAME, SURVEY_ANSWER)

    # Сохраняем данные в context
    context.user_data['survey'] = {
        'template_id': template['id'],
        'template_name': template['name'],
        'questions': questions,
        'current_question': 0,
        'answers': {}
    }

    # Задаем первый вопрос
    await _ask_question(update, context, 0)

    return SURVEY_ANSWER


async def _ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question_index: int):
    """
    Задает вопрос пользователю.
    """
    survey_data = context.user_data['survey']
    questions = survey_data['questions']

    if question_index >= len(questions):
        # Все вопросы пройдены - сохраняем ответы
        await _complete_survey(update, context)
        return

    question = questions[question_index]

    # Формируем сообщение с вопросом
    message = f"📝 Вопрос {question_index + 1} из {len(questions)}\n\n"
    message += f"*{question['question_text']}*\n\n"

    # Добавляем подсказку если есть
    if question.get('help_text'):
        message += f"💡 {question['help_text']}\n\n"

    # Добавляем инструкцию в зависимости от типа вопроса
    question_type = question['question_type']

    if question_type == 'numeric':
        config = json.loads(question['config']) if question.get('config') else {}
        min_val = config.get('min', 0)
        max_val = config.get('max', 100)
        message += f"Введите число от {min_val} до {max_val}"

    elif question_type == 'yes_no':
        message += "Ответьте: да / нет (или yes / no)"

    elif question_type == 'time':
        message += "Введите время в формате ЧЧ:ММ (например: 14:30)"

    elif question_type == 'choice':
        config = json.loads(question['config']) if question.get('config') else {}
        options = config.get('options', [])
        if options:
            message += "Выберите вариант:\n"
            for i, option in enumerate(options, 1):
                message += f"{i}. {option}\n"
            if config.get('multiple'):
                message += "\n(Можно выбрать несколько через запятую, например: 1,3,5)"

    elif question_type == 'text':
        message += "Введите ваш ответ"

    # Добавляем инфо про skip
    if not question['is_required']:
        message += "\n\n_Вопрос необязательный. Можете пропустить: /skip_"

    message += "\n\nОтменить заполнение: /cancel"

    await update.message.reply_text(message, parse_mode='Markdown')


async def handle_survey_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ответ на вопрос опроса.
    """
    chat_id = update.effective_chat.id
    text = update.message.text

    survey_data = context.user_data.get('survey')
    if not survey_data:
        await update.message.reply_text(
            "❌ Данные опроса не найдены. Начните заново: /surveys",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    current_index = survey_data['current_question']
    questions = survey_data['questions']
    question = questions[current_index]

    # Проверяем /skip
    if text == '/skip':
        if question['is_required']:
            await update.message.reply_text(
                "❌ Этот вопрос обязателен. Пожалуйста, ответьте на него.",
                parse_mode='Markdown'
            )
            return SURVEY_ANSWER
        else:
            # Пропускаем вопрос
            logger.info(f"Пользователь {chat_id} пропустил вопрос {question['id']}")
            survey_data['current_question'] += 1
            await _ask_question(update, context, survey_data['current_question'])
            return SURVEY_ANSWER

    # Валидируем ответ в зависимости от типа вопроса
    is_valid, error_message = _validate_answer(text, question)

    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_message}",
            parse_mode='Markdown'
        )
        return SURVEY_ANSWER

    # Сохраняем ответ
    survey_data['answers'][str(question['id'])] = text
    logger.info(f"Пользователь {chat_id} ответил на вопрос {question['id']}: {text}")

    # Переходим к следующему вопросу
    survey_data['current_question'] += 1

    if survey_data['current_question'] < len(questions):
        await _ask_question(update, context, survey_data['current_question'])
        return SURVEY_ANSWER
    else:
        # Все вопросы пройдены
        await _complete_survey(update, context)
        return ConversationHandler.END


def _validate_answer(text: str, question: Dict) -> Tuple[bool, str]:
    """
    Валидирует ответ на вопрос.

    Returns:
        (is_valid, error_message): кортеж с флагом валидности и сообщением об ошибке
    """
    question_type = question['question_type']

    if question_type == 'numeric':
        try:
            value = float(text)
            config = json.loads(question['config']) if question.get('config') else {}
            min_val = config.get('min', 0)
            max_val = config.get('max', 100)

            if value < min_val or value > max_val:
                return False, f"Число должно быть от {min_val} до {max_val}"

            return True, ""
        except ValueError:
            return False, "Пожалуйста, введите число"

    elif question_type == 'yes_no':
        normalized = text.lower().strip()
        if normalized not in ['да', 'нет', 'yes', 'no']:
            return False, "Пожалуйста, ответьте 'да' или 'нет' (или 'yes'/'no')"
        return True, ""

    elif question_type == 'time':
        # Проверяем формат времени ЧЧ:ММ
        import re
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', text):
            return False, "Пожалуйста, введите время в формате ЧЧ:ММ (например: 14:30)"
        return True, ""

    elif question_type == 'choice':
        config = json.loads(question['config']) if question.get('config') else {}
        options = config.get('options', [])

        if not options:
            return True, ""  # Если нет опций, принимаем любой ответ

        # Проверяем выбор по номеру
        try:
            # Поддерживаем множественный выбор через запятую
            choices = [c.strip() for c in text.split(',')]
            for choice in choices:
                choice_num = int(choice)
                if choice_num < 1 or choice_num > len(options):
                    return False, f"Выберите номер от 1 до {len(options)}"
            return True, ""
        except ValueError:
            # Если не число, проверяем текстовое совпадение
            if text in options:
                return True, ""
            return False, f"Выберите вариант из списка (номер от 1 до {len(options)})"

    elif question_type == 'text':
        if not text or len(text.strip()) == 0:
            return False, "Пожалуйста, введите ответ"
        return True, ""

    elif question_type == 'scale':
        # Scale работает как numeric
        return _validate_answer(text, {**question, 'question_type': 'numeric'})

    return True, ""


async def _complete_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Завершает опрос и сохраняет ответы.
    """
    chat_id = update.effective_chat.id
    survey_data = context.user_data['survey']

    # Формируем данные для сохранения
    now = datetime.now()
    response_data = {
        'chat_id': chat_id,
        'template_id': survey_data['template_id'],
        'response_date': now.strftime('%Y-%m-%d'),
        'response_time': now.strftime('%H:%M:%S'),
        'answers': survey_data['answers']
    }

    # Сохраняем в БД
    conn = _get_db_connection()
    success = save_survey_response(conn, response_data)

    if success:
        # Формируем резюме
        message = f"✅ Опрос *{survey_data['template_name']}* заполнен!\n\n"
        message += f"📅 {now.strftime('%d.%m.%Y')}\n"
        message += f"⏰ {now.strftime('%H:%M')}\n"
        message += f"📊 Ответов: {len(survey_data['answers'])}\n\n"
        message += "Спасибо за уделенное время! 🙏"

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=MAIN_KEYBOARD
        )

        logger.info(f"Опрос {survey_data['template_id']} успешно заполнен пользователем {chat_id}")
    else:
        await update.message.reply_text(
            "❌ Ошибка при сохранении ответов. Попробуйте позже.",
            reply_markup=MAIN_KEYBOARD
        )
        logger.error(f"Ошибка сохранения ответов опроса для пользователя {chat_id}")

    # Очищаем данные
    end_conversation(chat_id, HANDLER_NAME)
    if 'survey' in context.user_data:
        context.user_data.pop('survey')


async def cancel_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отменяет заполнение опроса.
    """
    chat_id = update.effective_chat.id
    logger.info(f"Отмена заполнения опроса для пользователя {chat_id}")

    # Завершаем диалог
    end_conversation(chat_id, HANDLER_NAME)

    # Очищаем данные
    if 'survey' in context.user_data:
        context.user_data.pop('survey')

    await update.message.reply_text(
        "Заполнение опроса отменено.",
        reply_markup=MAIN_KEYBOARD
    )

    return ConversationHandler.END


# Создание ConversationHandler
survey_conversation_handler = ConversationHandler(
    entry_points=[
        CommandHandler('fill', start_fill_survey)
    ],
    states={
        SURVEY_ANSWER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_survey_answer)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', cancel_survey)
    ],
    name=HANDLER_NAME
)


def register(application: Application):
    """
    Регистрирует обработчики опросов в приложении.
    """
    application.add_handler(CommandHandler('surveys', list_surveys))
    application.add_handler(survey_conversation_handler)
