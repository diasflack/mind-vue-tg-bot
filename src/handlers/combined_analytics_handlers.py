"""
Обработчики команд для объединенной аналитики (Phase 5.5).

Команды:
- /combined_analytics - показать объединенную аналитику впечатлений и опросов
"""

import logging
from typing import List
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

from src.data.storage import _get_db_connection
from src.data.combined_analytics_storage import (
    get_combined_daily_summary,
    get_activity_overview,
    get_correlation_data
)

logger = logging.getLogger(__name__)


def parse_analytics_args(args: List[str]) -> dict:
    """
    Парсит аргументы команды аналитики.

    Поддерживаемые аргументы:
    - --period N: количество дней для анализа
    """
    parsed = {
        'period_days': 7  # По умолчанию 7 дней
    }

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == '--period' and i + 1 < len(args):
            try:
                parsed['period_days'] = int(args[i + 1])
                i += 2
            except ValueError:
                i += 1
        else:
            i += 1

    return parsed


async def combined_analytics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает объединенную аналитику впечатлений и опросов.

    Команда: /combined_analytics [--period N]
    """
    chat_id = update.effective_chat.id

    # Парсим аргументы
    options = parse_analytics_args(context.args)
    period_days = options['period_days']

    conn = _get_db_connection()

    try:
        # Получаем обзор активности
        overview = get_activity_overview(conn, chat_id, period_days)

        # Проверяем наличие данных
        if (overview['total_impressions'] == 0 and
            overview['total_surveys'] == 0 and
            overview['total_entries'] == 0):
            await update.message.reply_text(
                f"📊 *Объединенная аналитика за {period_days} дней*\n\n"
                f"У вас пока нет данных за указанный период.\n\n"
                f"💡 Начните записывать настроение и впечатления!",
                parse_mode='Markdown'
            )
            return

        # Формируем сообщение
        message_lines = [f"📊 *Объединенная аналитика за {period_days} дней*\n"]

        # Общий обзор
        message_lines.append("📈 *Общая активность:*")
        message_lines.append(f"  📝 Записей дня: {overview['total_entries']}")
        message_lines.append(f"  💭 Впечатлений: {overview['total_impressions']}")
        message_lines.append(f"  📋 Опросов: {overview['total_surveys']}")

        if overview['avg_mood_score'] is not None:
            mood_emoji = _get_mood_emoji(overview['avg_mood_score'])
            message_lines.append(f"  {mood_emoji} Среднее настроение: {overview['avg_mood_score']}/10")

        message_lines.append("")

        # Распределение впечатлений
        if overview['total_impressions'] > 0:
            message_lines.append("😊 *Категории впечатлений:*")
            categories = overview['impression_categories']

            positive = categories.get('positive', 0)
            negative = categories.get('negative', 0)
            neutral = categories.get('neutral', 0)

            if positive > 0:
                message_lines.append(f"  😊 Позитивные: {positive}")
            if negative > 0:
                message_lines.append(f"  😔 Негативные: {negative}")
            if neutral > 0:
                message_lines.append(f"  😐 Нейтральные: {neutral}")

            message_lines.append("")

        # Получаем дневную статистику
        daily_summary = get_combined_daily_summary(conn, chat_id, period_days)

        if daily_summary:
            message_lines.append("📅 *Последние дни:*")

            # Показываем последние 5 дней
            for day in daily_summary[:5]:
                date = day['date']
                mood = day['mood_score']
                impressions = day['impressions_count']
                surveys = day['surveys_count']

                mood_str = f"{mood}/10" if mood is not None else "—"
                message_lines.append(
                    f"  {date}: настр. {mood_str}, "
                    f"впеч. {impressions}, опр. {surveys}"
                )

            message_lines.append("")

        # Корреляционный анализ
        correlation_data = get_correlation_data(conn, chat_id, period_days)

        if correlation_data and any(d['mood_score'] is not None for d in correlation_data):
            message_lines.append("🔗 *Корреляции:*")

            # Анализируем связь между настроением и позитивными впечатлениями
            days_with_mood = [d for d in correlation_data if d['mood_score'] is not None]

            if days_with_mood:
                avg_positive_on_good_days = 0
                avg_positive_on_bad_days = 0
                good_days_count = 0
                bad_days_count = 0

                for day in days_with_mood:
                    if day['mood_score'] >= 7:  # Хороший день
                        avg_positive_on_good_days += day['positive_count']
                        good_days_count += 1
                    elif day['mood_score'] <= 4:  # Плохой день
                        avg_positive_on_bad_days += day['positive_count']
                        bad_days_count += 1

                if good_days_count > 0 and bad_days_count > 0:
                    avg_positive_on_good_days /= good_days_count
                    avg_positive_on_bad_days /= bad_days_count

                    message_lines.append(
                        f"  В хорошие дни (настр. ≥7): {avg_positive_on_good_days:.1f} позит. впеч."
                    )
                    message_lines.append(
                        f"  В плохие дни (настр. ≤4): {avg_positive_on_bad_days:.1f} позит. впеч."
                    )

            message_lines.append("")

        # Подсказки
        message_lines.append("💡 *Подсказки:*")
        message_lines.append("  • Используйте /impression_analytics для детальной статистики впечатлений")
        message_lines.append("  • Используйте /survey_stats для аналитики опросов")
        message_lines.append(f"  • Изменить период: /combined_analytics --period <дней>")

        await update.message.reply_text(
            "\n".join(message_lines),
            parse_mode='Markdown'
        )

        logger.info(f"Пользователь {chat_id} запросил объединенную аналитику за {period_days} дней")

    except Exception as e:
        logger.error(f"Ошибка при получении объединенной аналитики для {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при получении аналитики.\n"
            "Попробуйте позже."
        )
    finally:
        conn.close()


def _get_mood_emoji(mood_score: float) -> str:
    """Возвращает emoji в зависимости от оценки настроения."""
    if mood_score >= 8:
        return "😊"
    elif mood_score >= 6:
        return "🙂"
    elif mood_score >= 4:
        return "😐"
    else:
        return "😔"


def register(application: Application) -> None:
    """Регистрирует handlers в приложении."""
    application.add_handler(CommandHandler('combined_analytics', combined_analytics_handler))

    logger.info("Зарегистрированы handlers для объединенной аналитики")
