"""
Модуль для обработки обмена данными между пользователями.
Обрабатывает команды для отправки и просмотра дневников.
"""

import io
import json
import logging
import secrets
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters, CallbackQueryHandler, Application
)

from src.utils.keyboards import MAIN_KEYBOARD
from src.data.storage import get_user_data_file, get_user_entries
from src.data.encryption import encrypt_for_sharing
from src.utils.conversation_manager import register_conversation, end_conversation, end_all_conversations

# Настройка логгирования
logger = logging.getLogger(__name__)

# Состояния диалога отправки дневника
SEND_DIARY_USER_ID = 1
SEND_DIARY_START_DATE = 2
SHARE_PASSWORD_ENTRY = 3

# Префикс для callback-данных отправки дневника
SHARE_PREFIX = "share_"

# Имена обработчиков для менеджера диалогов
SEND_HANDLER_NAME = "send_diary_handler"
VIEW_HANDLER_NAME = "view_shared_handler"

# Глобальные объекты для хранения ссылок на обработчики
send_conversation_handler = None
view_shared_handler = None


async def custom_cancel_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Локальный обработчик отмены для диалога отправки дневника.
    """
    chat_id = update.effective_chat.id
    logger.info(f"Отмена отправки дневника для пользователя {chat_id}")

    # Завершение диалога в менеджере
    end_conversation(chat_id, SEND_HANDLER_NAME)

    # Очистка данных пользователя
    if 'recipient_id' in context.user_data:
        context.user_data.pop('recipient_id')
    if 'selected_date_range' in context.user_data:
        context.user_data.pop('selected_date_range')
    if 'sharing_password' in context.user_data:
        context.user_data.pop('sharing_password')

    await update.message.reply_text(
        "Отправка дневника отменена.",
        reply_markup=MAIN_KEYBOARD
    )

    return ConversationHandler.END


async def custom_cancel_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Локальный обработчик отмены для диалога просмотра дневника.
    """
    chat_id = update.effective_chat.id
    logger.info(f"Отмена просмотра дневника для пользователя {chat_id}")

    # Завершение диалога в менеджере
    end_conversation(chat_id, VIEW_HANDLER_NAME)

    await update.message.reply_text(
        "Просмотр дневника отменен.",
        reply_markup=MAIN_KEYBOARD
    )

    return ConversationHandler.END


async def send_diary_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс отправки дневника другому пользователю.
    Запрашивает ID получателя.
    """
    # Завершаем все активные диалоги пользователя
    chat_id = update.effective_chat.id
    end_all_conversations(chat_id)

    # Регистрируем новый активный диалог
    register_conversation(chat_id, SEND_HANDLER_NAME, SEND_DIARY_USER_ID)

    logger.info(f"Пользователь {chat_id} начал процесс отправки дневника")

    # Проверка наличия записей у пользователя
    entries = get_user_entries(chat_id)

    if not entries:
        # Завершаем диалог, так как у пользователя нет записей
        end_conversation(chat_id, SEND_HANDLER_NAME)

        await update.message.reply_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Чтобы отправить ваш дневник другому пользователю, мне нужен ID этого пользователя.\n"
        "Попросите этого пользователя выполнить команду /id и отправить вам полученный номер.\n\n"
        "Введите ID пользователя, которому хотите отправить дневник:",
        reply_markup=ReplyKeyboardRemove()
    )
    return SEND_DIARY_USER_ID


async def send_diary_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ID получателя и запрашивает диапазон дат.
    """
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обновление состояния в менеджере диалогов
    register_conversation(chat_id, SEND_HANDLER_NAME, SEND_DIARY_START_DATE)

    # Попытка преобразовать ввод в целое число
    try:
        recipient_id = int(text)
        context.user_data['recipient_id'] = recipient_id
        logger.info(f"Пользователь {chat_id} указал получателя: {recipient_id}")

        # Создание кнопок выбора диапазона дат
        keyboard = create_date_range_keyboard()

        await update.message.reply_text(
            "Выберите период, за который хотите отправить данные:",
            reply_markup=keyboard
        )
        return SEND_DIARY_START_DATE

    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите корректный числовой ID пользователя.\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
        )
        return SEND_DIARY_USER_ID


def create_date_range_keyboard():
    """
    Создает клавиатуру выбора диапазона дат.
    """
    today = datetime.now().date()
    week_ago = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    month_ago = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    quarter_ago = (today - timedelta(days=90)).strftime('%Y-%m-%d')

    keyboard = [
        [InlineKeyboardButton("Последние 7 дней", callback_data=f"{SHARE_PREFIX}date_range_{week_ago}_{today}")],
        [InlineKeyboardButton("Последние 30 дней", callback_data=f"{SHARE_PREFIX}date_range_{month_ago}_{today}")],
        [InlineKeyboardButton("Последние 90 дней", callback_data=f"{SHARE_PREFIX}date_range_{quarter_ago}_{today}")],
        [InlineKeyboardButton("Всё время", callback_data=f"{SHARE_PREFIX}date_range_all")]
    ]

    return InlineKeyboardMarkup(keyboard)


async def process_date_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбранный диапазон дат и отправляет зашифрованный дневник получателю.
    """
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id

    # Завершение диалога в менеджере диалогов
    end_conversation(chat_id, SEND_HANDLER_NAME)

    recipient_id = context.user_data.get('recipient_id')

    if not recipient_id:
        await query.message.reply_text(
            "Произошла ошибка: ID получателя не найден.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    # Удаляем префикс из callback_data
    callback_data = query.data
    if callback_data.startswith(SHARE_PREFIX):
        callback_data = callback_data[len(SHARE_PREFIX):]

    # Логирование для отладки
    logger.info(f"Обрабатываем диапазон дат: {callback_data}")

    # Сохранение выбранного диапазона дат
    context.user_data['selected_date_range'] = callback_data

    # Генерация случайного одноразового пароля для обмена
    sharing_password = ''.join(
        secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        for _ in range(10)
    )
    context.user_data['sharing_password'] = sharing_password

    # Получение записей пользователя
    entries = get_user_entries(chat_id)

    if not entries:
        await query.message.reply_text(
            "Не удалось получить или расшифровать записи.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    # Обработка диапазона дат
    date_range = context.user_data['selected_date_range']

    # Преобразование в DataFrame для фильтрации
    import pandas as pd
    entries_df = pd.DataFrame(entries)

    try:
        if date_range == "date_range_all":
            # Использовать все данные
            filtered_df = entries_df
            logger.info(f"Используем все записи: {len(filtered_df)} записей")
        else:
            # Проверка формата строки date_range
            if not date_range.startswith("date_range_"):
                logger.error(f"Неверный формат диапазона дат: {date_range}")
                await query.message.reply_text(
                    "Произошла ошибка при обработке диапазона дат.",
                    reply_markup=MAIN_KEYBOARD
                )
                return ConversationHandler.END

            # Извлечение дат из данных обратного вызова
            parts = date_range.split('_')
            if len(parts) < 3:
                logger.error(f"Недостаточно частей в строке диапазона: {date_range}")
                await query.message.reply_text(
                    "Произошла ошибка при обработке диапазона дат.",
                    reply_markup=MAIN_KEYBOARD
                )
                return ConversationHandler.END

            # Извлекаем даты, учитывая, что после разделения могут быть дополнительные части
            start_date = parts[2]
            # Последняя часть - это конечная дата
            end_date = parts[3] if len(parts) > 3 else datetime.now().strftime('%Y-%m-%d')

            logger.info(f"Извлеченные даты: с {start_date} по {end_date}")

            # Конвертируем столбец даты в datetime перед фильтрацией
            if 'date' in entries_df.columns:
                entries_df['date'] = pd.to_datetime(entries_df['date'])

                # Проверяем формат дат
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    logger.info(f"Преобразованные даты: с {start_dt} по {end_dt}")

                    # Фильтрация по дате
                    filtered_df = entries_df[(entries_df['date'] >= start_dt) & (entries_df['date'] <= end_dt)]
                    logger.info(f"Отфильтровано {len(filtered_df)} записей из {len(entries_df)}")
                except Exception as e:
                    logger.error(f"Ошибка при преобразовании дат: {e}")
                    filtered_df = entries_df  # Используем все данные в случае ошибки
            else:
                logger.warning("Колонка 'date' не найдена в данных")
                filtered_df = entries_df
    except Exception as e:
        logger.error(f"Ошибка при фильтрации данных: {e}")
        await query.message.reply_text(
            f"Произошла ошибка при фильтрации данных: {str(e)}",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    if len(filtered_df) == 0:
        await query.message.reply_text(
            "За выбранный период нет данных для отправки.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    # Повторная шифровка отфильтрованных данных с одноразовым паролем для получателя
    all_entries = filtered_df.to_dict('records')
    encrypted_for_sharing = encrypt_for_sharing(all_entries, sharing_password)

    # Создание пользовательского формата для зашифрованного файла
    encrypted_package = {
        'encrypted_data': encrypted_for_sharing,
        'sender_id': chat_id,
        'format_version': '1.0'
    }

    # Преобразование в JSON, затем в байты
    encrypted_bytes = io.BytesIO()
    encrypted_bytes.write(json.dumps(encrypted_package).encode('utf-8'))
    encrypted_bytes.seek(0)

    try:
        # Получение информации об отправителе
        sender_info = ""
        if query.from_user.username:
            sender_info = f" от @{query.from_user.username}"
        elif query.from_user.first_name:
            sender_info = f" от {query.from_user.first_name}"

        # Отправка зашифрованного файла получателю
        await context.bot.send_document(
            chat_id=recipient_id,
            document=encrypted_bytes,
            filename="shared_encrypted_diary.json",
            caption=f"Зашифрованный дневник настроения{sender_info}. Для просмотра используйте команду /view_shared."
        )

        await query.message.reply_text(
            f"Дневник успешно отправлен указанному пользователю!\n\n"
            f"Сообщите получателю пароль '{sharing_password}' для доступа к данным. "
            f"Этот пароль будет нужен получателю при использовании команды /view_shared.",
            reply_markup=MAIN_KEYBOARD
        )
        logger.info(f"Пользователь {chat_id} успешно отправил дневник пользователю {recipient_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке дневника: {str(e)}")
        await query.message.reply_text(
            f"Не удалось отправить дневник. Возможно, указан неверный ID пользователя или пользователь заблокировал бота.\n\nОшибка: {str(e)}",
            reply_markup=MAIN_KEYBOARD
        )

    return ConversationHandler.END


async def view_shared_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс просмотра полученного дневника.
    Запрашивает пароль для расшифровки.
    """
    # Завершаем все активные диалоги пользователя
    chat_id = update.effective_chat.id
    end_all_conversations(chat_id)

    # Регистрируем новый активный диалог
    register_conversation(chat_id, VIEW_HANDLER_NAME, SHARE_PASSWORD_ENTRY)

    logger.info(f"Пользователь {chat_id} начал процесс просмотра полученного дневника")

    # Запрос пересылки файла дневника
    await update.message.reply_text(
        "Для просмотра полученного дневника, пожалуйста, перешлите мне файл дневника, "
        "который вам отправили.\n\n"
        "После этого вам потребуется ввести пароль, который вам сообщил отправитель.",
        reply_markup=ReplyKeyboardRemove()
    )

    # Запрос пароля
    await update.message.reply_text(
        "Пожалуйста, введите пароль для расшифровки полученного дневника:"
    )
    return SHARE_PASSWORD_ENTRY


async def process_shared_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает пароль для просмотра общего дневника.
    """
    # Завершение диалога в менеджере диалогов
    chat_id = update.effective_chat.id
    end_conversation(chat_id, VIEW_HANDLER_NAME)

    logger.info(f"Пользователь {chat_id} ввел пароль для расшифровки дневника")

    await update.message.reply_text(
        "Функция просмотра общих дневников требует обработки загруженных файлов, "
        "что выходит за рамки этого примера. В полной реализации здесь будет "
        "расшифровка и отображение общего дневника с использованием введенного пароля.",
        reply_markup=MAIN_KEYBOARD
    )
    return ConversationHandler.END


def register(application: Application):
    """
    Регистрирует обработчики команд для обмена данными.
    """
    global send_conversation_handler, view_shared_handler

    # Создаем новые обработчики для отправки дневника
    user_id_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, send_diary_user_id)
    date_range_handler = CallbackQueryHandler(process_date_range, pattern=f"^{SHARE_PREFIX}")

    # Создание обработчика разговора для отправки дневника
    send_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("send", send_diary_start)],
        states={
            SEND_DIARY_USER_ID: [user_id_handler],
            SEND_DIARY_START_DATE: [date_range_handler],
        },
        fallbacks=[CommandHandler("cancel", custom_cancel_send)],
        name=SEND_HANDLER_NAME,
        persistent=False,
        allow_reentry=True,
    )

    # Создаем новые обработчики для просмотра дневника
    password_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, process_shared_password)

    # Создание обработчика разговора для просмотра полученного дневника
    view_shared_handler = ConversationHandler(
        entry_points=[CommandHandler("view_shared", view_shared_start)],
        states={
            SHARE_PASSWORD_ENTRY: [password_handler],
        },
        fallbacks=[CommandHandler("cancel", custom_cancel_view)],
        name=VIEW_HANDLER_NAME,
        persistent=False,
        allow_reentry=True,
    )

    # Удаляем старые обработчики если они есть
    for handler in application.handlers.get(0, [])[:]:
        if isinstance(handler, ConversationHandler) and getattr(handler, 'name', None) in [SEND_HANDLER_NAME, VIEW_HANDLER_NAME]:
            application.remove_handler(handler)
            logger.info(f"Удален старый обработчик диалога {getattr(handler, 'name', 'unknown')}")

    # Добавляем новые обработчики
    application.add_handler(send_conversation_handler)
    application.add_handler(view_shared_handler)

    logger.info("Обработчики обмена данными зарегистрированы")