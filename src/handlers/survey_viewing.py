"""
Модуль с обработчиками для просмотра ответов на опросы.
Реализует команды для отображения заполненных опросов.
"""

import logging
from typing import Dict, Any, List
from telegram import Update
from telegram.ext import ContextTypes, Application, CommandHandler

from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import _get_db_connection
from src.data.surveys_storage import (
    get_user_survey_responses,
    get_responses_by_template,
    get_template_by_id,
    get_template_by_name,
    get_template_questions
)

logger = logging.getLogger(__name__)

# Максимальное количество ответов в одном сообщении
MAX_RESPONSES_PER_MESSAGE = 10


def _format_response_summary(response: Dict[str, Any], template: Dict[str, Any]) -> str:
    """
    Форматирует краткую информацию об ответе.

    Args:
        response: Данные ответа
        template: Данные шаблона

    Returns:
        str: Отформатированная строка
    """
    icon = template.get('icon', '📝')
    name = template['name']
    date = response['response_date']
    time = response['response_time']

    # Форматируем дату в более читаемый вид
    try:
        year, month, day = date.split('-')
        formatted_date = f"{day}.{month}.{year}"
    except:
        formatted_date = date

    # Форматируем время (убираем секунды)
    formatted_time = time.rsplit(':', 1)[0] if ':' in time else time

    # Количество ответов
    answer_count = len(response.get('answers', {}))

    summary = f"{icon} *{name}*\n"
    summary += f"📅 {formatted_date} ⏰ {formatted_time}\n"
    summary += f"📊 Ответов: {answer_count}\n"
    summary += f"ID: `{response['id']}`"

    return summary


def _format_detailed_response(
    response: Dict[str, Any],
    template: Dict[str, Any],
    questions: List[Dict[str, Any]]
) -> str:
    """
    Форматирует детальную информацию об ответе с вопросами.

    Args:
        response: Данные ответа
        template: Данные шаблона
        questions: Список вопросов шаблона

    Returns:
        str: Отформатированная строка
    """
    icon = template.get('icon', '📝')
    name = template['name']
    date = response['response_date']
    time = response['response_time']
    answers = response.get('answers', {})

    # Форматируем дату
    try:
        year, month, day = date.split('-')
        formatted_date = f"{day}.{month}.{year}"
    except:
        formatted_date = date

    formatted_time = time.rsplit(':', 1)[0] if ':' in time else time

    message = f"{icon} *{name}*\n"
    message += f"📅 {formatted_date} ⏰ {formatted_time}\n"
    message += f"━━━━━━━━━━━━━━━━\n\n"

    # Добавляем вопросы и ответы
    for question in questions:
        question_id = str(question['id'])
        if question_id in answers:
            answer = answers[question_id]
            message += f"❓ *{question['question_text']}*\n"
            message += f"💬 {answer}\n\n"

    return message


async def show_my_responses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает все ответы пользователя на опросы - команда /my_responses.
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} запросил свои ответы на опросы")

    conn = _get_db_connection()
    responses = get_user_survey_responses(conn, chat_id)

    if not responses:
        await update.message.reply_text(
            "📋 У вас пока нет заполненных опросов.\n\n"
            "Посмотреть доступные опросы: /surveys\n"
            "Заполнить опрос: `/fill <название>`",
            parse_mode='Markdown',
            reply_markup=MAIN_KEYBOARD
        )
        return

    # Группируем ответы по шаблонам для лучшего отображения
    template_cache = {}
    grouped = {}

    for response in responses:
        template_id = response['template_id']

        # Кешируем шаблоны чтобы не загружать каждый раз
        if template_id not in template_cache:
            template_cache[template_id] = get_template_by_id(conn, template_id)

        if template_id not in grouped:
            grouped[template_id] = []
        grouped[template_id].append(response)

    # Формируем сообщение
    message = f"📋 *Ваши ответы на опросы*\n"
    message += f"Всего ответов: {len(responses)}\n\n"
    message += "━━━━━━━━━━━━━━━━\n\n"

    count = 0
    for template_id, template_responses in grouped.items():
        template = template_cache[template_id]
        if not template:
            continue

        icon = template.get('icon', '📝')
        name = template['name']

        message += f"{icon} *{name}*\n"
        message += f"Заполнено раз: {len(template_responses)}\n\n"

        # Показываем последние несколько ответов
        for response in template_responses[:3]:  # Только последние 3
            date = response['response_date']
            try:
                year, month, day = date.split('-')
                formatted_date = f"{day}.{month}.{year}"
            except:
                formatted_date = date

            time = response['response_time'].rsplit(':', 1)[0]
            message += f"  • {formatted_date} {time} (ID: `{response['id']}`)\n"

        if len(template_responses) > 3:
            message += f"  _...и еще {len(template_responses) - 3}_\n"

        message += "\n"

        count += len(template_responses)

        # Ограничиваем размер сообщения
        if len(message) > 3500:
            break

    message += f"\n💡 Для просмотра ответов по конкретному опросу:\n"
    message += "`/survey_responses <название>`"

    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=MAIN_KEYBOARD
    )


async def show_survey_responses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает ответы пользователя на конкретный опрос - команда /survey_responses <название>.
    """
    chat_id = update.effective_chat.id

    # Проверяем наличие аргументов
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название опроса.\n\n"
            "Пример: `/survey_responses КПТ дневник`\n\n"
            "Посмотреть все ответы: /my_responses",
            parse_mode='Markdown',
            reply_markup=MAIN_KEYBOARD
        )
        return

    # Соединяем аргументы в название опроса
    survey_name = ' '.join(context.args)

    logger.info(f"Пользователь {chat_id} запросил ответы на опрос '{survey_name}'")

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
        return

    # Получаем ответы пользователя на этот опрос
    responses = get_responses_by_template(conn, chat_id, template['id'])

    if not responses:
        await update.message.reply_text(
            f"📋 Вы еще не заполняли опрос *{survey_name}*.\n\n"
            f"Заполнить: `/fill {survey_name}`",
            parse_mode='Markdown',
            reply_markup=MAIN_KEYBOARD
        )
        return

    # Получаем вопросы шаблона
    questions = get_template_questions(conn, template['id'])

    # Формируем сообщение с детальными ответами
    icon = template.get('icon', '📝')
    message = f"{icon} *{survey_name}*\n"
    message += f"Заполнено раз: {len(responses)}\n"
    message += "━━━━━━━━━━━━━━━━\n\n"

    # Показываем последние ответы (с ограничением)
    for i, response in enumerate(responses[:MAX_RESPONSES_PER_MESSAGE], 1):
        date = response['response_date']
        try:
            year, month, day = date.split('-')
            formatted_date = f"{day}.{month}.{year}"
        except:
            formatted_date = date

        time = response['response_time'].rsplit(':', 1)[0]

        message += f"*Ответ #{i}* (ID: `{response['id']}`)\n"
        message += f"📅 {formatted_date} ⏰ {time}\n\n"

        # Показываем вопросы и ответы
        answers = response.get('answers', {})
        for question in questions:
            question_id = str(question['id'])
            if question_id in answers:
                answer = answers[question_id]
                q_text = question['question_text']

                # Сокращаем длинные вопросы
                if len(q_text) > 50:
                    q_text = q_text[:47] + "..."

                message += f"❓ {q_text}\n"

                # Сокращаем длинные ответы
                if len(answer) > 100:
                    answer = answer[:97] + "..."

                message += f"💬 {answer}\n\n"

        message += "━━━━━━━━━━━━━━━━\n\n"

        # Ограничиваем размер сообщения
        if len(message) > 3500:
            # Отправляем текущее сообщение
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            message = f"{icon} *{survey_name}* (продолжение)\n\n"

    # Отправляем последнее сообщение
    if len(message) > 50:
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=MAIN_KEYBOARD
        )

    if len(responses) > MAX_RESPONSES_PER_MESSAGE:
        await update.message.reply_text(
            f"Показаны последние {MAX_RESPONSES_PER_MESSAGE} ответов из {len(responses)}.",
            reply_markup=MAIN_KEYBOARD
        )

    logger.info(f"Показано {min(len(responses), MAX_RESPONSES_PER_MESSAGE)} ответов для пользователя {chat_id}")


def register(application: Application):
    """
    Регистрирует обработчики просмотра ответов в приложении.
    """
    application.add_handler(CommandHandler('my_responses', show_my_responses))
    application.add_handler(CommandHandler('survey_responses', show_survey_responses))
