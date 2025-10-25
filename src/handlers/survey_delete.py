"""
Handlers для удаления и активации пользовательских шаблонов (Phase 3.4).

Команды:
- /delete_survey <название> - удалить пользовательский опрос
- /activate_survey <название> - активировать опрос
- /deactivate_survey <название> - деактивировать опрос
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

from src.config import DELETE_SURVEY_CONFIRM
from src.data.storage import _get_db_connection
from src.data.surveys_storage import (
    get_user_templates,
    get_template_questions,
    delete_template,
    update_template
)

logger = logging.getLogger(__name__)


async def delete_survey_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Начало удаления опроса - /delete_survey <название>.
    Запрашивает подтверждение перед удалением.
    """
    chat_id = update.effective_chat.id

    # Проверяем что указано название шаблона
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название шаблона.\\n\\n"
            "Использование: /delete_survey <название>\\n\\n"
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
                f"❌ Шаблон *{template_name}* не найден.\\n\\n"
                f"Посмотреть свои шаблоны: /my_surveys",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        # Проверяем что это не системный шаблон
        if template.get('is_system', False):
            await update.message.reply_text(
                f"❌ Системный шаблон *{template_name}* нельзя удалить.\\n\\n"
                f"Системные шаблоны защищены от удаления.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        # Сохраняем данные в контекст
        context.user_data['template_id'] = template['id']
        context.user_data['template_name'] = template_name

        # Запрашиваем подтверждение
        questions = get_template_questions(conn, template['id'])

        await update.message.reply_text(
            f"⚠️ *Подтверждение удаления*\\n\\n"
            f"Вы уверены что хотите удалить опрос *{template_name}*?\\n\\n"
            f"❓ Вопросов в опросе: {len(questions)}\\n"
            f"{'✅' if template.get('is_active') else '⏸'} Статус: {'Активен' if template.get('is_active') else 'Неактивен'}\\n\\n"
            f"⚠️ *Внимание:* Будут удалены все вопросы и ответы по этому опросу!\\n\\n"
            f"Введите *да* для подтверждения или *нет* для отмены:",
            parse_mode='Markdown'
        )

        return DELETE_SURVEY_CONFIRM

    except Exception as e:
        logger.error(f"Ошибка при начале удаления опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже."
        )
        return ConversationHandler.END


async def confirm_delete_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Подтверждение удаления опроса.
    """
    chat_id = update.effective_chat.id
    confirmation = update.message.text.strip().lower()

    if confirmation not in ['да', 'yes', 'y']:
        await update.message.reply_text(
            "❌ Удаление отменено.\\n\\n"
            "Опрос сохранен."
        )
        context.user_data.clear()
        return ConversationHandler.END

    try:
        conn = _get_db_connection()
        template_id = context.user_data['template_id']
        template_name = context.user_data['template_name']

        # Удаляем шаблон
        success = delete_template(conn, template_id, chat_id)

        if success:
            await update.message.reply_text(
                f"✅ *Опрос удален!*\\n\\n"
                f"Опрос *{template_name}* и все связанные данные удалены.\\n\\n"
                f"Посмотреть оставшиеся опросы: /my_surveys\\n"
                f"Создать новый опрос: /create_survey",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось удалить опрос.\\n"
                "Возможно, вы не являетесь владельцем."
            )

        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка при удалении опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при удалении опроса."
        )
        context.user_data.clear()
        return ConversationHandler.END


async def activate_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Активация опроса - /activate_survey <название>.
    Проверяет наличие вопросов перед активацией.
    """
    chat_id = update.effective_chat.id

    # Проверяем что указано название шаблона
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название шаблона.\\n\\n"
            "Использование: /activate_survey <название>\\n\\n"
            "Посмотреть свои шаблоны: /my_surveys"
        )
        return

    template_name = ' '.join(context.args)

    try:
        conn = _get_db_connection()

        # Ищем шаблон пользователя
        templates = get_user_templates(conn, chat_id)
        template = next((t for t in templates if t['name'] == template_name), None)

        if not template:
            await update.message.reply_text(
                f"❌ Шаблон *{template_name}* не найден.\\n\\n"
                f"Посмотреть свои шаблоны: /my_surveys",
                parse_mode='Markdown'
            )
            return

        # Проверяем что опрос еще не активен
        if template.get('is_active', False):
            await update.message.reply_text(
                f"ℹ️ Опрос *{template_name}* уже активен.\\n\\n"
                f"Посмотреть свои опросы: /my_surveys",
                parse_mode='Markdown'
            )
            return

        # Проверяем наличие вопросов
        questions = get_template_questions(conn, template['id'])

        if not questions:
            await update.message.reply_text(
                f"❌ *Невозможно активировать опрос*\\n\\n"
                f"Опрос *{template_name}* не содержит вопросов.\\n\\n"
                f"Добавьте хотя бы один вопрос:\\n"
                f"/add_question {template_name}",
                parse_mode='Markdown'
            )
            return

        # Активируем опрос
        success = update_template(conn, template['id'], chat_id, is_active=True)

        if success:
            await update.message.reply_text(
                f"✅ *Опрос активирован!*\\n\\n"
                f"Опрос *{template_name}* теперь доступен для заполнения.\\n"
                f"❓ Вопросов: {len(questions)}\\n\\n"
                f"Деактивировать опрос: /deactivate_survey {template_name}\\n"
                f"Посмотреть все опросы: /my_surveys",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось активировать опрос."
            )

    except Exception as e:
        logger.error(f"Ошибка при активации опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при активации опроса."
        )


async def deactivate_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Деактивация опроса - /deactivate_survey <название>.
    """
    chat_id = update.effective_chat.id

    # Проверяем что указано название шаблона
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название шаблона.\\n\\n"
            "Использование: /deactivate_survey <название>\\n\\n"
            "Посмотреть свои шаблоны: /my_surveys"
        )
        return

    template_name = ' '.join(context.args)

    try:
        conn = _get_db_connection()

        # Ищем шаблон пользователя
        templates = get_user_templates(conn, chat_id)
        template = next((t for t in templates if t['name'] == template_name), None)

        if not template:
            await update.message.reply_text(
                f"❌ Шаблон *{template_name}* не найден.\\n\\n"
                f"Посмотреть свои шаблоны: /my_surveys",
                parse_mode='Markdown'
            )
            return

        # Проверяем что это не системный шаблон
        if template.get('is_system', False):
            await update.message.reply_text(
                f"❌ Системный шаблон *{template_name}* нельзя деактивировать.\\n\\n"
                f"Системные шаблоны всегда активны.",
                parse_mode='Markdown'
            )
            return

        # Проверяем что опрос активен
        if not template.get('is_active', False):
            await update.message.reply_text(
                f"ℹ️ Опрос *{template_name}* уже неактивен.\\n\\n"
                f"Посмотреть свои опросы: /my_surveys",
                parse_mode='Markdown'
            )
            return

        # Деактивируем опрос
        success = update_template(conn, template['id'], chat_id, is_active=False)

        if success:
            await update.message.reply_text(
                f"✅ *Опрос деактивирован!*\\n\\n"
                f"Опрос *{template_name}* больше не доступен для заполнения.\\n\\n"
                f"Активировать опрос: /activate_survey {template_name}\\n"
                f"Посмотреть все опросы: /my_surveys",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось деактивировать опрос."
            )

    except Exception as e:
        logger.error(f"Ошибка при деактивации опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при деактивации опроса."
        )


async def cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отменяет процесс удаления опроса.
    """
    context.user_data.clear()

    await update.message.reply_text(
        "❌ Удаление отменено."
    )

    return ConversationHandler.END


def register(application) -> None:
    """
    Регистрирует handlers для удаления и активации опросов.
    """
    # ConversationHandler для удаления опроса
    delete_survey_conv = ConversationHandler(
        entry_points=[CommandHandler('delete_survey', delete_survey_start)],
        states={
            DELETE_SURVEY_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete_survey)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_delete)],
        name="delete_survey_conversation",
        persistent=False
    )

    application.add_handler(delete_survey_conv)

    # Обычные команды
    application.add_handler(CommandHandler('activate_survey', activate_survey))
    application.add_handler(CommandHandler('deactivate_survey', deactivate_survey))

    logger.info("Survey delete and activation handlers зарегистрированы")
