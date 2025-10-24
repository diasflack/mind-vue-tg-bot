"""
Модуль для работы с хранилищем опросов.
Реализует CRUD операции для шаблонов опросов и ответов пользователей.
"""

import logging
import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.data.encryption import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


def get_available_templates(
    conn: sqlite3.Connection,
    only_active: bool = True,
    only_system: bool = False
) -> List[Dict[str, Any]]:
    """
    Получает список доступных шаблонов опросов.

    Args:
        conn: Соединение с БД
        only_active: Возвращать только активные шаблоны
        only_system: Возвращать только системные шаблоны

    Returns:
        List[Dict]: Список шаблонов
    """
    query = "SELECT * FROM survey_templates WHERE 1=1"
    params = []

    if only_active:
        query += " AND is_active = 1"

    if only_system:
        query += " AND is_system = 1"

    query += " ORDER BY is_system DESC, name ASC"

    cursor = conn.execute(query, params)
    columns = [desc[0] for desc in cursor.description]

    templates = []
    for row in cursor.fetchall():
        template = dict(zip(columns, row))
        # Преобразуем integer в boolean
        template['is_system'] = bool(template['is_system'])
        template['is_active'] = bool(template['is_active'])
        templates.append(template)

    logger.debug(f"Получено {len(templates)} шаблонов опросов")
    return templates


def get_template_by_id(conn: sqlite3.Connection, template_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает шаблон по ID.

    Args:
        conn: Соединение с БД
        template_id: ID шаблона

    Returns:
        Dict или None: Шаблон или None если не найден
    """
    cursor = conn.execute(
        "SELECT * FROM survey_templates WHERE id = ?",
        (template_id,)
    )

    row = cursor.fetchone()
    if not row:
        return None

    columns = [desc[0] for desc in cursor.description]
    template = dict(zip(columns, row))
    template['is_system'] = bool(template['is_system'])
    template['is_active'] = bool(template['is_active'])

    return template


def get_template_by_name(conn: sqlite3.Connection, name: str) -> Optional[Dict[str, Any]]:
    """
    Получает шаблон по имени.

    Args:
        conn: Соединение с БД
        name: Имя шаблона

    Returns:
        Dict или None: Шаблон или None если не найден
    """
    cursor = conn.execute(
        "SELECT * FROM survey_templates WHERE name = ?",
        (name,)
    )

    row = cursor.fetchone()
    if not row:
        return None

    columns = [desc[0] for desc in cursor.description]
    template = dict(zip(columns, row))
    template['is_system'] = bool(template['is_system'])
    template['is_active'] = bool(template['is_active'])

    return template


def get_template_questions(conn: sqlite3.Connection, template_id: int) -> List[Dict[str, Any]]:
    """
    Получает вопросы шаблона, отсортированные по order_index.

    Args:
        conn: Соединение с БД
        template_id: ID шаблона

    Returns:
        List[Dict]: Список вопросов
    """
    cursor = conn.execute("""
        SELECT * FROM survey_questions
        WHERE template_id = ?
        ORDER BY order_index ASC
    """, (template_id,))

    columns = [desc[0] for desc in cursor.description]

    questions = []
    for row in cursor.fetchall():
        question = dict(zip(columns, row))
        question['is_required'] = bool(question['is_required'])
        questions.append(question)

    logger.debug(f"Получено {len(questions)} вопросов для шаблона {template_id}")
    return questions


def save_survey_response(conn: sqlite3.Connection, response_data: Dict[str, Any]) -> bool:
    """
    Сохраняет ответ на опрос с шифрованием данных.

    Args:
        conn: Соединение с БД
        response_data: Данные ответа с ключами:
            - chat_id: ID пользователя
            - template_id: ID шаблона
            - response_date: Дата ответа (YYYY-MM-DD)
            - response_time: Время ответа (HH:MM:SS)
            - answers: Dict с ответами {question_id: answer}

    Returns:
        bool: True если успешно, False если ошибка
    """
    try:
        chat_id = response_data['chat_id']
        template_id = response_data['template_id']
        response_date = response_data['response_date']
        response_time = response_data['response_time']
        answers = response_data['answers']

        # Шифруем ответы
        encrypted_answers = encrypt_data(answers, chat_id)

        # Сохраняем в БД
        conn.execute("""
            INSERT INTO survey_responses
            (chat_id, template_id, response_date, response_time, encrypted_data)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, template_id, response_date, response_time, encrypted_answers))

        conn.commit()
        logger.info(f"Ответ на опрос сохранен для пользователя {chat_id}, шаблон {template_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка сохранения ответа на опрос: {e}")
        conn.rollback()
        return False


def get_user_survey_responses(
    conn: sqlite3.Connection,
    chat_id: int,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Получает ответы пользователя на опросы с расшифровкой.

    Args:
        conn: Соединение с БД
        chat_id: ID пользователя
        date: Фильтр по конкретной дате (YYYY-MM-DD)
        start_date: Начальная дата диапазона
        end_date: Конечная дата диапазона

    Returns:
        List[Dict]: Список ответов с расшифрованными данными
    """
    query = """
        SELECT * FROM survey_responses
        WHERE chat_id = ?
    """
    params = [chat_id]

    if date:
        query += " AND response_date = ?"
        params.append(date)
    elif start_date and end_date:
        query += " AND response_date BETWEEN ? AND ?"
        params.extend([start_date, end_date])

    query += " ORDER BY response_date DESC, response_time DESC"

    cursor = conn.execute(query, params)
    columns = [desc[0] for desc in cursor.description]

    responses = []
    for row in cursor.fetchall():
        response = dict(zip(columns, row))

        # Расшифровываем ответы
        decrypted_answers = decrypt_data(response['encrypted_data'], chat_id)
        if decrypted_answers:
            response['answers'] = decrypted_answers
            # Удаляем зашифрованные данные из результата
            del response['encrypted_data']
            responses.append(response)
        else:
            logger.warning(f"Не удалось расшифровать ответ ID {response['id']} для пользователя {chat_id}")

    logger.debug(f"Получено {len(responses)} ответов для пользователя {chat_id}")
    return responses


def get_responses_by_template(
    conn: sqlite3.Connection,
    chat_id: int,
    template_id: int,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Получает ответы пользователя по конкретному шаблону.

    Args:
        conn: Соединение с БД
        chat_id: ID пользователя
        template_id: ID шаблона
        limit: Максимальное количество ответов

    Returns:
        List[Dict]: Список ответов
    """
    query = """
        SELECT * FROM survey_responses
        WHERE chat_id = ? AND template_id = ?
        ORDER BY response_date DESC, response_time DESC
    """
    params = [chat_id, template_id]

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cursor = conn.execute(query, params)
    columns = [desc[0] for desc in cursor.description]

    responses = []
    for row in cursor.fetchall():
        response = dict(zip(columns, row))

        # Расшифровываем ответы
        decrypted_answers = decrypt_data(response['encrypted_data'], chat_id)
        if decrypted_answers:
            response['answers'] = decrypted_answers
            del response['encrypted_data']
            responses.append(response)

    logger.debug(f"Получено {len(responses)} ответов для пользователя {chat_id} по шаблону {template_id}")
    return responses


def delete_survey_response(conn: sqlite3.Connection, response_id: int, chat_id: int) -> bool:
    """
    Удаляет ответ на опрос. Проверяет принадлежность ответа пользователю.

    Args:
        conn: Соединение с БД
        response_id: ID ответа
        chat_id: ID пользователя (для проверки прав)

    Returns:
        bool: True если успешно удален, False если ошибка или нет прав
    """
    try:
        # Проверяем принадлежность ответа пользователю
        cursor = conn.execute(
            "SELECT chat_id FROM survey_responses WHERE id = ?",
            (response_id,)
        )
        row = cursor.fetchone()

        if not row:
            logger.warning(f"Ответ {response_id} не найден")
            return False

        if row[0] != chat_id:
            logger.warning(f"Попытка удалить чужой ответ {response_id} пользователем {chat_id}")
            return False

        # Удаляем ответ
        conn.execute("DELETE FROM survey_responses WHERE id = ?", (response_id,))
        conn.commit()

        logger.info(f"Ответ {response_id} удален пользователем {chat_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка удаления ответа на опрос: {e}")
        conn.rollback()
        return False


def get_survey_statistics(
    conn: sqlite3.Connection,
    chat_id: int,
    template_id: int
) -> Dict[str, Any]:
    """
    Получает статистику по ответам пользователя на конкретный опрос.

    Args:
        conn: Соединение с БД
        chat_id: ID пользователя
        template_id: ID шаблона

    Returns:
        Dict: Статистика (количество ответов, первый/последний ответ и т.д.)
    """
    cursor = conn.execute("""
        SELECT
            COUNT(*) as total_responses,
            MIN(response_date) as first_response_date,
            MAX(response_date) as last_response_date
        FROM survey_responses
        WHERE chat_id = ? AND template_id = ?
    """, (chat_id, template_id))

    row = cursor.fetchone()

    return {
        'total_responses': row[0],
        'first_response_date': row[1],
        'last_response_date': row[2]
    }
