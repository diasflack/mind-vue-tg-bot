"""
Handlers для экспорта данных (Phase 5.4).

Команды:
- /export_impressions [--format csv|json] [--from DATE] [--to DATE]
- /export_surveys <название> [--format csv|json] [--from DATE] [--to DATE]
- /export_all - экспорт всех данных в JSON
"""

import logging
from datetime import datetime
from io import BytesIO
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.data.storage import _get_db_connection
from src.data.export import (
    export_impressions_csv,
    export_impressions_json,
    export_survey_responses_csv,
    export_survey_responses_json,
    export_all_data_json
)

logger = logging.getLogger(__name__)


def parse_export_args(args: list) -> dict:
    """
    Парсит аргументы команды экспорта.

    Args:
        args: список аргументов

    Returns:
        dict: словарь с параметрами {format, from_date, to_date, survey_name}
    """
    params = {
        'format': 'csv',  # По умолчанию CSV
        'from_date': None,
        'to_date': None,
        'survey_name': None
    }

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == '--format' and i + 1 < len(args):
            params['format'] = args[i + 1].lower()
            i += 2
        elif arg == '--from' and i + 1 < len(args):
            params['from_date'] = args[i + 1]
            i += 2
        elif arg == '--to' and i + 1 < len(args):
            params['to_date'] = args[i + 1]
            i += 2
        else:
            # Если не флаг, считаем что это название опроса
            if not arg.startswith('--'):
                params['survey_name'] = arg
            i += 1

    return params


async def export_impressions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Экспортирует впечатления пользователя - /export_impressions.

    Параметры:
        --format csv|json: формат экспорта (по умолчанию csv)
        --from DATE: начальная дата (YYYY-MM-DD)
        --to DATE: конечная дата (YYYY-MM-DD)
    """
    chat_id = update.effective_chat.id

    # Парсим аргументы
    params = parse_export_args(context.args)

    # Валидация формата
    if params['format'] not in ['csv', 'json']:
        await update.message.reply_text(
            "❌ Неверный формат.\n\n"
            "Поддерживаемые форматы: csv, json\n\n"
            "Использование: /export_impressions [--format csv|json] [--from DATE] [--to DATE]"
        )
        return

    try:
        conn = _get_db_connection()

        # Экспортируем данные
        if params['format'] == 'csv':
            data = export_impressions_csv(
                conn,
                chat_id=chat_id,
                from_date=params['from_date'],
                to_date=params['to_date']
            )
            filename = f"impressions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            mime_type = 'text/csv'
        else:  # json
            data = export_impressions_json(
                conn,
                chat_id=chat_id,
                from_date=params['from_date'],
                to_date=params['to_date']
            )
            filename = f"impressions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            mime_type = 'application/json'

        # Проверяем наличие данных
        if not data or (params['format'] == 'csv' and data.count('\n') <= 1):
            await update.message.reply_text(
                "ℹ️ Нет впечатлений для экспорта.\n\n"
                "Добавьте впечатления с помощью /add_impression"
            )
            return

        # Отправляем файл
        file_bytes = BytesIO(data.encode('utf-8'))
        file_bytes.name = filename

        await update.message.reply_document(
            document=file_bytes,
            filename=filename,
            caption=f"📊 Экспорт впечатлений ({params['format'].upper()})"
        )

        logger.info(f"Пользователь {chat_id} экспортировал впечатления в {params['format']}")

    except Exception as e:
        logger.error(f"Ошибка при экспорте впечатлений: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при экспорте данных.\n"
            "Попробуйте позже."
        )


async def export_surveys_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Экспортирует ответы на конкретный опрос - /export_surveys.

    Параметры:
        <название>: название опроса (обязательно)
        --format csv|json: формат экспорта (по умолчанию csv)
        --from DATE: начальная дата (YYYY-MM-DD)
        --to DATE: конечная дата (YYYY-MM-DD)
    """
    chat_id = update.effective_chat.id

    # Парсим аргументы
    params = parse_export_args(context.args)

    # Проверяем что указано название опроса
    if not params['survey_name']:
        await update.message.reply_text(
            "❌ Не указано название опроса.\n\n"
            "Использование: /export_surveys <название> [--format csv|json] [--from DATE] [--to DATE]\n\n"
            "Пример: /export_surveys Настроение --format json"
        )
        return

    # Валидация формата
    if params['format'] not in ['csv', 'json']:
        await update.message.reply_text(
            "❌ Неверный формат.\n\n"
            "Поддерживаемые форматы: csv, json"
        )
        return

    try:
        conn = _get_db_connection()

        # Экспортируем данные
        if params['format'] == 'csv':
            data = export_survey_responses_csv(
                conn,
                chat_id=chat_id,
                survey_name=params['survey_name'],
                from_date=params['from_date'],
                to_date=params['to_date']
            )
        else:  # json
            data = export_survey_responses_json(
                conn,
                chat_id=chat_id,
                survey_name=params['survey_name'],
                from_date=params['from_date'],
                to_date=params['to_date']
            )

        # Проверяем что опрос найден
        if data is None:
            await update.message.reply_text(
                f"❌ Опрос '{params['survey_name']}' не найден.\n\n"
                f"Посмотреть доступные опросы: /surveys"
            )
            return

        # Проверяем наличие данных
        if not data or (params['format'] == 'csv' and data.count('\n') <= 1):
            await update.message.reply_text(
                f"ℹ️ Нет ответов на опрос '{params['survey_name']}' для экспорта.\n\n"
                f"Заполните опрос с помощью /fill_survey"
            )
            return

        # Формируем имя файла
        safe_name = params['survey_name'].replace(' ', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if params['format'] == 'csv':
            filename = f"survey_{safe_name}_{timestamp}.csv"
            mime_type = 'text/csv'
        else:
            filename = f"survey_{safe_name}_{timestamp}.json"
            mime_type = 'application/json'

        # Отправляем файл
        file_bytes = BytesIO(data.encode('utf-8'))
        file_bytes.name = filename

        await update.message.reply_document(
            document=file_bytes,
            filename=filename,
            caption=f"📊 Экспорт опроса '{params['survey_name']}' ({params['format'].upper()})"
        )

        logger.info(f"Пользователь {chat_id} экспортировал опрос '{params['survey_name']}' в {params['format']}")

    except Exception as e:
        logger.error(f"Ошибка при экспорте опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при экспорте данных.\n"
            "Попробуйте позже."
        )


async def export_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Экспортирует все данные пользователя в JSON - /export_all.

    Включает:
    - Записи дневника
    - Впечатления
    - Ответы на все опросы
    """
    chat_id = update.effective_chat.id

    try:
        conn = _get_db_connection()

        # Экспортируем все данные
        data = export_all_data_json(conn, chat_id=chat_id)

        # Формируем имя файла
        filename = f"mindvue_all_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Отправляем файл
        file_bytes = BytesIO(data.encode('utf-8'))
        file_bytes.name = filename

        await update.message.reply_document(
            document=file_bytes,
            filename=filename,
            caption=(
                "📦 Полный экспорт всех данных\n\n"
                "Включает:\n"
                "• Записи дневника\n"
                "• Впечатления\n"
                "• Ответы на опросы\n\n"
                "Формат: JSON"
            )
        )

        logger.info(f"Пользователь {chat_id} экспортировал все данные")

    except Exception as e:
        logger.error(f"Ошибка при полном экспорте данных: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при экспорте данных.\n"
            "Попробуйте позже."
        )


def register(application) -> None:
    """Регистрирует handlers для экспорта данных."""
    application.add_handler(CommandHandler('export_impressions', export_impressions_handler))
    application.add_handler(CommandHandler('export_surveys', export_surveys_handler))
    application.add_handler(CommandHandler('export_all', export_all_handler))

    logger.info("Export handlers зарегистрированы")
