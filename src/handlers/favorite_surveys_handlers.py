"""
Обработчики команд для управления избранными опросами (Phase 5.3).

Команды:
- /favorite_surveys - список избранных опросов
- /add_favorite <название> - добавить опрос в избранное
- /remove_favorite <название> - удалить из избранного
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

from src.data.storage import _get_db_connection
from src.data.favorite_surveys_storage import (
    add_to_favorites,
    remove_from_favorites,
    get_favorite_surveys,
    is_favorite
)
from src.data.surveys_storage import get_template_by_name

logger = logging.getLogger(__name__)


async def favorite_surveys_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отображает список избранных опросов.

    Команда: /favorite_surveys
    """
    chat_id = update.effective_chat.id
    conn = _get_db_connection()

    try:
        favorites = get_favorite_surveys(conn, chat_id)

        if not favorites:
            await update.message.reply_text(
                "У вас пока нет избранных опросов.\n\n"
                "Используйте /add_favorite <название>, чтобы добавить опрос в избранное."
            )
            return

        # Формируем список избранных
        message_lines = ["⭐ *Избранные опросы:*\n"]

        for idx, survey in enumerate(favorites, 1):
            survey_name = survey['survey_name']
            description = survey.get('description', '')
            is_system = survey.get('is_system', 0)

            system_mark = " (системный)" if is_system else ""
            message_lines.append(f"{idx}. *{survey_name}*{system_mark}")

            if description:
                message_lines.append(f"   _{description}_")

            message_lines.append("")

        message_lines.append("\n💡 Используйте /remove_favorite <название>, чтобы удалить из избранного.")

        await update.message.reply_text(
            "\n".join(message_lines),
            parse_mode='Markdown'
        )
        logger.info(f"Пользователь {chat_id} просмотрел избранные опросы ({len(favorites)} шт.)")

    except Exception as e:
        logger.error(f"Ошибка при отображении избранных опросов для {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при получении списка избранных опросов."
        )
    finally:
        conn.close()


async def add_favorite_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Добавляет опрос в избранное.

    Команда: /add_favorite <название>
    """
    chat_id = update.effective_chat.id

    # Проверяем аргументы
    if not context.args:
        await update.message.reply_text(
            "❌ Неверное использование команды.\n\n"
            "Использование: /add_favorite <название опроса>\n"
            "Пример: /add_favorite Настроение"
        )
        return

    survey_name = ' '.join(context.args)
    conn = _get_db_connection()

    try:
        # Получаем опрос по имени
        template = get_template_by_name(conn, survey_name)

        if not template:
            await update.message.reply_text(
                f"❌ Опрос '{survey_name}' не найден.\n\n"
                "Используйте /surveys для просмотра доступных опросов."
            )
            return

        template_id = template['id']

        # Проверяем, может быть уже в избранном
        if is_favorite(conn, chat_id, template_id):
            await update.message.reply_text(
                f"ℹ️ Опрос '{survey_name}' уже в избранном."
            )
            return

        # Добавляем в избранное
        result = add_to_favorites(conn, chat_id, template_id)

        if result:
            await update.message.reply_text(
                f"✅ Опрос '{survey_name}' добавлен в избранное!\n\n"
                "Используйте /favorite_surveys для просмотра всех избранных опросов."
            )
            logger.info(f"Пользователь {chat_id} добавил опрос '{survey_name}' в избранное")
        else:
            await update.message.reply_text(
                f"❌ Не удалось добавить опрос '{survey_name}' в избранное."
            )

    except Exception as e:
        logger.error(f"Ошибка при добавлении опроса в избранное для {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при добавлении опроса в избранное."
        )
    finally:
        conn.close()


async def remove_favorite_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Удаляет опрос из избранного.

    Команда: /remove_favorite <название>
    """
    chat_id = update.effective_chat.id

    # Проверяем аргументы
    if not context.args:
        await update.message.reply_text(
            "❌ Неверное использование команды.\n\n"
            "Использование: /remove_favorite <название опроса>\n"
            "Пример: /remove_favorite Настроение"
        )
        return

    survey_name = ' '.join(context.args)
    conn = _get_db_connection()

    try:
        # Получаем опрос по имени
        template = get_template_by_name(conn, survey_name)

        if not template:
            await update.message.reply_text(
                f"❌ Опрос '{survey_name}' не найден.\n\n"
                "Используйте /surveys для просмотра доступных опросов."
            )
            return

        template_id = template['id']

        # Удаляем из избранного
        result = remove_from_favorites(conn, chat_id, template_id)

        if result:
            await update.message.reply_text(
                f"✅ Опрос '{survey_name}' удален из избранного."
            )
            logger.info(f"Пользователь {chat_id} удалил опрос '{survey_name}' из избранного")
        else:
            await update.message.reply_text(
                f"ℹ️ Опрос '{survey_name}' не был в избранном."
            )

    except Exception as e:
        logger.error(f"Ошибка при удалении опроса из избранного для {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при удалении опроса из избранного."
        )
    finally:
        conn.close()


def register(application: Application) -> None:
    """Регистрирует handlers в приложении."""
    application.add_handler(CommandHandler('favorite_surveys', favorite_surveys_handler))
    application.add_handler(CommandHandler('add_favorite', add_favorite_handler))
    application.add_handler(CommandHandler('remove_favorite', remove_favorite_handler))

    logger.info("Зарегистрированы handlers для избранных опросов")
