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


# ============================================================================
# Функции для работы с пользовательскими шаблонами (Phase 3)
# ============================================================================

def create_user_template(
    conn: sqlite3.Connection,
    chat_id: int,
    name: str,
    description: str
) -> Optional[int]:
    """
    Создает пользовательский шаблон опроса.

    Args:
        conn: Соединение с БД
        chat_id: ID пользователя-создателя
        name: Название шаблона (3-50 символов, уникальное)
        description: Описание шаблона (до 500 символов)

    Returns:
        int или None: ID созданного шаблона или None при ошибке
    """
    try:
        # Проверяем лимит (максимум 20 пользовательских шаблонов)
        count = count_user_templates(conn, chat_id)
        if count >= 20:
            logger.warning(f"Пользователь {chat_id} достиг лимита шаблонов (20)")
            return None

        # Проверяем уникальность названия для пользователя
        cursor = conn.execute("""
            SELECT id FROM survey_templates
            WHERE name = ? AND created_by = ?
        """, (name, chat_id))

        if cursor.fetchone():
            logger.warning(f"Шаблон с названием '{name}' уже существует у пользователя {chat_id}")
            return None

        # Создаем шаблон (по умолчанию is_active=False, is_system=False)
        cursor = conn.execute("""
            INSERT INTO survey_templates
            (name, description, is_system, is_active, created_by, created_at)
            VALUES (?, ?, 0, 0, ?, ?)
        """, (name, description, chat_id, datetime.now().isoformat()))

        conn.commit()
        template_id = cursor.lastrowid

        logger.info(f"Создан пользовательский шаблон '{name}' (ID: {template_id}) пользователем {chat_id}")
        return template_id

    except Exception as e:
        logger.error(f"Ошибка создания пользовательского шаблона: {e}")
        conn.rollback()
        return None


def update_template(
    conn: sqlite3.Connection,
    template_id: int,
    chat_id: int,
    **updates
) -> bool:
    """
    Обновляет шаблон опроса. Только владелец может обновить свой шаблон.

    Args:
        conn: Соединение с БД
        template_id: ID шаблона
        chat_id: ID пользователя (для проверки прав)
        **updates: Поля для обновления (name, description, is_active)

    Returns:
        bool: True если успешно, False если ошибка или нет прав
    """
    try:
        # Проверяем принадлежность шаблона пользователю
        cursor = conn.execute("""
            SELECT created_by, is_system FROM survey_templates
            WHERE id = ?
        """, (template_id,))

        row = cursor.fetchone()
        if not row:
            logger.warning(f"Шаблон {template_id} не найден")
            return False

        created_by, is_system = row

        if is_system:
            logger.warning(f"Попытка изменить системный шаблон {template_id}")
            return False

        if created_by != chat_id:
            logger.warning(f"Попытка изменить чужой шаблон {template_id} пользователем {chat_id}")
            return False

        # Формируем SQL для обновления
        allowed_fields = {'name', 'description', 'is_active'}
        update_fields = {k: v for k, v in updates.items() if k in allowed_fields}

        if not update_fields:
            logger.warning("Нет полей для обновления")
            return False

        # Если меняется название, проверяем уникальность
        if 'name' in update_fields:
            cursor = conn.execute("""
                SELECT id FROM survey_templates
                WHERE name = ? AND created_by = ? AND id != ?
            """, (update_fields['name'], chat_id, template_id))

            if cursor.fetchone():
                logger.warning(f"Шаблон с названием '{update_fields['name']}' уже существует")
                return False

        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [template_id]

        conn.execute(f"""
            UPDATE survey_templates
            SET {set_clause}
            WHERE id = ?
        """, values)

        conn.commit()
        logger.info(f"Шаблон {template_id} обновлен пользователем {chat_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка обновления шаблона: {e}")
        conn.rollback()
        return False


def delete_template(
    conn: sqlite3.Connection,
    template_id: int,
    chat_id: int
) -> bool:
    """
    Удаляет шаблон опроса. Только владелец может удалить свой шаблон.
    CASCADE удалит все связанные вопросы и ответы.

    Args:
        conn: Соединение с БД
        template_id: ID шаблона
        chat_id: ID пользователя (для проверки прав)

    Returns:
        bool: True если успешно, False если ошибка или нет прав
    """
    try:
        # Проверяем принадлежность шаблона пользователю
        cursor = conn.execute("""
            SELECT created_by, is_system, name FROM survey_templates
            WHERE id = ?
        """, (template_id,))

        row = cursor.fetchone()
        if not row:
            logger.warning(f"Шаблон {template_id} не найден")
            return False

        created_by, is_system, name = row

        if is_system:
            logger.warning(f"Попытка удалить системный шаблон {template_id}")
            return False

        if created_by != chat_id:
            logger.warning(f"Попытка удалить чужой шаблон {template_id} пользователем {chat_id}")
            return False

        # Удаляем шаблон (CASCADE удалит вопросы и ответы)
        conn.execute("DELETE FROM survey_templates WHERE id = ?", (template_id,))
        conn.commit()

        logger.info(f"Шаблон '{name}' (ID: {template_id}) удален пользователем {chat_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка удаления шаблона: {e}")
        conn.rollback()
        return False


def get_user_templates(
    conn: sqlite3.Connection,
    chat_id: int,
    only_active: bool = False
) -> List[Dict[str, Any]]:
    """
    Получает шаблоны, созданные пользователем.

    Args:
        conn: Соединение с БД
        chat_id: ID пользователя
        only_active: Возвращать только активные шаблоны

    Returns:
        List[Dict]: Список шаблонов пользователя
    """
    query = "SELECT * FROM survey_templates WHERE created_by = ?"
    params = [chat_id]

    if only_active:
        query += " AND is_active = 1"

    query += " ORDER BY created_at DESC"

    cursor = conn.execute(query, params)
    columns = [desc[0] for desc in cursor.description]

    templates = []
    for row in cursor.fetchall():
        template = dict(zip(columns, row))
        template['is_system'] = bool(template['is_system'])
        template['is_active'] = bool(template['is_active'])
        templates.append(template)

    logger.debug(f"Получено {len(templates)} пользовательских шаблонов для {chat_id}")
    return templates


def count_user_templates(conn: sqlite3.Connection, chat_id: int) -> int:
    """
    Подсчитывает количество шаблонов пользователя.

    Args:
        conn: Соединение с БД
        chat_id: ID пользователя

    Returns:
        int: Количество шаблонов
    """
    cursor = conn.execute("""
        SELECT COUNT(*) FROM survey_templates
        WHERE created_by = ? AND is_system = 0
    """, (chat_id,))

    return cursor.fetchone()[0]


# ============================================================================
# Функции для работы с вопросами в пользовательских шаблонах (Phase 3.2)
# ============================================================================

def add_question_to_template(
    conn: sqlite3.Connection,
    template_id: int,
    chat_id: int,
    question_data: Dict[str, Any]
) -> Optional[int]:
    """
    Добавляет вопрос к шаблону. Только владелец может добавить вопрос.

    Args:
        conn: Соединение с БД
        template_id: ID шаблона
        chat_id: ID пользователя (для проверки прав)
        question_data: Данные вопроса с ключами:
            - question_text: Текст вопроса (10-500 символов)
            - question_type: Тип (text, numeric, yes_no, time, choice, scale)
            - config: JSON конфигурация (опционально)
            - is_required: Обязательный вопрос (по умолчанию True)

    Returns:
        int или None: ID созданного вопроса или None при ошибке
    """
    try:
        # Проверяем принадлежность шаблона пользователю
        cursor = conn.execute("""
            SELECT created_by, is_system FROM survey_templates
            WHERE id = ?
        """, (template_id,))

        row = cursor.fetchone()
        if not row:
            logger.warning(f"Шаблон {template_id} не найден")
            return None

        created_by, is_system = row

        if is_system:
            logger.warning(f"Попытка добавить вопрос к системному шаблону {template_id}")
            return None

        if created_by != chat_id:
            logger.warning(f"Попытка добавить вопрос к чужому шаблону {template_id} пользователем {chat_id}")
            return None

        # Проверяем лимит вопросов (максимум 30)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM survey_questions
            WHERE template_id = ?
        """, (template_id,))

        question_count = cursor.fetchone()[0]
        if question_count >= 30:
            logger.warning(f"Достигнут лимит вопросов (30) для шаблона {template_id}")
            return None

        # Получаем следующий order_index
        cursor = conn.execute("""
            SELECT COALESCE(MAX(order_index), 0) FROM survey_questions
            WHERE template_id = ?
        """, (template_id,))

        next_order = cursor.fetchone()[0] + 1

        # Вставляем вопрос
        question_text = question_data['question_text']
        question_type = question_data['question_type']
        config = question_data.get('config')
        is_required = question_data.get('is_required', True)

        cursor = conn.execute("""
            INSERT INTO survey_questions
            (template_id, question_text, question_type, order_index, is_required, config)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (template_id, question_text, question_type, next_order, is_required, config))

        conn.commit()
        question_id = cursor.lastrowid

        logger.info(f"Вопрос {question_id} добавлен к шаблону {template_id} пользователем {chat_id}")
        return question_id

    except Exception as e:
        logger.error(f"Ошибка добавления вопроса к шаблону: {e}")
        conn.rollback()
        return None


def update_question(
    conn: sqlite3.Connection,
    question_id: int,
    template_id: int,
    chat_id: int,
    **updates
) -> bool:
    """
    Обновляет вопрос. Только владелец шаблона может обновить вопрос.

    Args:
        conn: Соединение с БД
        question_id: ID вопроса
        template_id: ID шаблона (для проверки прав)
        chat_id: ID пользователя (для проверки прав)
        **updates: Поля для обновления (question_text, question_type, config, is_required)

    Returns:
        bool: True если успешно, False если ошибка или нет прав
    """
    try:
        # Проверяем принадлежность шаблона пользователю
        cursor = conn.execute("""
            SELECT created_by, is_system FROM survey_templates
            WHERE id = ?
        """, (template_id,))

        row = cursor.fetchone()
        if not row:
            logger.warning(f"Шаблон {template_id} не найден")
            return False

        created_by, is_system = row

        if is_system:
            logger.warning(f"Попытка изменить вопрос системного шаблона {template_id}")
            return False

        if created_by != chat_id:
            logger.warning(f"Попытка изменить вопрос чужого шаблона {template_id} пользователем {chat_id}")
            return False

        # Проверяем что вопрос принадлежит этому шаблону
        cursor = conn.execute("""
            SELECT template_id FROM survey_questions
            WHERE id = ?
        """, (question_id,))

        row = cursor.fetchone()
        if not row or row[0] != template_id:
            logger.warning(f"Вопрос {question_id} не принадлежит шаблону {template_id}")
            return False

        # Формируем SQL для обновления
        allowed_fields = {'question_text', 'question_type', 'config', 'is_required'}
        update_fields = {k: v for k, v in updates.items() if k in allowed_fields}

        if not update_fields:
            logger.warning("Нет полей для обновления вопроса")
            return False

        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [question_id]

        conn.execute(f"""
            UPDATE survey_questions
            SET {set_clause}
            WHERE id = ?
        """, values)

        conn.commit()
        logger.info(f"Вопрос {question_id} обновлен пользователем {chat_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка обновления вопроса: {e}")
        conn.rollback()
        return False


def delete_question(
    conn: sqlite3.Connection,
    question_id: int,
    template_id: int,
    chat_id: int
) -> bool:
    """
    Удаляет вопрос из шаблона. Только владелец может удалить вопрос.
    Пересчитывает order_index для оставшихся вопросов.

    Args:
        conn: Соединение с БД
        question_id: ID вопроса
        template_id: ID шаблона (для проверки прав)
        chat_id: ID пользователя (для проверки прав)

    Returns:
        bool: True если успешно, False если ошибка или нет прав
    """
    try:
        # Проверяем принадлежность шаблона пользователю
        cursor = conn.execute("""
            SELECT created_by, is_system FROM survey_templates
            WHERE id = ?
        """, (template_id,))

        row = cursor.fetchone()
        if not row:
            logger.warning(f"Шаблон {template_id} не найден")
            return False

        created_by, is_system = row

        if is_system:
            logger.warning(f"Попытка удалить вопрос из системного шаблона {template_id}")
            return False

        if created_by != chat_id:
            logger.warning(f"Попытка удалить вопрос из чужого шаблона {template_id} пользователем {chat_id}")
            return False

        # Проверяем что вопрос принадлежит этому шаблону
        cursor = conn.execute("""
            SELECT template_id, order_index FROM survey_questions
            WHERE id = ?
        """, (question_id,))

        row = cursor.fetchone()
        if not row or row[0] != template_id:
            logger.warning(f"Вопрос {question_id} не принадлежит шаблону {template_id}")
            return False

        deleted_order = row[1]

        # Удаляем вопрос
        conn.execute("DELETE FROM survey_questions WHERE id = ?", (question_id,))

        # Пересчитываем order_index для оставшихся вопросов
        conn.execute("""
            UPDATE survey_questions
            SET order_index = order_index - 1
            WHERE template_id = ? AND order_index > ?
        """, (template_id, deleted_order))

        conn.commit()
        logger.info(f"Вопрос {question_id} удален из шаблона {template_id} пользователем {chat_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка удаления вопроса: {e}")
        conn.rollback()
        return False


def reorder_questions(
    conn: sqlite3.Connection,
    template_id: int,
    chat_id: int,
    question_ids_order: List[int]
) -> bool:
    """
    Изменяет порядок вопросов в шаблоне.

    Args:
        conn: Соединение с БД
        template_id: ID шаблона
        chat_id: ID пользователя (для проверки прав)
        question_ids_order: Список ID вопросов в новом порядке

    Returns:
        bool: True если успешно, False если ошибка или нет прав
    """
    try:
        # Проверяем принадлежность шаблона пользователю
        cursor = conn.execute("""
            SELECT created_by, is_system FROM survey_templates
            WHERE id = ?
        """, (template_id,))

        row = cursor.fetchone()
        if not row:
            logger.warning(f"Шаблон {template_id} не найден")
            return False

        created_by, is_system = row

        if is_system:
            logger.warning(f"Попытка изменить порядок вопросов системного шаблона {template_id}")
            return False

        if created_by != chat_id:
            logger.warning(f"Попытка изменить порядок вопросов чужого шаблона {template_id} пользователем {chat_id}")
            return False

        # Получаем все вопросы шаблона
        cursor = conn.execute("""
            SELECT id FROM survey_questions
            WHERE template_id = ?
            ORDER BY order_index
        """, (template_id,))

        existing_ids = {row[0] for row in cursor.fetchall()}

        # Проверяем что все вопросы из списка принадлежат шаблону
        if set(question_ids_order) != existing_ids:
            logger.warning(f"Список вопросов не соответствует вопросам шаблона {template_id}")
            return False

        # Обновляем order_index для каждого вопроса
        for new_index, question_id in enumerate(question_ids_order, start=1):
            conn.execute("""
                UPDATE survey_questions
                SET order_index = ?
                WHERE id = ?
            """, (new_index, question_id))

        conn.commit()
        logger.info(f"Порядок вопросов шаблона {template_id} изменен пользователем {chat_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка изменения порядка вопросов: {e}")
        conn.rollback()
        return False
