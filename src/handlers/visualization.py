"""
Модуль с обработчиками для визуализации данных.
Обрабатывает команды для создания и отображения графиков.
"""

import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)

from src.data.storage import get_user_entries
from src.utils.keyboards import MAIN_KEYBOARD
from src.visualization.charts import create_time_series_chart, create_correlation_matrix
from src.visualization.heatmaps import create_monthly_heatmap, create_mood_distribution
from src.utils.formatters import get_column_name
from src.handlers.basic import cancel

# Настройка логгирования
logger = logging.getLogger(__name__)

# Состояния для диалогов визуализации
(
    SELECT_CHART_TYPE,
    SELECT_METRIC,
    SELECT_PERIOD
) = range(3)


async def start_visualization(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс визуализации данных.
    Предлагает пользователю выбрать тип графика.

    Args:
        update: объект с информацией о сообщении
        context: контекст бота

    Returns:
        int: следующее состояние диалога (SELECT_CHART_TYPE)
    """
    chat_id = update.effective_chat.id
    logger.info(f"Пользователь {chat_id} начал процесс визуализации")

    # Проверка наличия записей у пользователя
    entries = get_user_entries(chat_id)

    if not entries:
        await update.message.reply_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END

    # Создаем клавиатуру для выбора типа графика
    keyboard = [
        [InlineKeyboardButton("Динамика показателей", callback_data="time_series")],
        [InlineKeyboardButton("Распределение значений", callback_data="distribution")],
        [InlineKeyboardButton("Корреляция показателей", callback_data="correlation")],
        [InlineKeyboardButton("Календарь настроения", callback_data="calendar")]
    ]

    await update.message.reply_text(
        "Выберите тип графика для визуализации ваших данных:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SELECT_CHART_TYPE


async def select_chart_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор типа графика.
    В зависимости от выбора, запрашивает метрику или период.

    Args:
        update: объект с информацией о callback query
        context: контекст бота

    Returns:
        int: следующее состояние диалога
    """
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    chart_type = query.data

    # Логирование для отладки
    logger.info(f"Пользователь {chat_id} выбрал тип графика: {chart_type}")

    # Сохраняем выбранный тип графика
    context.user_data['chart_type'] = chart_type

    if chart_type == "time_series":
        # Для динамики показателей предлагаем выбрать несколько метрик
        keyboard = [
            [
                InlineKeyboardButton("Настроение", callback_data="mood"),
                InlineKeyboardButton("Сон", callback_data="sleep")
            ],
            [
                InlineKeyboardButton("Тревога", callback_data="anxiety"),
                InlineKeyboardButton("Депрессия", callback_data="depression")
            ],
            [
                InlineKeyboardButton("Все показатели", callback_data="all")
            ]
        ]

        await query.message.edit_text(
            "Выберите показатели для графика динамики:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return SELECT_METRIC

    elif chart_type == "distribution":
        # Для распределения предлагаем выбрать одну метрику
        keyboard = [
            [
                InlineKeyboardButton("Настроение", callback_data="mood"),
                InlineKeyboardButton("Сон", callback_data="sleep")
            ],
            [
                InlineKeyboardButton("Тревога", callback_data="anxiety"),
                InlineKeyboardButton("Депрессия", callback_data="depression")
            ],
            [
                InlineKeyboardButton("Работоспособность", callback_data="productivity"),
                InlineKeyboardButton("Общительность", callback_data="sociability")
            ]
        ]

        await query.message.edit_text(
            "Выберите показатель для графика распределения:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return SELECT_METRIC

    elif chart_type == "correlation":
        # Для корреляции не нужно выбирать метрики, сразу показываем корреляцию всех показателей
        await generate_correlation_chart(query.message, chat_id)
        return ConversationHandler.END

    elif chart_type == "calendar":
        # Для календаря предлагаем выбрать одну метрику
        keyboard = [
            [
                InlineKeyboardButton("Настроение", callback_data="mood"),
                InlineKeyboardButton("Сон", callback_data="sleep")
            ],
            [
                InlineKeyboardButton("Тревога", callback_data="anxiety"),
                InlineKeyboardButton("Депрессия", callback_data="depression")
            ]
        ]

        await query.message.edit_text(
            "Выберите показатель для календаря настроения:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return SELECT_METRIC

    else:
        await query.message.edit_text(
            "Неизвестный тип графика. Пожалуйста, попробуйте снова.",
            reply_markup=MAIN_KEYBOARD
        )

        return ConversationHandler.END


async def select_metric(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор метрики для визуализации.

    Args:
        update: объект с информацией о callback query
        context: контекст бота

    Returns:
        int: следующее состояние диалога или ConversationHandler.END
    """
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    metric = query.data

    # Логирование для отладки
    logger.info(f"Пользователь {chat_id} выбрал метрику: {metric}")

    # Сохраняем выбранную метрику
    context.user_data['metric'] = metric

    chart_type = context.user_data.get('chart_type')

    if chart_type == "time_series":
        await generate_time_series_chart(query.message, chat_id, metric)
    elif chart_type == "distribution":
        await generate_distribution_chart(query.message, chat_id, metric)
    elif chart_type == "calendar":
        # Для календаря нужно выбрать период
        now = datetime.now()
        keyboard = [
            [
                InlineKeyboardButton(f"{now.month - 2}/{now.year}",
                                     callback_data=f"{now.year}_{now.month - 2}")
            ],
            [
                InlineKeyboardButton(f"{now.month - 1}/{now.year}",
                                     callback_data=f"{now.year}_{now.month - 1}")
            ],
            [
                InlineKeyboardButton(f"{now.month}/{now.year}",
                                     callback_data=f"{now.year}_{now.month}")
            ]
        ]

        await query.message.edit_text(
            "Выберите месяц для календаря настроения:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return SELECT_PERIOD

    return ConversationHandler.END


async def select_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор периода для календаря настроения.

    Args:
        update: объект с информацией о callback query
        context: контекст бота

    Returns:
        int: состояние ConversationHandler.END
    """
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    year, month = query.data.split("_")

    # Логирование для отладки
    logger.info(f"Пользователь {chat_id} выбрал период: год={year}, месяц={month}")

    # Генерация календаря настроения
    metric = context.user_data.get('metric')
    await generate_calendar_chart(query.message, chat_id, metric, int(year), int(month))

    return ConversationHandler.END


async def generate_time_series_chart(message, chat_id: int, metric: str):
    """
    Генерирует и отправляет график временного ряда.

    Args:
        message: сообщение для ответа
        chat_id: ID пользователя
        metric: название метрики или 'all' для всех метрик
    """
    # Получаем данные пользователя
    entries = get_user_entries(chat_id)

    if not entries:
        await message.edit_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=None
        )
        return

    # Определяем метрики для отображения
    if metric == "all":
        columns = ['mood', 'sleep', 'balance', 'mania', 'depression',
                   'anxiety', 'irritability', 'productivity', 'sociability']
    else:
        columns = [metric]

    try:
        # Создание графика
        chart_buffer = create_time_series_chart(entries, columns)

        # Отправка графика пользователю
        await message.edit_text("Генерация графика...")
        await message.reply_photo(
            photo=chart_buffer,
            caption=f"График динамики показателей",
            reply_markup=MAIN_KEYBOARD
        )

        # Удаление промежуточного сообщения
        await message.delete()

    except Exception as e:
        logger.error(f"Ошибка при генерации графика временного ряда: {e}")
        await message.edit_text(
            f"Произошла ошибка при генерации графика: {str(e)}",
            reply_markup=None
        )


async def generate_distribution_chart(message, chat_id: int, metric: str):
    """
    Генерирует и отправляет график распределения.

    Args:
        message: сообщение для ответа
        chat_id: ID пользователя
        metric: название метрики
    """
    # Получаем данные пользователя
    entries = get_user_entries(chat_id)

    if not entries:
        await message.edit_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=None
        )
        return

    try:
        # Создание графика распределения
        chart_buffer = create_mood_distribution(entries, metric)

        if chart_buffer is None:
            await message.edit_text(
                f"Не удалось создать график распределения для показателя {get_column_name(metric)}.",
                reply_markup=None
            )
            return

        # Отправка графика пользователю
        await message.edit_text("Генерация графика...")
        await message.reply_photo(
            photo=chart_buffer,
            caption=f"Распределение показателя {get_column_name(metric)}",
            reply_markup=MAIN_KEYBOARD
        )

        # Удаление промежуточного сообщения
        await message.delete()

    except Exception as e:
        logger.error(f"Ошибка при генерации графика распределения: {e}")
        await message.edit_text(
            f"Произошла ошибка при генерации графика: {str(e)}",
            reply_markup=None
        )


async def generate_correlation_chart(message, chat_id: int):
    """
    Генерирует и отправляет матрицу корреляции.

    Args:
        message: сообщение для ответа
        chat_id: ID пользователя
    """
    # Получаем данные пользователя
    entries = get_user_entries(chat_id)

    if not entries:
        # When editing a message that had an inline keyboard, we need to provide a new keyboard or None
        await message.edit_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=None  # Explicitly set to None to remove the keyboard
        )
        return

    # Если записей мало, корреляция может быть ненадежной
    if len(entries) < 5:
        await message.edit_text(
            "Для построения матрицы корреляции нужно больше записей (минимум 5).",
            reply_markup=None  # Explicitly set to None to remove the keyboard
        )
        return

    columns = ['mood', 'sleep', 'balance', 'mania', 'depression',
               'anxiety', 'irritability', 'productivity', 'sociability']

    try:
        # Instead of editing the message text, which requires an inline keyboard,
        # let's first reply with a temporary status message
        status_message = await message.reply_text("Генерация матрицы корреляции...")

        # Create the correlation matrix
        chart_buffer = create_correlation_matrix(entries, columns)

        # Send the chart as a new message
        await message.reply_photo(
            photo=chart_buffer,
            caption="Матрица корреляции показателей",
            reply_markup=MAIN_KEYBOARD
        )

        # Delete the temporary status message
        await status_message.delete()

        # Delete or update the original message
        try:
            await message.delete()
        except Exception as e:
            # If we can't delete, try to update with a simple text
            try:
                await message.edit_text(
                    "Матрица корреляции сгенерирована.",
                    reply_markup=None  # Remove the inline keyboard
                )
            except Exception:
                # If that also fails, just ignore it
                pass

    except Exception as e:
        logger.error(f"Ошибка при генерации матрицы корреляции: {e}")
        await message.edit_text(
            f"Произошла ошибка при генерации матрицы корреляции: {str(e)}",
            reply_markup=None  # Explicitly set to None to remove the keyboard
        )


async def generate_calendar_chart(message, chat_id: int, metric: str, year: int, month: int):
    """
    Генерирует и отправляет календарь настроения.

    Args:
        message: сообщение для ответа
        chat_id: ID пользователя
        metric: название метрики
        year: год
        month: месяц
    """
    # Получаем данные пользователя
    entries = get_user_entries(chat_id)

    if not entries:
        await message.edit_text(
            "У вас еще нет записей в дневнике или не удалось расшифровать данные.",
            reply_markup=None
        )
        return

    try:
        # Создание календаря настроения
        chart_buffer = create_monthly_heatmap(entries, year, month, metric)

        if chart_buffer is None:
            await message.edit_text(
                f"Не удалось создать календарь для показателя {get_column_name(metric)}.",
                reply_markup=None
            )
            return

        # Отправка графика пользователю
        await message.edit_text("Генерация календаря настроения...")
        await message.reply_photo(
            photo=chart_buffer,
            caption=f"Календарь показателя {get_column_name(metric)} за {month}/{year}",
            reply_markup=MAIN_KEYBOARD
        )

        # Удаление промежуточного сообщения
        await message.delete()

    except Exception as e:
        logger.error(f"Ошибка при генерации календаря настроения: {e}")
        await message.edit_text(
            f"Произошла ошибка при генерации календаря: {str(e)}",
            reply_markup=None
        )


def register(application):
    """
    Регистрирует обработчики команд для визуализации.

    Args:
        application: экземпляр приложения бота
    """
    # Регистрация обработчика для визуализации
    viz_handler = ConversationHandler(
        entry_points=[CommandHandler("visualize", start_visualization)],
        states={
            SELECT_CHART_TYPE: [CallbackQueryHandler(select_chart_type)],
            SELECT_METRIC: [CallbackQueryHandler(select_metric)],
            SELECT_PERIOD: [CallbackQueryHandler(select_period)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(viz_handler)

    logger.info("Обработчики визуализации зарегистрированы")