"""
Модуль с функциями для форматирования вывода данных.
"""

import pandas as pd
from typing import Dict, Any, List, Optional
import sqlite3
from src.utils.date_helpers import format_date


def enrich_entries_with_impressions(
    entries: List[Dict[str, Any]],
    chat_id: int,
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """
    Обогащает записи привязанными впечатлениями.

    Args:
        entries: список записей
        chat_id: ID пользователя
        conn: соединение с БД (опционально)

    Returns:
        List[Dict]: записи с добавленным полем 'impressions'
    """
    if not entries or not conn:
        return entries

    try:
        from src.data.impressions_storage import get_entry_impressions

        enriched_entries = []
        for entry in entries:
            entry_copy = entry.copy()
            # Получаем впечатления для этой даты
            impressions = get_entry_impressions(conn, chat_id, entry['date'])
            entry_copy['impressions'] = impressions
            enriched_entries.append(entry_copy)

        return enriched_entries

    except Exception:
        # В случае ошибки возвращаем исходные записи
        return entries


def format_entry_summary(entry: Dict[str, Any]) -> str:
    """
    Форматирует сводку записи для вывода пользователю.

    Args:
        entry: запись для форматирования

    Returns:
        str: форматированная сводка записи
    """
    # Форматирование даты в более читаемый вид (ДД.ММ.ГГГГ)
    formatted_date = format_date(entry['date'])

    summary = f"✅ Запись успешно сохранена и зашифрована!\n\n"
    summary += f"📅 Дата: {formatted_date}\n"
    summary += f"😊 Настроение: {entry['mood']}/10\n"
    summary += f"😴 Сон: {entry['sleep']}/10\n"

    if entry.get('comment'):
        summary += f"💬 Комментарий: {entry['comment']}\n"

    summary += f"⚖️ Ровность настроения: {entry['balance']}/10\n"
    summary += f"🔆 Мания: {entry['mania']}/10\n"
    summary += f"😞 Депрессия: {entry['depression']}/10\n"
    summary += f"😰 Тревога: {entry['anxiety']}/10\n"
    summary += f"😠 Раздражительность: {entry['irritability']}/10\n"
    summary += f"📊 Работоспособность: {entry['productivity']}/10\n"
    summary += f"👋 Общительность: {entry['sociability']}/10\n"

    return summary


def format_stats_summary(entries_df: pd.DataFrame) -> str:
    """
    Форматирует статистику по записям для вывода пользователю.

    Args:
        entries_df: DataFrame с записями

    Returns:
        str: форматированная статистика
    """
    numeric_columns = ['mood', 'sleep', 'balance', 'mania',
                       'depression', 'anxiety', 'irritability',
                       'productivity', 'sociability']

    stats_text = "📊 Статистика:\n\n"
    for col in numeric_columns:
        if col in entries_df.columns:
            col_data = pd.to_numeric(entries_df[col], errors='coerce')
            if not col_data.isna().all():
                avg = col_data.mean()
                stats_text += f"{get_column_name(col)}: среднее = {avg:.2f}/10\n"

    stats_text += f"\n📝 Всего записей: {len(entries_df)}"

    # Добавление диапазона дат
    if 'date' in entries_df.columns and len(entries_df) > 0:
        start_date = pd.to_datetime(entries_df['date']).min().strftime('%d.%m.%Y')
        end_date = pd.to_datetime(entries_df['date']).max().strftime('%d.%m.%Y')
        stats_text += f"\n📅 Период: с {start_date} по {end_date}"

    return stats_text


def get_column_name(column: str) -> str:
    """
    Возвращает русское название колонки для вывода.

    Args:
        column: название колонки в базе данных

    Returns:
        str: русское название колонки
    """
    column_names = {
        'mood': '😊 Настроение',
        'sleep': '😴 Сон',
        'balance': '⚖️ Ровность настроения',
        'mania': '🔆 Мания',
        'depression': '😞 Депрессия',
        'anxiety': '😰 Тревога',
        'irritability': '😠 Раздражительность',
        'productivity': '📊 Работоспособность',
        'sociability': '👋 Общительность'
    }

    return column_names.get(column, column)


def _format_comment_preview(comment: str, max_length: int = 50) -> str:
    """
    Форматирует комментарий с ограничением длины.

    Args:
        comment: текст комментария
        max_length: максимальная длина комментария

    Returns:
        str: отформатированный комментарий с многоточием если необходимо
    """
    if len(comment) > max_length:
        return comment[:max_length - 3] + "..."
    return comment


def _format_single_entry(entry: Dict[str, Any]) -> str:
    """
    Форматирует одну запись дневника для отображения.

    Args:
        entry: словарь с данными записи

    Returns:
        str: отформатированная запись
    """
    # Форматирование даты в более читаемый вид (ДД.ММ.ГГГГ)
    formatted_date = format_date(entry['date'])

    result = f"📅 {formatted_date}\n"
    result += f"😊 Настроение: {entry['mood']}/10\n"

    # Добавляем комментарий, если он есть
    if entry.get('comment'):
        comment_preview = _format_comment_preview(entry['comment'])
        result += f"💬 {comment_preview}\n"

    # Добавляем сон, тревогу и депрессию (как наиболее важные показатели)
    result += f"😴 Сон: {entry['sleep']}/10\n"
    result += f"😰 Тревога: {entry['anxiety']}/10\n"
    result += f"😞 Депрессия: {entry['depression']}/10\n"

    # Добавляем привязанные впечатления, если есть
    if entry.get('impressions'):
        impressions = entry['impressions']
        result += f"\n💭 Впечатлений: {len(impressions)}\n"
        for imp in impressions[:3]:  # Показываем максимум 3
            category_emoji = {'positive': '😊', 'negative': '😞', 'neutral': '😐'}.get(imp.get('category'), '💭')
            text_preview = imp['text'][:40] + '...' if len(imp['text']) > 40 else imp['text']
            result += f"  {category_emoji} {text_preview} (ID: {imp['id']})\n"
        if len(impressions) > 3:
            result += f"  ... и еще {len(impressions) - 3}\n"

    result += "-------------------\n\n"

    return result


def format_entry_list(entries: List[Dict[str, Any]], max_entries: int = 5) -> str:
    """
    Форматирует список последних записей для вывода пользователю.

    Args:
        entries: список записей для форматирования
        max_entries: максимальное количество записей для отображения

    Returns:
        str: форматированный список записей
    """
    if not entries:
        return "У вас еще нет записей в дневнике."

    # Сортировка записей по дате (от новых к старым)
    try:
        sorted_entries = sorted(entries, key=lambda x: x['date'], reverse=True)
    except Exception:
        # Если не получилось отсортировать, используем исходный порядок
        sorted_entries = entries

    # Ограничение количества отображаемых записей
    display_entries = sorted_entries[:max_entries]

    result = f"📝 Последние {len(display_entries)} записей:\n\n"

    for entry in display_entries:
        try:
            result += _format_single_entry(entry)
        except Exception:
            # В случае проблем с форматированием отдельной записи, пропускаем ее
            continue

    if len(sorted_entries) > max_entries:
        result += f"\nИ еще {len(sorted_entries) - max_entries} записей. Используйте /download для выгрузки всего дневника."

    return result