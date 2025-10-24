"""
Модуль с обработчиками для добавления впечатлений.
Реализует диалоговый процесс ввода впечатления.
"""

import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters, Application
)

from src.config import (
    IMPRESSION_TEXT, IMPRESSION_INTENSITY,
    IMPRESSION_CATEGORY, IMPRESSION_TAGS
)
from src.utils.keyboards import NUMERIC_KEYBOARD, MAIN_KEYBOARD
from src.data.storage import save_user, _get_db_connection
from src.data.impressions_storage import (
    save_impression, create_tag, attach_tags_to_impression
)
from src.data.models import IMPRESSION_CATEGORIES
from src.utils.conversation_manager import register_conversation, end_conversation, end_all_conversations

# Настройка логгирования
logger = logging.getLogger(__name__)

# Имя обработчика для менеджера диалогов
HANDLER_NAME = "impression_handler"

# Клавиатура для выбора категории
CATEGORY_KEYBOARD = ReplyKeyboardMarkup([
    ['1 - Влечение/Тяга', '2 - Эмоция'],
    ['3 - Физическое', '4 - Мысли'],
    ['5 - Другое', '/skip']
], one_time_keyboard=True)

# Маппинг выбора категории на значения
CATEGORY_MAP = {
    '1': 'craving',
    '2': 'emotion',
    '3': 'physical',
    '4': 'thoughts',
    '5': 'other'
}


async def start_impression(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс добавления нового впечатления.
    Первый шаг - запрос текста впечатления.
    """
    # Завершаем все активные диалоги пользователя
    chat_id = update.effective_chat.id
    end_all_conversations(chat_id)

    # Регистрируем новый активный диалог
    register_conversation(chat_id, HANDLER_NAME, IMPRESSION_TEXT)

    # Сохранение информации о пользователе
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    save_user(chat_id, username, first_name)

    # Получение текущей даты и времени
    now = datetime.now()
    impression_date = now.strftime('%Y-%m-%d')
    impression_time = now.strftime('%H:%M:%S')

    # Инициализация словаря данных пользователя
    context.user_data['impression'] = {
        'chat_id': chat_id,
        'impression_date': impression_date,
        'impression_time': impression_time
    }

    logger.info(f"Пользователь {chat_id} начал добавление впечатления")

    await update.effective_message.reply_text(
        "📝 Новое впечатление\n\n"
        "Опишите ваше текущее состояние или впечатление:\n"
        "(Например: 'Хочется выпить', 'Злюсь', 'Мне хорошо')\n\n"
        "Чтобы отменить в любой момент, нажмите /cancel"
    )

    return IMPRESSION_TEXT


async def handle_impression_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод текста впечатления.
    """
    text = update.message.text.strip()

    if not text:
        await update.effective_message.reply_text(
            "Пожалуйста, введите текст впечатления."
        )
        return IMPRESSION_TEXT

    # Сохраняем текст
    context.user_data['impression']['impression_text'] = text

    logger.debug(f"Текст впечатления: {text}")

    await update.effective_message.reply_text(
        "Оцените интенсивность от 1 до 10:\n"
        "(или /skip чтобы пропустить)",
        reply_markup=NUMERIC_KEYBOARD
    )

    return IMPRESSION_INTENSITY


async def handle_impression_intensity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод интенсивности.
    """
    text = update.message.text.strip()

    # Пропуск
    if text == '/skip':
        context.user_data['impression']['intensity'] = None
        logger.debug("Интенсивность пропущена")
    else:
        # Валидация
        try:
            intensity = int(text)
            if intensity < 1 or intensity > 10:
                await update.effective_message.reply_text(
                    "Интенсивность должна быть от 1 до 10.\n"
                    "Попробуйте снова или /skip:",
                    reply_markup=NUMERIC_KEYBOARD
                )
                return IMPRESSION_INTENSITY

            context.user_data['impression']['intensity'] = intensity
            logger.debug(f"Интенсивность: {intensity}")
        except ValueError:
            await update.effective_message.reply_text(
                "Пожалуйста, введите число от 1 до 10 или /skip:",
                reply_markup=NUMERIC_KEYBOARD
            )
            return IMPRESSION_INTENSITY

    # Переход к выбору категории
    await update.effective_message.reply_text(
        "Выберите категорию:\n"
        "1️⃣ Влечение/Тяга\n"
        "2️⃣ Эмоция\n"
        "3️⃣ Физическое состояние\n"
        "4️⃣ Мысли\n"
        "5️⃣ Другое\n\n"
        "или /skip",
        reply_markup=CATEGORY_KEYBOARD
    )

    return IMPRESSION_CATEGORY


async def handle_impression_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор категории.
    """
    text = update.message.text.strip()

    # Пропуск
    if text == '/skip':
        context.user_data['impression']['category'] = None
        logger.debug("Категория пропущена")
    else:
        # Извлекаем первый символ (число)
        choice = text[0] if text else None

        if choice in CATEGORY_MAP:
            category = CATEGORY_MAP[choice]
            context.user_data['impression']['category'] = category
            logger.debug(f"Категория: {category}")
        else:
            await update.effective_message.reply_text(
                "Пожалуйста, выберите категорию (1-5) или /skip:",
                reply_markup=CATEGORY_KEYBOARD
            )
            return IMPRESSION_CATEGORY

    # Переход к тегам
    await update.effective_message.reply_text(
        "Добавить теги? (через запятую или /skip)\n"
        "Например: стресс, работа, вечер"
    )

    return IMPRESSION_TAGS


async def handle_impression_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод тегов и сохраняет впечатление.
    """
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Получаем соединение с БД
    conn = _get_db_connection()

    impression_data = context.user_data['impression']

    # Сохраняем впечатление
    success = save_impression(conn, impression_data)

    if not success:
        await update.effective_message.reply_text(
            "❌ Ошибка при сохранении впечатления. Попробуйте позже.",
            reply_markup=MAIN_KEYBOARD
        )
        end_conversation(chat_id, HANDLER_NAME)
        if 'impression' in context.user_data:
            context.user_data.pop('impression')
        return ConversationHandler.END

    # Получаем ID сохраненного впечатления
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM impressions
        WHERE chat_id = ? AND impression_date = ? AND impression_time = ?
        ORDER BY id DESC LIMIT 1
    """, (chat_id, impression_data['impression_date'], impression_data['impression_time']))

    row = cursor.fetchone()
    if not row:
        logger.error("Не удалось получить ID сохраненного впечатления")
    else:
        impression_id = row[0]

        # Обработка тегов если не /skip
        if text != '/skip' and text:
            # Парсим теги
            tag_names = [t.strip() for t in text.split(',') if t.strip()]

            if tag_names:
                # Создаем теги и получаем их ID
                tag_ids = []
                for tag_name in tag_names:
                    tag_id = create_tag(conn, chat_id, tag_name)
                    if tag_id:
                        tag_ids.append(tag_id)

                # Привязываем теги к впечатлению
                if tag_ids:
                    attach_tags_to_impression(conn, impression_id, tag_ids)
                    logger.info(f"Привязано {len(tag_ids)} тегов к впечатлению {impression_id}")

    # Формируем подтверждение
    confirmation = "✅ Впечатление сохранено!\n\n"
    confirmation += f"📝 {impression_data['impression_text']}\n"

    if impression_data.get('intensity'):
        confirmation += f"🔥 Интенсивность: {impression_data['intensity']}/10\n"

    if impression_data.get('category'):
        category_names = {
            'craving': 'Влечение/Тяга',
            'emotion': 'Эмоция',
            'physical': 'Физическое состояние',
            'thoughts': 'Мысли',
            'other': 'Другое'
        }
        confirmation += f"📂 Категория: {category_names.get(impression_data['category'], impression_data['category'])}\n"

    if text != '/skip' and text:
        confirmation += f"🏷️ Теги: {text}\n"

    confirmation += f"⏰ {impression_data['impression_time'].rsplit(':', 1)[0]}, {impression_data['impression_date']}"

    await update.effective_message.reply_text(
        confirmation,
        reply_markup=MAIN_KEYBOARD
    )

    # Завершение диалога
    end_conversation(chat_id, HANDLER_NAME)
    if 'impression' in context.user_data:
        context.user_data.pop('impression')

    logger.info(f"Впечатление успешно сохранено для пользователя {chat_id}")

    return ConversationHandler.END


async def cancel_impression(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отменяет добавление впечатления.
    """
    chat_id = update.effective_chat.id
    logger.info(f"Отмена добавления впечатления для пользователя {chat_id}")

    # Завершение диалога в менеджере
    end_conversation(chat_id, HANDLER_NAME)

    # Очистка данных пользователя
    if 'impression' in context.user_data:
        context.user_data.pop('impression')

    await update.message.reply_text(
        "Добавление впечатления отменено.",
        reply_markup=MAIN_KEYBOARD
    )

    return ConversationHandler.END


# Создание ConversationHandler
impression_conversation_handler = ConversationHandler(
    entry_points=[
        CommandHandler('impression', start_impression)
    ],
    states={
        IMPRESSION_TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_impression_text)
        ],
        IMPRESSION_INTENSITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_impression_intensity)
        ],
        IMPRESSION_CATEGORY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_impression_category)
        ],
        IMPRESSION_TAGS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_impression_tags)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', cancel_impression)
    ],
    name=HANDLER_NAME
)


def register(application: Application):
    """
    Регистрирует обработчики впечатлений в приложении.
    """
    application.add_handler(impression_conversation_handler)
