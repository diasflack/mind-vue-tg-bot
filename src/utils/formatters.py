"""
Модуль с функциями для форматирования вывода данных.
"""

import pandas as pd
from typing import Dict, Any, List


def format_entry_summary(entry: Dict[str, Any]) -> str:
    """
    Форматирует сводку записи для вывода пользователю.
    
    Args:
        entry: запись для форматирования
        
    Returns:
        str: форматированная сводка записи
    """
    summary = f"Запись успешно сохранена и зашифрована!\n\n"
    summary += f"Дата: {entry['date']}\n"
    summary += f"Настроение: {entry['mood']}\n"
    summary += f"Сон: {entry['sleep']}\n"
    
    if entry.get('comment'):
        summary += f"Комментарий: {entry['comment']}\n"
    
    summary += f"Ровность настроения: {entry['balance']}\n"
    summary += f"Мания: {entry['mania']}\n"
    summary += f"Депрессия: {entry['depression']}\n"
    summary += f"Тревога: {entry['anxiety']}\n"
    summary += f"Раздражительность: {entry['irritability']}\n"
    summary += f"Работоспособность: {entry['productivity']}\n"
    summary += f"Общительность: {entry['sociability']}\n"
    
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
    
    stats_text = "Статистика:\n"
    for col in numeric_columns:
        if col in entries_df.columns:
            col_data = pd.to_numeric(entries_df[col], errors='coerce')
            if not col_data.isna().all():
                avg = col_data.mean()
                stats_text += f"{get_column_name(col)}: среднее = {avg:.2f}\n"
    
    stats_text += f"\nВсего записей: {len(entries_df)}"
    
    # Добавление диапазона дат
    if 'date' in entries_df.columns and len(entries_df) > 0:
        start_date = pd.to_datetime(entries_df['date']).min().strftime('%Y-%m-%d')
        end_date = pd.to_datetime(entries_df['date']).max().strftime('%Y-%m-%d')
        stats_text += f"\nПериод: с {start_date} по {end_date}"
    
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
        'mood': 'Настроение',
        'sleep': 'Сон',
        'balance': 'Ровность настроения',
        'mania': 'Мания',
        'depression': 'Депрессия',
        'anxiety': 'Тревога',
        'irritability': 'Раздражительность',
        'productivity': 'Работоспособность',
        'sociability': 'Общительность'
    }
    
    return column_names.get(column, column)
