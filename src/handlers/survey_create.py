"""
Handlers для создания пользовательских шаблонов опросов (Phase 3.1).

Команды:
- /create_survey - начать создание нового опроса
- /my_surveys - показать список пользовательских опросов
"""

import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)

from src.config import CREATE_SURVEY_NAME, CREATE_SURVEY_DESC
from src.data.storage import _get_db_connection
from src.data.surveys_storage import (
    create_user_template,
    get_user_templates,
    count_user_templates,
    get_template_questions
)

logger = logging.getLogger(__name__)

# Константы
MAX_TEMPLATES = 20
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 500


async def create_survey_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Начало создания нового опроса - /create_survey.
    Проверяет лимит и запрашивает название.
    """
    chat_id = update.effective_chat.id

    try:
        conn = _get_db_connection()

        # Проверяем лимит (максимум 20 пользовательских шаблонов)
        count = count_user_templates(conn, chat_id)

        if count >= MAX_TEMPLATES:
            await update.message.reply_text(
                f"❌ Вы достигли лимита пользовательских опросов ({MAX_TEMPLATES}).\n\n"
                f"Удалите ненужные опросы с помощью /delete_survey, чтобы создать новые."
            )
            return ConversationHandler.END

        # Запрашиваем название
        await update.message.reply_text(
            f"📝 *Создание нового опроса*\n\n"
            f"У вас {count}/{MAX_TEMPLATES} опросов.\n\n"
            f"Введите название опроса ({MIN_NAME_LENGTH}-{MAX_NAME_LENGTH} символов):\n\n"
            f"_Для отмены используйте /cancel_",
            parse_mode='Markdown'
        )

        return CREATE_SURVEY_NAME

    except Exception as e:
        logger.error(f"Ошибка при начале создания опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при проверке лимита опросов.\n"
            "Попробуйте позже."
        )
        return ConversationHandler.END


async def receive_survey_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получает название опроса и валидирует его.
    """
    chat_id = update.effective_chat.id
    name = update.message.text.strip()

    # Валидация длины
    if len(name) < MIN_NAME_LENGTH:
        await update.message.reply_text(
            f"❌ Название слишком короткое.\n"
            f"Минимум {MIN_NAME_LENGTH} символа."
        )
        return CREATE_SURVEY_NAME

    if len(name) > MAX_NAME_LENGTH:
        await update.message.reply_text(
            f"❌ Название слишком длинное.\n"
            f"Максимум {MAX_NAME_LENGTH} символов."
        )
        return CREATE_SURVEY_NAME

    try:
        conn = _get_db_connection()

        # Проверяем уникальность названия
        existing = get_user_templates(conn, chat_id)
        if any(t['name'] == name for t in existing):
            await update.message.reply_text(
                f"❌ Опрос с названием *{name}* уже существует.\n\n"
                f"Выберите другое название.",
                parse_mode='Markdown'
            )
            return CREATE_SURVEY_NAME

        # Сохраняем название в контекст
        context.user_data['survey_name'] = name

        # Запрашиваем описание
        await update.message.reply_text(
            f"✅ Название: *{name}*\n\n"
            f"Теперь введите описание опроса (до {MAX_DESCRIPTION_LENGTH} символов):\n\n"
            f"_Для отмены используйте /cancel_",
            parse_mode='Markdown'
        )

        return CREATE_SURVEY_DESC

    except Exception as e:
        logger.error(f"Ошибка при проверке названия опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при проверке названия.\n"
            "Попробуйте позже."
        )
        return ConversationHandler.END


async def receive_survey_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получает описание опроса и создает шаблон в БД.
    """
    chat_id = update.effective_chat.id
    description = update.message.text.strip()

    # Проверяем что есть название в контексте
    if 'survey_name' not in context.user_data:
        logger.error("Отсутствует survey_name в context.user_data")
        await update.message.reply_text(
            "❌ Произошла ошибка. Начните создание заново с /create_survey"
        )
        return ConversationHandler.END

    name = context.user_data['survey_name']

    # Валидация длины описания
    if len(description) > MAX_DESCRIPTION_LENGTH:
        await update.message.reply_text(
            f"❌ Описание слишком длинное.\n"
            f"Максимум {MAX_DESCRIPTION_LENGTH} символов."
        )
        return CREATE_SURVEY_DESC

    try:
        conn = _get_db_connection()

        # Создаем шаблон
        template_id = create_user_template(conn, chat_id, name, description)

        if template_id is None:
            await update.message.reply_text(
                "❌ Не удалось создать опрос.\n"
                "Возможно, название уже занято или достигнут лимит."
            )
            return ConversationHandler.END

        # Успешное создание
        await update.message.reply_text(
            f"✅ *Опрос создан!*\n\n"
            f"📝 Название: {name}\n"
            f"📄 Описание: {description}\n\n"
            f"Шаблон создан, но пока *неактивен*.\n\n"
            f"Чтобы добавить вопросы, используйте:\n"
            f"/add_question {name}\n\n"
            f"Чтобы активировать опрос после добавления вопросов:\n"
            f"/activate_survey {name}\n\n"
            f"Просмотр всех ваших опросов: /my_surveys",
            parse_mode='Markdown'
        )

        # Очищаем контекст
        context.user_data.pop('survey_name', None)

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка при создании шаблона опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при создании опроса.\n"
            "Попробуйте позже."
        )
        return ConversationHandler.END


async def show_my_surveys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает список пользовательских опросов - /my_surveys.
    Группирует по активным/неактивным, показывает количество вопросов.
    """
    chat_id = update.effective_chat.id

    try:
        conn = _get_db_connection()

        # Получаем все шаблоны пользователя
        templates = get_user_templates(conn, chat_id)

        if not templates:
            await update.message.reply_text(
                "📝 У вас пока нет пользовательских опросов.\n\n"
                "Создайте первый опрос с помощью /create_survey"
            )
            return

        # Группируем по активным/неактивным
        active_templates = [t for t in templates if t['is_active']]
        inactive_templates = [t for t in templates if not t['is_active']]

        message_parts = [f"📋 *Ваши опросы ({len(templates)}/{MAX_TEMPLATES}):*\n"]

        # Активные опросы
        if active_templates:
            message_parts.append("\n✅ *Активные:*")
            for template in active_templates:
                questions = get_template_questions(conn, template['id'])
                question_count = len(questions)

                message_parts.append(
                    f"\n• *{template['name']}*"
                    f"\n  📄 {template['description']}"
                    f"\n  ❓ Вопросов: {question_count}"
                )

        # Неактивные опросы
        if inactive_templates:
            message_parts.append("\n\n⏸ *Неактивные:*")
            for template in inactive_templates:
                questions = get_template_questions(conn, template['id'])
                question_count = len(questions)

                message_parts.append(
                    f"\n• *{template['name']}*"
                    f"\n  📄 {template['description']}"
                    f"\n  ❓ Вопросов: {question_count}"
                )

        message_parts.append(
            "\n\n_Управление опросами:_\n"
            "/edit_survey <название> - редактировать\n"
            "/delete_survey <название> - удалить\n"
            "/activate_survey <название> - активировать\n"
            "/deactivate_survey <название> - деактивировать"
        )

        await update.message.reply_text(
            '\n'.join(message_parts),
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Ошибка при получении списка опросов: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при загрузке списка опросов.\n"
            "Попробуйте позже."
        )


async def cancel_create_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отменяет процесс создания опроса.
    """
    # Очищаем контекст
    context.user_data.pop('survey_name', None)

    await update.message.reply_text(
        "❌ Создание опроса отменено."
    )

    return ConversationHandler.END


def register(application) -> None:
    """
    Регистрирует handlers для создания опросов.
    """
    # ConversationHandler для создания опроса
    create_survey_conv = ConversationHandler(
        entry_points=[CommandHandler('create_survey', create_survey_start)],
        states={
            CREATE_SURVEY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_survey_name)
            ],
            CREATE_SURVEY_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_survey_description)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_create_survey)],
        name="create_survey_conversation",
        persistent=False
    )

    application.add_handler(create_survey_conv)

    # Обычные команды
    application.add_handler(CommandHandler('my_surveys', show_my_surveys))

    logger.info("Survey creation handlers зарегистрированы")
