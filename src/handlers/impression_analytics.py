"""
Handlers для аналитики впечатлений (Phase 4.1).

Команды:
- /impression_analytics - показать аналитику впечатлений
"""

import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.data.impressions_storage import get_user_impressions

logger = logging.getLogger(__name__)

# Константы для времени суток
TIME_PERIODS = {
    'night': (0, 6),    # Ночь: 00:00-06:00
    'morning': (6, 12),  # Утро: 06:00-12:00
    'afternoon': (12, 18),  # День: 12:00-18:00
    'evening': (18, 24)  # Вечер: 18:00-24:00
}

TIME_PERIOD_NAMES = {
    'night': '🌙 Ночь',
    'morning': '🌅 Утро',
    'afternoon': '☀️ День',
    'evening': '🌆 Вечер'
}

CATEGORY_EMOJI = {
    'positive': '😊',
    'negative': '😔',
    'neutral': '😐'
}

CATEGORY_NAMES = {
    'positive': 'Позитивные',
    'negative': 'Негативные',
    'neutral': 'Нейтральные'
}

WEEKDAY_NAMES = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']


def parse_analytics_args(args: List[str]) -> Dict[str, Any]:
    """
    Парсит аргументы команды аналитики.

    Поддерживаемые аргументы:
    - --period N: последние N дней
    - --from DATE --to DATE: произвольный период
    - --category CATEGORY: фильтрация по категории
    - --detailed: детальная статистика
    """
    parsed = {
        'period_days': 7,  # По умолчанию 7 дней
        'date_from': None,
        'date_to': None,
        'category': None,
        'detailed': False
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

        elif arg == '--from' and i + 1 < len(args):
            parsed['date_from'] = args[i + 1]
            i += 2

        elif arg == '--to' and i + 1 < len(args):
            parsed['date_to'] = args[i + 1]
            i += 2

        elif arg == '--category' and i + 1 < len(args):
            parsed['category'] = args[i + 1]
            i += 2

        elif arg == '--detailed':
            parsed['detailed'] = True
            i += 1

        else:
            i += 1

    return parsed


def filter_impressions_by_period(
    impressions: List[Dict],
    period_days: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> List[Dict]:
    """Фильтрует впечатления по периоду."""
    if not impressions:
        return []

    now = datetime.now()

    # Определяем диапазон дат
    if date_from and date_to:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            # Если формат неверный, используем period_days
            start_date = now - timedelta(days=period_days or 7)
            end_date = now
    else:
        start_date = now - timedelta(days=period_days or 7)
        end_date = now

    # Фильтруем
    filtered = []
    for imp in impressions:
        try:
            created_at = datetime.strptime(imp['created_at'], '%Y-%m-%d %H:%M:%S')
            if start_date <= created_at <= end_date:
                filtered.append(imp)
        except (ValueError, KeyError):
            continue

    return filtered


def calculate_category_stats(impressions: List[Dict]) -> Dict[str, Dict[str, Any]]:
    """Подсчитывает статистику по категориям."""
    stats = defaultdict(lambda: {'count': 0, 'intensities': []})

    for imp in impressions:
        category = imp.get('category', 'neutral')
        stats[category]['count'] += 1

        intensity = imp.get('intensity')
        if intensity is not None:
            stats[category]['intensities'].append(intensity)

    # Вычисляем средние интенсивности
    for category, data in stats.items():
        if data['intensities']:
            data['avg_intensity'] = sum(data['intensities']) / len(data['intensities'])
        else:
            data['avg_intensity'] = 0

    return dict(stats)


def calculate_tag_frequency(impressions: List[Dict]) -> List[tuple]:
    """Подсчитывает частоту тегов."""
    all_tags = []

    for imp in impressions:
        tags = imp.get('tags', [])
        if tags:
            all_tags.extend(tags)

    tag_counter = Counter(all_tags)
    return tag_counter.most_common(10)  # Топ 10 тегов


def calculate_time_of_day_distribution(impressions: List[Dict]) -> Dict[str, int]:
    """Распределение по времени суток."""
    distribution = {period: 0 for period in TIME_PERIODS.keys()}

    for imp in impressions:
        try:
            created_at = datetime.strptime(imp['created_at'], '%Y-%m-%d %H:%M:%S')
            hour = created_at.hour

            for period, (start_hour, end_hour) in TIME_PERIODS.items():
                if start_hour <= hour < end_hour:
                    distribution[period] += 1
                    break
        except (ValueError, KeyError):
            continue

    return distribution


def calculate_weekday_distribution(impressions: List[Dict]) -> Dict[int, int]:
    """Распределение по дням недели."""
    distribution = defaultdict(int)

    for imp in impressions:
        try:
            created_at = datetime.strptime(imp['created_at'], '%Y-%m-%d %H:%M:%S')
            weekday = created_at.weekday()  # 0=Monday, 6=Sunday
            distribution[weekday] += 1
        except (ValueError, KeyError):
            continue

    return dict(distribution)


def calculate_intensity_trend(impressions: List[Dict]) -> List[float]:
    """Вычисляет тренд интенсивности."""
    if not impressions:
        return []

    # Сортируем по дате
    sorted_impressions = sorted(
        impressions,
        key=lambda x: x.get('created_at', '')
    )

    # Извлекаем интенсивности
    intensities = [
        imp.get('intensity', 0)
        for imp in sorted_impressions
        if imp.get('intensity') is not None
    ]

    return intensities


def format_analytics_message(
    impressions: List[Dict],
    category_stats: Dict,
    tag_frequency: List[tuple],
    time_distribution: Dict,
    weekday_distribution: Dict,
    intensities: List[float],
    args: Dict[str, Any]
) -> str:
    """Форматирует сообщение с аналитикой."""
    if not impressions:
        return (
            "📊 *Аналитика впечатлений*\n\n"
            "❌ Нет данных за выбранный период.\n\n"
            "Добавьте впечатления: /impression"
        )

    # Заголовок
    period_text = f"последние {args['period_days']} дней"
    if args.get('date_from') and args.get('date_to'):
        period_text = f"{args['date_from']} — {args['date_to']}"

    message = [
        "📊 *Аналитика впечатлений*",
        f"📅 Период: {period_text}",
        ""
    ]

    # Общая статистика
    total_count = len(impressions)
    all_intensities = [imp.get('intensity', 0) for imp in impressions if imp.get('intensity') is not None]
    avg_intensity = sum(all_intensities) / len(all_intensities) if all_intensities else 0

    message.extend([
        "*📈 Общая статистика:*",
        f"• Всего впечатлений: *{total_count}*",
        f"• Средняя интенсивность: *{avg_intensity:.1f}/10*",
        ""
    ])

    # Статистика по категориям
    if category_stats:
        message.append("*🎭 По категориям:*")

        for category in ['positive', 'negative', 'neutral']:
            if category in category_stats:
                stats = category_stats[category]
                emoji = CATEGORY_EMOJI.get(category, '•')
                name = CATEGORY_NAMES.get(category, category)
                count = stats['count']
                avg = stats['avg_intensity']
                percentage = (count / total_count * 100) if total_count > 0 else 0

                message.append(
                    f"{emoji} {name}: *{count}* ({percentage:.0f}%) — "
                    f"интенсивность {avg:.1f}"
                )

        message.append("")

    # Топ тегов
    if tag_frequency:
        message.append("*🏷 Популярные теги:*")
        for tag, count in tag_frequency[:5]:
            message.append(f"• #{tag}: *{count}*")
        message.append("")

    # Распределение по времени суток (в детальном режиме)
    if args.get('detailed') and time_distribution:
        message.append("*🕐 Время суток:*")
        for period in ['morning', 'afternoon', 'evening', 'night']:
            count = time_distribution.get(period, 0)
            if count > 0:
                name = TIME_PERIOD_NAMES.get(period, period)
                percentage = (count / total_count * 100) if total_count > 0 else 0
                message.append(f"{name}: *{count}* ({percentage:.0f}%)")
        message.append("")

    # Распределение по дням недели (в детальном режиме)
    if args.get('detailed') and weekday_distribution:
        message.append("*📅 По дням недели:*")
        for weekday in range(7):
            count = weekday_distribution.get(weekday, 0)
            if count > 0:
                day_name = WEEKDAY_NAMES[weekday]
                message.append(f"{day_name}: *{count}*")
        message.append("")

    # Тренд интенсивности
    if intensities and len(intensities) >= 2:
        first_half = intensities[:len(intensities) // 2]
        second_half = intensities[len(intensities) // 2:]

        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0

        trend_diff = avg_second - avg_first

        message.append("*📊 Динамика:*")
        if trend_diff > 0.5:
            message.append(f"📈 Растущий тренд (+{trend_diff:.1f})")
        elif trend_diff < -0.5:
            message.append(f"📉 Снижающийся тренд ({trend_diff:.1f})")
        else:
            message.append("➡️ Стабильный тренд")
        message.append("")

    # Подсказки
    message.extend([
        "_Используйте флаги:_",
        "_• --period N (дни)_",
        "_• --detailed (детальная статистика)_",
        "_• --category positive/negative/neutral_"
    ])

    return "\n".join(message)


async def show_impression_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает аналитику по впечатлениям - /impression_analytics.

    Аргументы:
    - --period N: последние N дней (по умолчанию 7)
    - --from DATE --to DATE: произвольный период
    - --category CATEGORY: фильтрация по категории
    - --detailed: детальная статистика
    """
    chat_id = update.effective_chat.id

    try:
        # Парсим аргументы
        args = parse_analytics_args(context.args)

        # Получаем все впечатления пользователя
        from src.data.storage import _get_db_connection
        conn = _get_db_connection()

        all_impressions = get_user_impressions(conn, chat_id)

        # Фильтруем по периоду
        impressions = filter_impressions_by_period(
            all_impressions,
            period_days=args['period_days'],
            date_from=args.get('date_from'),
            date_to=args.get('date_to')
        )

        # Фильтруем по категории (если указана)
        if args.get('category'):
            impressions = [
                imp for imp in impressions
                if imp.get('category') == args['category']
            ]

        # Вычисляем статистики
        category_stats = calculate_category_stats(impressions)
        tag_frequency = calculate_tag_frequency(impressions)
        time_distribution = calculate_time_of_day_distribution(impressions)
        weekday_distribution = calculate_weekday_distribution(impressions)
        intensities = calculate_intensity_trend(impressions)

        # Форматируем сообщение
        message = format_analytics_message(
            impressions,
            category_stats,
            tag_frequency,
            time_distribution,
            weekday_distribution,
            intensities,
            args
        )

        await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Ошибка при формировании аналитики впечатлений: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при формировании аналитики.\n"
            "Попробуйте позже."
        )


def register(application) -> None:
    """Регистрирует handlers для аналитики впечатлений."""
    application.add_handler(CommandHandler('impression_analytics', show_impression_analytics))

    logger.info("Impression analytics handlers зарегистрированы")
