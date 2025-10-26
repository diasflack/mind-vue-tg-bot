"""
Handlers для редактирования пользовательских шаблонов опросов (Phase 3.3).

Команды:
- /edit_survey <название> - редактировать опрос
- /edit_question <название_шаблона> <номер_вопроса> - редактировать вопрос
- /delete_question <название_шаблона> <номер_вопроса> - удалить вопрос
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from src.config import EDIT_SURVEY_SELECT, EDIT_QUESTION_SELECT
from src.data.storage import _get_db_connection
from src.data.surveys_storage import (
    get_user_templates,
    get_template_questions,
    update_template,
    update_question,
    delete_question
)

logger = logging.getLogger(__name__)

# Константы
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 500
MIN_QUESTION_LENGTH = 10
MAX_QUESTION_LENGTH = 500


async def edit_survey_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Начало редактирования опроса - /edit_survey <название>.
    Проверяет владельца и показывает меню редактирования.
    """
    chat_id = update.effective_chat.id

    # Проверяем что указано название шаблона
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название шаблона.\\n\\n"
            "Использование: /edit_survey <название>\\n\\n"
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
                f"❌ Системный шаблон *{template_name}* нельзя редактировать.\\n\\n"
                f"Вы можете создать собственный шаблон: /create_survey",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        # Сохраняем данные в контекст
        context.user_data['template_id'] = template['id']
        context.user_data['template_name'] = template_name

        # Показываем меню редактирования
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить название", callback_data="edit_name")],
            [InlineKeyboardButton("📝 Изменить описание", callback_data="edit_desc")],
            [InlineKeyboardButton("❓ Редактировать вопросы", callback_data="edit_questions")],
            [InlineKeyboardButton("❌ Отмена", callback_data="edit_cancel")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        questions = get_template_questions(conn, template['id'])

        await update.message.reply_text(
            f"✏️ *Редактирование '{template_name}'*\\n\\n"
            f"📄 Описание: {template['description']}\\n"
            f"❓ Вопросов: {len(questions)}\\n"
            f"{'✅' if template['is_active'] else '⏸'} Статус: {'Активен' if template['is_active'] else 'Неактивен'}\\n\\n"
            f"Выберите что хотите изменить:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        return EDIT_SURVEY_SELECT

    except Exception as e:
        logger.error(f"Ошибка при начале редактирования опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже."
        )
        return ConversationHandler.END


async def handle_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработка выбора пункта меню редактирования.
    """
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "edit_cancel":
        await query.edit_message_text("❌ Редактирование отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    elif action == "edit_name":
        await query.edit_message_text(
            f"✏️ *Изменение названия*\\n\\n"
            f"Текущее название: *{context.user_data['template_name']}*\\n\\n"
            f"Введите новое название ({MIN_NAME_LENGTH}-{MAX_NAME_LENGTH} символов):\\n\\n"
            f"_Для отмены используйте /cancel_",
            parse_mode='Markdown'
        )
        context.user_data['edit_action'] = 'name'
        return EDIT_SURVEY_SELECT

    elif action == "edit_desc":
        await query.edit_message_text(
            f"📝 *Изменение описания*\\n\\n"
            f"Введите новое описание (до {MAX_DESCRIPTION_LENGTH} символов):\\n\\n"
            f"_Для отмены используйте /cancel_",
            parse_mode='Markdown'
        )
        context.user_data['edit_action'] = 'description'
        return EDIT_SURVEY_SELECT

    elif action == "edit_questions":
        # Показываем список вопросов для редактирования
        try:
            conn = _get_db_connection()
            template_id = context.user_data['template_id']
            questions = get_template_questions(conn, template_id)

            if not questions:
                await query.edit_message_text(
                    "❓ В шаблоне пока нет вопросов.\\n\\n"
                    f"Добавить вопрос: /add_question {context.user_data['template_name']}"
                )
                return ConversationHandler.END

            keyboard = []
            for i, q in enumerate(questions, 1):
                text = q['question_text']
                if len(text) > 40:
                    text = text[:37] + "..."
                keyboard.append([
                    InlineKeyboardButton(f"{i}. {text}", callback_data=f"editq_{q['id']}")
                ])

            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="edit_cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"❓ *Вопросы в '{context.user_data['template_name']}'*\\n\\n"
                f"Выберите вопрос для редактирования:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            return EDIT_QUESTION_SELECT

        except Exception as e:
            logger.error(f"Ошибка при получении списка вопросов: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
            return ConversationHandler.END

    return EDIT_SURVEY_SELECT


async def edit_survey_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Изменение названия опроса.
    """
    chat_id = update.effective_chat.id
    new_name = update.message.text.strip()

    # Валидация длины
    if len(new_name) < MIN_NAME_LENGTH:
        await update.message.reply_text(
            f"❌ Название слишком короткое.\\n"
            f"Минимум {MIN_NAME_LENGTH} символа."
        )
        return EDIT_SURVEY_SELECT

    if len(new_name) > MAX_NAME_LENGTH:
        await update.message.reply_text(
            f"❌ Название слишком длинное.\\n"
            f"Максимум {MAX_NAME_LENGTH} символов."
        )
        return EDIT_SURVEY_SELECT

    try:
        conn = _get_db_connection()
        template_id = context.user_data['template_id']

        # Проверяем уникальность нового названия
        existing = get_user_templates(conn, chat_id)
        if any(t['name'] == new_name and t['id'] != template_id for t in existing):
            await update.message.reply_text(
                f"❌ Опрос с названием *{new_name}* уже существует.\\n\\n"
                f"Выберите другое название.",
                parse_mode='Markdown'
            )
            return EDIT_SURVEY_SELECT

        # Обновляем название
        success = update_template(conn, template_id, chat_id, name=new_name)

        if success:
            await update.message.reply_text(
                f"✅ *Название обновлено!*\\n\\n"
                f"Новое название: {new_name}\\n\\n"
                f"Посмотреть опрос: /my_surveys",
                parse_mode='Markdown'
            )
            context.user_data.clear()
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ Не удалось обновить название.\\n"
                "Попробуйте позже."
            )
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка при обновлении названия опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обновлении названия."
        )
        return ConversationHandler.END


async def edit_survey_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Изменение описания опроса.
    """
    chat_id = update.effective_chat.id
    new_description = update.message.text.strip()

    # Валидация длины
    if len(new_description) > MAX_DESCRIPTION_LENGTH:
        await update.message.reply_text(
            f"❌ Описание слишком длинное.\\n"
            f"Максимум {MAX_DESCRIPTION_LENGTH} символов."
        )
        return EDIT_SURVEY_SELECT

    try:
        conn = _get_db_connection()
        template_id = context.user_data['template_id']

        # Обновляем описание
        success = update_template(conn, template_id, chat_id, description=new_description)

        if success:
            await update.message.reply_text(
                f"✅ *Описание обновлено!*\\n\\n"
                f"Новое описание: {new_description}\\n\\n"
                f"Посмотреть опрос: /my_surveys",
                parse_mode='Markdown'
            )
            context.user_data.clear()
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ Не удалось обновить описание."
            )
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка при обновлении описания опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обновлении описания."
        )
        return ConversationHandler.END


async def handle_question_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработка выбора вопроса для редактирования.
    """
    query = update.callback_query
    await query.answer()

    if query.data == "edit_cancel":
        await query.edit_message_text("❌ Редактирование отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    # Извлекаем ID вопроса
    question_id = int(query.data.replace("editq_", ""))
    context.user_data['question_id'] = question_id

    # Показываем меню редактирования вопроса
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить текст", callback_data="editq_text")],
        [InlineKeyboardButton("🗑 Удалить вопрос", callback_data="editq_delete")],
        [InlineKeyboardButton("❌ Отмена", callback_data="edit_cancel")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✏️ *Редактирование вопроса*\\n\\n"
        f"Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    return EDIT_QUESTION_SELECT


async def handle_question_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработка действия с вопросом.
    """
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "edit_cancel":
        await query.edit_message_text("❌ Редактирование отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    elif action == "editq_text":
        await query.edit_message_text(
            f"✏️ *Изменение текста вопроса*\\n\\n"
            f"Введите новый текст вопроса ({MIN_QUESTION_LENGTH}-{MAX_QUESTION_LENGTH} символов):\\n\\n"
            f"_Для отмены используйте /cancel_",
            parse_mode='Markdown'
        )
        context.user_data['question_action'] = 'text'
        return EDIT_QUESTION_SELECT

    elif action == "editq_delete":
        # Сразу удаляем вопрос (без дополнительного подтверждения)
        return await delete_question_confirm(update, context)

    return EDIT_QUESTION_SELECT


async def edit_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Изменение текста вопроса.
    """
    chat_id = update.effective_chat.id
    new_text = update.message.text.strip()

    # Валидация длины
    if len(new_text) < MIN_QUESTION_LENGTH:
        await update.message.reply_text(
            f"❌ Текст вопроса слишком короткий.\\n"
            f"Минимум {MIN_QUESTION_LENGTH} символов."
        )
        return EDIT_QUESTION_SELECT

    if len(new_text) > MAX_QUESTION_LENGTH:
        await update.message.reply_text(
            f"❌ Текст вопроса слишком длинный.\\n"
            f"Максимум {MAX_QUESTION_LENGTH} символов."
        )
        return EDIT_QUESTION_SELECT

    try:
        conn = _get_db_connection()
        template_id = context.user_data['template_id']
        question_id = context.user_data['question_id']

        # Обновляем текст вопроса
        success = update_question(conn, question_id, template_id, chat_id, question_text=new_text)

        if success:
            await update.message.reply_text(
                f"✅ *Текст вопроса обновлен!*\\n\\n"
                f"Новый текст: {new_text}\\n\\n"
                f"Посмотреть все вопросы: /my_surveys",
                parse_mode='Markdown'
            )
            context.user_data.clear()
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ Не удалось обновить текст вопроса."
            )
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка при обновлении текста вопроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обновлении вопроса."
        )
        return ConversationHandler.END


async def delete_question_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Удаление вопроса из шаблона.
    """
    chat_id = update.effective_chat.id

    try:
        conn = _get_db_connection()
        template_id = context.user_data['template_id']
        question_id = context.user_data['question_id']

        # Удаляем вопрос
        success = delete_question(conn, question_id, template_id, chat_id)

        if success:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    f"✅ *Вопрос удален!*\\n\\n"
                    f"Посмотреть оставшиеся вопросы: /my_surveys",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"✅ *Вопрос удален!*\\n\\n"
                    f"Посмотреть оставшиеся вопросы: /my_surveys",
                    parse_mode='Markdown'
                )
            context.user_data.clear()
            return ConversationHandler.END
        else:
            message = "❌ Не удалось удалить вопрос."
            if update.callback_query:
                await update.callback_query.edit_message_text(message)
            else:
                await update.message.reply_text(message)
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка при удалении вопроса: {e}")
        message = "❌ Произошла ошибка при удалении вопроса."
        if update.callback_query:
            await update.callback_query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return ConversationHandler.END


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отменяет процесс редактирования.
    """
    context.user_data.clear()

    await update.message.reply_text(
        "❌ Редактирование отменено."
    )

    return ConversationHandler.END


def register(application) -> None:
    """
    Регистрирует handlers для редактирования опросов.
    """
    # ConversationHandler для редактирования опроса
    edit_survey_conv = ConversationHandler(
        entry_points=[CommandHandler('edit_survey', edit_survey_start)],
        states={
            EDIT_SURVEY_SELECT: [
                CallbackQueryHandler(handle_edit_menu, pattern='^edit_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: (
                    edit_survey_name(update, context)
                    if context.user_data.get('edit_action') == 'name'
                    else edit_survey_description(update, context)
                ))
            ],
            EDIT_QUESTION_SELECT: [
                CallbackQueryHandler(handle_question_select, pattern='^editq_\\d+$'),
                CallbackQueryHandler(handle_question_action, pattern='^editq_(text|delete)$'),
                CallbackQueryHandler(handle_edit_menu, pattern='^edit_cancel$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: (
                    edit_question_text(update, context)
                    if context.user_data.get('question_action') == 'text'
                    else ConversationHandler.END
                ))
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_edit)],
        name="edit_survey_conversation",
        persistent=False
    )

    application.add_handler(edit_survey_conv)

    logger.info("Survey edit handlers зарегистрированы")
