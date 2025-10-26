"""
Модуль для объединенной аналитики впечатлений и опросов (Phase 5.5).

Функции для получения комплексной аналитики из обоих источников данных.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def get_combined_daily_summary(
    conn: sqlite3.Connection,
    chat_id: int,
    days: int = 7
) -> List[Dict[str, Any]]:
    """
    Получает объединенную дневную статистику за период.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        days: количество дней для анализа

    Returns:
        List[Dict]: список дневных сводок с данными из обоих источников
    """
    cursor = conn.cursor()

    # Вычисляем период
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days - 1)

    try:
        # Получаем данные за период
        cursor.execute('''
            SELECT
                e.date,
                e.mood_score,
                COUNT(DISTINCT i.id) as impressions_count,
                COUNT(DISTINCT sr.id) as surveys_count
            FROM entries e
            LEFT JOIN impressions i ON e.chat_id = i.chat_id AND e.date = i.entry_date
            LEFT JOIN survey_responses sr ON e.chat_id = sr.chat_id AND DATE(e.date) = DATE(sr.completed_at)
            WHERE e.chat_id = ?
                AND e.date >= ?
                AND e.date <= ?
            GROUP BY e.date
            ORDER BY e.date DESC
        ''', (chat_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

        rows = cursor.fetchall()

        summary = []
        for row in rows:
            summary.append({
                'date': row[0],
                'mood_score': row[1],
                'impressions_count': row[2],
                'surveys_count': row[3]
            })

        return summary

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении объединенной статистики: {e}")
        return []


def get_activity_overview(
    conn: sqlite3.Connection,
    chat_id: int,
    days: int = 7
) -> Dict[str, Any]:
    """
    Получает общий обзор активности за период.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        days: количество дней для анализа

    Returns:
        Dict: обзор активности с агрегированными данными
    """
    cursor = conn.cursor()

    # Вычисляем период
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days - 1)

    overview = {
        'total_impressions': 0,
        'total_surveys': 0,
        'total_entries': 0,
        'avg_mood_score': None,
        'impression_categories': {
            'positive': 0,
            'negative': 0,
            'neutral': 0
        }
    }

    try:
        # Подсчет впечатлений
        cursor.execute('''
            SELECT COUNT(*) FROM impressions
            WHERE chat_id = ?
                AND created_at >= ?
        ''', (chat_id, start_date.strftime('%Y-%m-%d')))

        overview['total_impressions'] = cursor.fetchone()[0]

        # Подсчет опросов
        cursor.execute('''
            SELECT COUNT(*) FROM survey_responses
            WHERE chat_id = ?
                AND completed_at >= ?
        ''', (chat_id, start_date.strftime('%Y-%m-%d')))

        overview['total_surveys'] = cursor.fetchone()[0]

        # Подсчет записей
        cursor.execute('''
            SELECT COUNT(*) FROM entries
            WHERE chat_id = ?
                AND date >= ?
        ''', (chat_id, start_date.strftime('%Y-%m-%d')))

        overview['total_entries'] = cursor.fetchone()[0]

        # Средний mood score
        cursor.execute('''
            SELECT AVG(mood_score) FROM entries
            WHERE chat_id = ?
                AND date >= ?
                AND mood_score IS NOT NULL
        ''', (chat_id, start_date.strftime('%Y-%m-%d')))

        avg_mood = cursor.fetchone()[0]
        if avg_mood is not None:
            overview['avg_mood_score'] = round(avg_mood, 1)

        # Распределение категорий впечатлений
        cursor.execute('''
            SELECT category, COUNT(*) FROM impressions
            WHERE chat_id = ?
                AND created_at >= ?
                AND category IS NOT NULL
            GROUP BY category
        ''', (chat_id, start_date.strftime('%Y-%m-%d')))

        for row in cursor.fetchall():
            category, count = row
            if category in overview['impression_categories']:
                overview['impression_categories'][category] = count

        return overview

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении обзора активности: {e}")
        return overview


def get_correlation_data(
    conn: sqlite3.Connection,
    chat_id: int,
    days: int = 7
) -> List[Dict[str, Any]]:
    """
    Получает данные для корреляционного анализа настроения и впечатлений.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        days: количество дней для анализа

    Returns:
        List[Dict]: данные для анализа корреляций по дням
    """
    cursor = conn.cursor()

    # Вычисляем период
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days - 1)

    try:
        # Получаем данные с разбивкой по категориям впечатлений
        cursor.execute('''
            SELECT
                e.date,
                e.mood_score,
                SUM(CASE WHEN i.category = 'positive' THEN 1 ELSE 0 END) as positive_count,
                SUM(CASE WHEN i.category = 'negative' THEN 1 ELSE 0 END) as negative_count,
                SUM(CASE WHEN i.category = 'neutral' THEN 1 ELSE 0 END) as neutral_count
            FROM entries e
            LEFT JOIN impressions i ON e.chat_id = i.chat_id AND e.date = i.entry_date
            WHERE e.chat_id = ?
                AND e.date >= ?
                AND e.date <= ?
            GROUP BY e.date
            ORDER BY e.date
        ''', (chat_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                'date': row[0],
                'mood_score': row[1],
                'positive_count': row[2],
                'negative_count': row[3],
                'neutral_count': row[4]
            })

        return data

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении корреляционных данных: {e}")
        return []
