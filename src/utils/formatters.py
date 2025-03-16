"""
Модуль с функциями для форматирования вывода данных.
"""

import pandas as pd
from typing import Dict, Any, List
from src.utils.date_helpers import format_date


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
            # Форматирование даты в более читаемый вид (ДД.ММ.ГГГГ)
            formatted_date = format_date(entry['date'])

            result += f"📅 {formatted_date}\n"
            result += f"😊 Настроение: {entry['mood']}/10\n"

            # Добавляем комментарий, если он есть
            if entry.get('comment'):
                # Ограничиваем длину комментария для компактности
                comment = entry['comment']
                if len(comment) > 50:
                    comment = comment[:47] + "..."
                result += f"💬 {comment}\n"

            # Добавляем сон, тревогу и депрессию (как наиболее важные показатели)
            result += f"😴 Сон: {entry['sleep']}/10\n"
            result += f"😰 Тревога: {entry['anxiety']}/10\n"
            result += f"😞 Депрессия: {entry['depression']}/10\n"

            result += "-------------------\n\n"
        except Exception as e:
            # В случае проблем с форматированием отдельной записи, пропускаем ее
            continue

    if len(sorted_entries) > max_entries:
        result += f"\nИ еще {len(sorted_entries) - max_entries} записей. Используйте /download для выгрузки всего дневника."

    return result