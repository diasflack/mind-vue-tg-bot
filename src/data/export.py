"""
Модуль для экспорта данных в различных форматах (Phase 5.4).

Поддерживает экспорт:
- Впечатлений (impressions) в CSV/JSON
- Ответов на опросы (survey responses) в CSV/JSON
- Всех данных в JSON
"""

import sqlite3
import json
import csv
from io import StringIO
from typing import Dict, Any, List, Optional
from datetime import datetime


def export_impressions_csv(
    conn: sqlite3.Connection,
    chat_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> str:
    """
    Экспортирует впечатления пользователя в CSV формат.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        from_date: начальная дата фильтра (YYYY-MM-DD)
        to_date: конечная дата фильтра (YYYY-MM-DD)

    Returns:
        str: CSV данные как строка
    """
    cursor = conn.cursor()

    # Формируем SQL запрос с фильтрацией
    query = '''
        SELECT
            id,
            impression_text as text,
            impression_date as date,
            impression_time as time,
            category,
            intensity,
            entry_date,
            created_at
        FROM impressions
        WHERE chat_id = ?
    '''
    params = [chat_id]

    if from_date:
        query += ' AND impression_date >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND impression_date <= ?'
        params.append(to_date)

    query += ' ORDER BY impression_date, impression_time'

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Создаем CSV
    output = StringIO()
    if rows:
        # Получаем имена колонок
        column_names = [desc[0] for desc in cursor.description]
        writer = csv.DictWriter(output, fieldnames=column_names)
        writer.writeheader()

        for row in rows:
            row_dict = dict(zip(column_names, row))
            writer.writerow(row_dict)
    else:
        # Пустой CSV с заголовками
        writer = csv.DictWriter(output, fieldnames=['id', 'text', 'date', 'time', 'category', 'intensity', 'entry_date', 'created_at'])
        writer.writeheader()

    return output.getvalue()


def export_impressions_json(
    conn: sqlite3.Connection,
    chat_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> str:
    """
    Экспортирует впечатления пользователя в JSON формат.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        from_date: начальная дата фильтра (YYYY-MM-DD)
        to_date: конечная дата фильтра (YYYY-MM-DD)

    Returns:
        str: JSON данные как строка
    """
    cursor = conn.cursor()

    # Формируем SQL запрос с фильтрацией
    query = '''
        SELECT
            id,
            impression_text as text,
            impression_date as date,
            impression_time as time,
            category,
            intensity,
            entry_date,
            created_at
        FROM impressions
        WHERE chat_id = ?
    '''
    params = [chat_id]

    if from_date:
        query += ' AND impression_date >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND impression_date <= ?'
        params.append(to_date)

    query += ' ORDER BY impression_date, impression_time'

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Создаем список впечатлений
    impressions = []
    column_names = [desc[0] for desc in cursor.description]

    for row in rows:
        impression = dict(zip(column_names, row))
        impressions.append(impression)

    # Формируем итоговый JSON
    result = {
        'impressions': impressions,
        'count': len(impressions),
        'exported_at': datetime.now().isoformat(),
        'filters': {
            'chat_id': chat_id,
            'from_date': from_date,
            'to_date': to_date
        }
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


def export_survey_responses_csv(
    conn: sqlite3.Connection,
    chat_id: int,
    survey_name: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Optional[str]:
    """
    Экспортирует ответы на конкретный опрос в CSV формат.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        survey_name: название опроса
        from_date: начальная дата фильтра (YYYY-MM-DD)
        to_date: конечная дата фильтра (YYYY-MM-DD)

    Returns:
        str или None: CSV данные как строка или None если опрос не найден
    """
    cursor = conn.cursor()

    # Получаем template_id опроса
    cursor.execute('SELECT id FROM survey_templates WHERE name = ?', (survey_name,))
    template_row = cursor.fetchone()

    if not template_row:
        return None

    template_id = template_row[0]

    # Получаем все вопросы для этого опроса
    cursor.execute('''
        SELECT id, question_text, question_type
        FROM survey_questions
        WHERE template_id = ?
        ORDER BY order_num
    ''', (template_id,))
    questions = cursor.fetchall()

    if not questions:
        return ''

    # Получаем все ответы
    query = '''
        SELECT
            sr.id as response_id,
            sr.response_date,
            sr.response_time
        FROM survey_responses sr
        WHERE sr.chat_id = ? AND sr.template_id = ?
    '''
    params = [chat_id, template_id]

    if from_date:
        query += ' AND sr.response_date >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND sr.response_date <= ?'
        params.append(to_date)

    query += ' ORDER BY sr.response_date, sr.response_time'

    cursor.execute(query, params)
    responses = cursor.fetchall()

    # Формируем CSV
    output = StringIO()

    # Создаем заголовки: дата, время, затем вопросы
    fieldnames = ['response_date', 'response_time'] + [q[1] for q in questions]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    # Для каждого ответа собираем данные
    for response in responses:
        response_id = response[0]
        row_data = {
            'response_date': response[1],
            'response_time': response[2]
        }

        # Получаем ответы на все вопросы
        for question_id, question_text, question_type in questions:
            cursor.execute('''
                SELECT answer_text, answer_numeric
                FROM survey_answers
                WHERE response_id = ? AND question_id = ?
            ''', (response_id, question_id))
            answer = cursor.fetchone()

            if answer:
                # Используем numeric или text в зависимости от типа
                answer_value = answer[1] if answer[1] is not None else answer[0]
                row_data[question_text] = answer_value
            else:
                row_data[question_text] = ''

        writer.writerow(row_data)

    return output.getvalue()


def export_survey_responses_json(
    conn: sqlite3.Connection,
    chat_id: int,
    survey_name: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Optional[str]:
    """
    Экспортирует ответы на конкретный опрос в JSON формат.

    Args:
        conn: соединение с БД
        chat_id: ID пользователя
        survey_name: название опроса
        from_date: начальная дата фильтра (YYYY-MM-DD)
        to_date: конечная дата фильтра (YYYY-MM-DD)

    Returns:
        str или None: JSON данные как строка или None если опрос не найден
    """
    cursor = conn.cursor()

    # Получаем template_id опроса
    cursor.execute('SELECT id FROM survey_templates WHERE name = ?', (survey_name,))
    template_row = cursor.fetchone()

    if not template_row:
        return None

    template_id = template_row[0]

    # Получаем все вопросы для этого опроса
    cursor.execute('''
        SELECT id, question_text, question_type
        FROM survey_questions
        WHERE template_id = ?
        ORDER BY order_num
    ''', (template_id,))
    questions = cursor.fetchall()

    # Получаем все ответы
    query = '''
        SELECT
            sr.id as response_id,
            sr.response_date,
            sr.response_time
        FROM survey_responses sr
        WHERE sr.chat_id = ? AND sr.template_id = ?
    '''
    params = [chat_id, template_id]

    if from_date:
        query += ' AND sr.response_date >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND sr.response_date <= ?'
        params.append(to_date)

    query += ' ORDER BY sr.response_date, sr.response_time'

    cursor.execute(query, params)
    responses = cursor.fetchall()

    # Формируем список ответов
    responses_list = []

    for response in responses:
        response_id = response[0]
        response_data = {
            'date': response[1],
            'time': response[2],
            'answers': []
        }

        # Получаем ответы на все вопросы
        for question_id, question_text, question_type in questions:
            cursor.execute('''
                SELECT answer_text, answer_numeric
                FROM survey_answers
                WHERE response_id = ? AND question_id = ?
            ''', (response_id, question_id))
            answer = cursor.fetchone()

            if answer:
                answer_value = answer[1] if answer[1] is not None else answer[0]
                response_data['answers'].append({
                    'question': question_text,
                    'answer': answer_value,
                    'type': question_type
                })

        responses_list.append(response_data)

    # Формируем итоговый JSON
    result = {
        'survey_name': survey_name,
        'responses': responses_list,
        'count': len(responses_list),
        'exported_at': datetime.now().isoformat(),
        'filters': {
            'chat_id': chat_id,
            'from_date': from_date,
            'to_date': to_date
        }
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


def export_all_data_json(
    conn: sqlite3.Connection,
    chat_id: int
) -> str:
    """
    Экспортирует все данные пользователя в JSON формат.

    Включает:
    - Записи дневника (entries)
    - Впечатления (impressions)
    - Ответы на все опросы (survey responses)

    Args:
        conn: соединение с БД
        chat_id: ID пользователя

    Returns:
        str: JSON данные как строка
    """
    cursor = conn.cursor()

    # Экспортируем записи дневника
    cursor.execute('''
        SELECT
            date, mood, sleep_hours, comment,
            balance, mania, depression, anxiety,
            irritability, productivity, sociability
        FROM entries
        WHERE chat_id = ?
        ORDER BY date
    ''', (chat_id,))

    entries = []
    for row in cursor.fetchall():
        entries.append({
            'date': row[0],
            'mood': row[1],
            'sleep_hours': row[2],
            'comment': row[3],
            'balance': row[4],
            'mania': row[5],
            'depression': row[6],
            'anxiety': row[7],
            'irritability': row[8],
            'productivity': row[9],
            'sociability': row[10]
        })

    # Экспортируем впечатления
    cursor.execute('''
        SELECT
            id, impression_text, impression_date, impression_time,
            category, intensity, entry_date
        FROM impressions
        WHERE chat_id = ?
        ORDER BY impression_date, impression_time
    ''', (chat_id,))

    impressions = []
    for row in cursor.fetchall():
        impressions.append({
            'id': row[0],
            'text': row[1],
            'date': row[2],
            'time': row[3],
            'category': row[4],
            'intensity': row[5],
            'entry_date': row[6]
        })

    # Экспортируем ответы на опросы
    # Сначала получаем все опросы пользователя
    cursor.execute('''
        SELECT DISTINCT st.name
        FROM survey_responses sr
        JOIN survey_templates st ON sr.template_id = st.id
        WHERE sr.chat_id = ?
    ''', (chat_id,))

    surveys = {}
    for (survey_name,) in cursor.fetchall():
        # Для каждого опроса получаем ответы в формате JSON
        survey_json = export_survey_responses_json(conn, chat_id, survey_name)
        if survey_json:
            survey_data = json.loads(survey_json)
            surveys[survey_name] = survey_data['responses']

    # Формируем итоговый JSON
    result = {
        'user_id': chat_id,
        'exported_at': datetime.now().isoformat(),
        'data': {
            'entries': entries,
            'entries_count': len(entries),
            'impressions': impressions,
            'impressions_count': len(impressions),
            'surveys': surveys,
            'surveys_count': sum(len(responses) for responses in surveys.values())
        }
    }

    return json.dumps(result, ensure_ascii=False, indent=2)
