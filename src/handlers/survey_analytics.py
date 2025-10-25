"""
Handlers для аналитики опросов (Phase 4.2).

Команды:
- /survey_stats <название> - показать аналитику по опросу
"""

import logging
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.data.storage import _get_db_connection
from src.data.surveys_storage import (
    get_available_templates,
    get_template_questions,
    get_user_survey_responses
)

logger = logging.getLogger(__name__)


def parse_survey_args(args: List[str]) -> tuple:
    """
    Парсит аргументы команды аналитики опросов.

    Returns:
        (survey_name, options_dict)
    """
    if not args:
        return None, {}

    # Ищем флаги
    flags = {}
    name_parts = []

    i = 0
    while i < len(args):
        if args[i] == '--period' and i + 1 < len(args):
            try:
                flags['period_days'] = int(args[i + 1])
                i += 2
            except ValueError:
                i += 1
        else:
            name_parts.append(args[i])
            i += 1

    survey_name = ' '.join(name_parts) if name_parts else None
    flags.setdefault('period_days', 30)  # По умолчанию 30 дней

    return survey_name, flags


def filter_responses_by_period(responses: List[Dict], period_days: int) -> List[Dict]:
    """Фильтрует ответы по периоду."""
    if not responses or not period_days:
        return responses

    cutoff_date = datetime.now() - timedelta(days=period_days)

    filtered = []
    for resp in responses:
        try:
            completed_at = datetime.strptime(resp['completed_at'], '%Y-%m-%d %H:%M:%S')
            if completed_at >= cutoff_date:
                filtered.append(resp)
        except (ValueError, KeyError):
            continue

    return filtered


def analyze_numeric_question(
    question: Dict,
    responses: List[Dict]
) -> Dict[str, Any]:
    """Анализирует числовой вопрос."""
    question_id = str(question['id'])
    values = []

    for resp in responses:
        answers = resp.get('answers', {})
        if question_id in answers:
            try:
                value = float(answers[question_id])
                values.append(value)
            except (ValueError, TypeError):
                continue

    if not values:
        return {'count': 0}

    # Статистика
    stats = {
        'count': len(values),
        'avg': sum(values) / len(values),
        'min': min(values),
        'max': max(values),
        'values': values
    }

    # Тренд (сравнение первой и второй половины)
    if len(values) >= 4:
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid
        second_half_avg = sum(values[mid:]) / (len(values) - mid)
        trend_diff = second_half_avg - first_half_avg

        if trend_diff > 0.5:
            stats['trend'] = 'растущий'
            stats['trend_emoji'] = '📈'
        elif trend_diff < -0.5:
            stats['trend'] = 'снижающийся'
            stats['trend_emoji'] = '📉'
        else:
            stats['trend'] = 'стабильный'
            stats['trend_emoji'] = '➡️'
    else:
        stats['trend'] = 'недостаточно данных'
        stats['trend_emoji'] = '❓'

    return stats


def analyze_choice_question(
    question: Dict,
    responses: List[Dict]
) -> Dict[str, Any]:
    """Анализирует вопрос с выбором."""
    question_id = str(question['id'])
    all_choices = []

    for resp in responses:
        answers = resp.get('answers', {})
        if question_id in answers:
            answer = answers[question_id]
            # Ответ может быть списком через запятую
            if ',' in answer:
                choices = [c.strip() for c in answer.split(',')]
                all_choices.extend(choices)
            else:
                all_choices.append(answer.strip())

    if not all_choices:
        return {'count': 0}

    # Частота выбора
    choice_counter = Counter(all_choices)
    total_responses = len([r for r in responses if question_id in r.get('answers', {})])

    stats = {
        'count': total_responses,
        'total_choices': len(all_choices),
        'choices': []
    }

    for choice, count in choice_counter.most_common():
        percentage = (count / total_responses * 100) if total_responses > 0 else 0
        stats['choices'].append({
            'text': choice,
            'count': count,
            'percentage': percentage
        })

    return stats


def analyze_yes_no_question(
    question: Dict,
    responses: List[Dict]
) -> Dict[str, Any]:
    """Анализирует yes/no вопрос."""
    question_id = str(question['id'])
    yes_count = 0
    no_count = 0

    for resp in responses:
        answers = resp.get('answers', {})
        if question_id in answers:
            answer = answers[question_id].lower()
            if answer in ['да', 'yes', 'y']:
                yes_count += 1
            elif answer in ['нет', 'no', 'n']:
                no_count += 1

    total = yes_count + no_count

    return {
        'count': total,
        'yes_count': yes_count,
        'no_count': no_count,
        'yes_percentage': (yes_count / total * 100) if total > 0 else 0,
        'no_percentage': (no_count / total * 100) if total > 0 else 0
    }


def detect_cbt_pattern(questions: List[Dict]) -> Optional[tuple]:
    """
    Определяет паттерн КПТ дневника (вопросы 'до' и 'после').

    Returns:
        (before_question_id, after_question_id) или None
    """
    before_q = None
    after_q = None

    for q in questions:
        text = q.get('question_text', '').lower()
        if '(до)' in text or 'до' in text and ('интенсивн' in text or 'уровень' in text):
            before_q = q
        elif '(после)' in text or 'после' in text and ('интенсивн' in text or 'уровень' in text):
            after_q = q

    if before_q and after_q:
        return (str(before_q['id']), str(after_q['id']))

    return None


def analyze_cbt_before_after(
    before_q_id: str,
    after_q_id: str,
    responses: List[Dict]
) -> Dict[str, Any]:
    """Анализ КПТ: сравнение до/после."""
    before_values = []
    after_values = []
    improvements = []

    for resp in responses:
        answers = resp.get('answers', {})
        if before_q_id in answers and after_q_id in answers:
            try:
                before = float(answers[before_q_id])
                after = float(answers[after_q_id])
                before_values.append(before)
                after_values.append(after)
                improvements.append(before - after)
            except (ValueError, TypeError):
                continue

    if not before_values:
        return {'count': 0}

    avg_before = sum(before_values) / len(before_values)
    avg_after = sum(after_values) / len(after_values)
    avg_improvement = sum(improvements) / len(improvements)

    return {
        'count': len(before_values),
        'avg_before': avg_before,
        'avg_after': avg_after,
        'avg_improvement': avg_improvement,
        'improvement_percentage': (avg_improvement / avg_before * 100) if avg_before > 0 else 0
    }


def detect_addiction_pattern(questions: List[Dict]) -> Optional[tuple]:
    """
    Определяет паттерн дневника зависимости.

    Returns:
        (craving_question_id, relapse_question_id) или None
    """
    craving_q = None
    relapse_q = None

    for q in questions:
        text = q.get('question_text', '').lower()
        if 'тяг' in text or 'craving' in text:
            craving_q = q
        elif 'срыв' in text or 'relapse' in text:
            relapse_q = q

    if craving_q:
        return (str(craving_q['id']), str(relapse_q['id']) if relapse_q else None)

    return None


def analyze_addiction_craving(
    craving_q_id: str,
    relapse_q_id: Optional[str],
    responses: List[Dict]
) -> Dict[str, Any]:
    """Анализ тяги и срывов."""
    craving_values = []
    relapse_count = 0

    for resp in responses:
        answers = resp.get('answers', {})

        # Тяга
        if craving_q_id in answers:
            try:
                value = float(answers[craving_q_id])
                craving_values.append(value)
            except (ValueError, TypeError):
                pass

        # Срывы
        if relapse_q_id and relapse_q_id in answers:
            answer = answers[relapse_q_id].lower()
            if answer in ['да', 'yes', 'y']:
                relapse_count += 1

    if not craving_values:
        return {'count': 0}

    # Тренд тяги
    avg_craving = sum(craving_values) / len(craving_values)

    if len(craving_values) >= 4:
        mid = len(craving_values) // 2
        first_half_avg = sum(craving_values[:mid]) / mid
        second_half_avg = sum(craving_values[mid:]) / (len(craving_values) - mid)
        trend_diff = second_half_avg - first_half_avg

        if trend_diff < -0.5:
            trend = 'снижается'
            trend_emoji = '📉'
        elif trend_diff > 0.5:
            trend = 'растет'
            trend_emoji = '📈'
        else:
            trend = 'стабильна'
            trend_emoji = '➡️'
    else:
        trend = 'недостаточно данных'
        trend_emoji = '❓'

    return {
        'count': len(craving_values),
        'avg_craving': avg_craving,
        'min_craving': min(craving_values),
        'max_craving': max(craving_values),
        'trend': trend,
        'trend_emoji': trend_emoji,
        'relapse_count': relapse_count,
        'relapse_percentage': (relapse_count / len(responses) * 100) if responses else 0
    }


def format_survey_stats_message(
    template: Dict,
    questions: List[Dict],
    responses: List[Dict],
    options: Dict
) -> str:
    """Форматирует сообщение с аналитикой опроса."""
    if not responses:
        return (
            f"📊 *Статистика: {template['name']}*\n\n"
            f"❌ Нет ответов за выбранный период.\n\n"
            f"Заполнить опрос: /fill {template['name']}"
        )

    message = [
        f"📊 *Статистика: {template['name']}*",
        f"📅 Период: последние {options.get('period_days', 30)} дней",
        f"📝 Ответов: *{len(responses)}*",
        ""
    ]

    # Проверка на специальные паттерны
    cbt_pattern = detect_cbt_pattern(questions)
    addiction_pattern = detect_addiction_pattern(questions)

    # Специальная аналитика для КПТ
    if cbt_pattern:
        before_id, after_id = cbt_pattern
        cbt_stats = analyze_cbt_before_after(before_id, after_id, responses)

        if cbt_stats['count'] > 0:
            message.extend([
                "*🧠 КПТ Анализ: До/После*",
                f"• Средняя оценка ДО: *{cbt_stats['avg_before']:.1f}*",
                f"• Средняя оценка ПОСЛЕ: *{cbt_stats['avg_after']:.1f}*",
                f"• Среднее улучшение: *{cbt_stats['avg_improvement']:.1f}* ({cbt_stats['improvement_percentage']:.0f}%)",
                ""
            ])

    # Специальная аналитика для дневника зависимости
    if addiction_pattern:
        craving_id, relapse_id = addiction_pattern
        addiction_stats = analyze_addiction_craving(craving_id, relapse_id, responses)

        if addiction_stats['count'] > 0:
            message.extend([
                "*💪 Анализ тяги:*",
                f"• Средняя тяга: *{addiction_stats['avg_craving']:.1f}/10*",
                f"• Диапазон: {addiction_stats['min_craving']:.0f} - {addiction_stats['max_craving']:.0f}",
                f"• Тренд: {addiction_stats['trend_emoji']} {addiction_stats['trend']}",
                f"• Срывов: *{addiction_stats['relapse_count']}* ({addiction_stats['relapse_percentage']:.0f}%)",
                ""
            ])

    # Аналитика по вопросам
    for question in questions:
        q_type = question.get('question_type')
        q_text = question.get('question_text', 'Вопрос')

        if q_type in ['numeric', 'scale']:
            stats = analyze_numeric_question(question, responses)
            if stats['count'] > 0:
                message.extend([
                    f"*📊 {q_text}*",
                    f"• Среднее: *{stats['avg']:.1f}*",
                    f"• Диапазон: {stats['min']:.1f} - {stats['max']:.1f}",
                    f"• Тренд: {stats['trend_emoji']} {stats['trend']}",
                    ""
                ])

        elif q_type == 'choice':
            stats = analyze_choice_question(question, responses)
            if stats['count'] > 0:
                message.append(f"*☑️ {q_text}*")
                for choice_data in stats['choices'][:5]:  # Топ 5
                    message.append(
                        f"• {choice_data['text']}: *{choice_data['count']}* ({choice_data['percentage']:.0f}%)"
                    )
                message.append("")

        elif q_type == 'yes_no':
            stats = analyze_yes_no_question(question, responses)
            if stats['count'] > 0:
                message.extend([
                    f"*✅ {q_text}*",
                    f"• Да: *{stats['yes_count']}* ({stats['yes_percentage']:.0f}%)",
                    f"• Нет: *{stats['no_count']}* ({stats['no_percentage']:.0f}%)",
                    ""
                ])

    message.extend([
        "_Используйте флаги:_",
        "_• --period N (дни, по умолчанию 30)_"
    ])

    return "\n".join(message)


async def show_survey_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает статистику по опросу - /survey_stats <название>.

    Аргументы:
    - <название>: название опроса
    - --period N: период в днях (по умолчанию 30)
    """
    chat_id = update.effective_chat.id

    # Парсим аргументы
    survey_name, options = parse_survey_args(context.args)

    if not survey_name:
        await update.message.reply_text(
            "❌ Укажите название опроса.\n\n"
            "Использование: /survey_stats <название>\n\n"
            "Посмотреть доступные опросы: /surveys"
        )
        return

    try:
        conn = _get_db_connection()

        # Находим шаблон
        templates = get_available_templates(conn)
        template = next((t for t in templates if t['name'] == survey_name), None)

        if not template:
            await update.message.reply_text(
                f"❌ Опрос *{survey_name}* не найден.\n\n"
                f"Посмотреть доступные опросы: /surveys",
                parse_mode='Markdown'
            )
            return

        # Получаем вопросы
        questions = get_template_questions(conn, template['id'])

        # Получаем ответы пользователя
        all_responses = get_user_survey_responses(conn, chat_id, template['id'])

        # Фильтруем по периоду
        responses = filter_responses_by_period(all_responses, options.get('period_days', 30))

        # Форматируем сообщение
        message = format_survey_stats_message(template, questions, responses, options)

        await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Ошибка при формировании статистики опроса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при формировании статистики.\n"
            "Попробуйте позже."
        )


def register(application) -> None:
    """Регистрирует handlers для аналитики опросов."""
    application.add_handler(CommandHandler('survey_stats', show_survey_stats))

    logger.info("Survey analytics handlers зарегистрированы")
