"""
Модуль с системными шаблонами опросов.
Содержит предопределенные шаблоны: КПТ, Зависимость, Благодарность, Сон.
"""

import logging
import json
import sqlite3
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def get_cbt_journal_template() -> Dict[str, Any]:
    """
    Возвращает шаблон КПТ дневника (Когнитивно-поведенческая терапия).

    Returns:
        Dict с данными шаблона и вопросами
    """
    return {
        'name': 'КПТ дневник',
        'description': 'Когнитивно-поведенческая терапия для работы с автоматическими мыслями',
        'is_system': True,
        'icon': '🧠',
        'questions': [
            {
                'question_text': 'Опишите ситуацию, которая вызвала эмоциональную реакцию',
                'question_type': 'text',
                'order_index': 1,
                'is_required': True,
                'help_text': 'Что произошло? Где? Когда? С кем?'
            },
            {
                'question_text': 'Какие автоматические мысли возникли?',
                'question_type': 'text',
                'order_index': 2,
                'is_required': True,
                'help_text': 'Что вы подумали в тот момент?'
            },
            {
                'question_text': 'Какие эмоции вы испытывали?',
                'question_type': 'text',
                'order_index': 3,
                'is_required': True,
                'help_text': 'Злость, грусть, тревога, страх и т.д.'
            },
            {
                'question_text': 'Оцените интенсивность эмоций (1-10)',
                'question_type': 'numeric',
                'order_index': 4,
                'is_required': True,
                'config': json.dumps({'min': 1, 'max': 10}),
                'help_text': '1 - минимальная, 10 - максимальная'
            },
            {
                'question_text': 'Какие когнитивные искажения вы заметили?',
                'question_type': 'choice',
                'order_index': 5,
                'is_required': True,
                'config': json.dumps({
                    'options': [
                        'Чёрно-белое мышление',
                        'Катастрофизация',
                        'Персонализация',
                        'Чтение мыслей',
                        'Долженствование',
                        'Фильтрация',
                        'Другое'
                    ],
                    'multiple': True
                }),
                'help_text': 'Можно выбрать несколько'
            },
            {
                'question_text': 'Альтернативная, более сбалансированная мысль',
                'question_type': 'text',
                'order_index': 6,
                'is_required': True,
                'help_text': 'Как можно посмотреть на ситуацию иначе?'
            },
            {
                'question_text': 'Переоцените интенсивность эмоций сейчас (1-10)',
                'question_type': 'numeric',
                'order_index': 7,
                'is_required': True,
                'config': json.dumps({'min': 1, 'max': 10}),
                'help_text': 'Изменилась ли интенсивность после рефрейминга?'
            }
        ]
    }


def get_addiction_journal_template() -> Dict[str, Any]:
    """
    Возвращает шаблон дневника зависимости.

    Returns:
        Dict с данными шаблона и вопросами
    """
    return {
        'name': 'Дневник зависимости',
        'description': 'Отслеживание влечения, триггеров и стратегий совладания',
        'is_system': True,
        'icon': '💪',
        'questions': [
            {
                'question_text': 'Было ли сегодня влечение?',
                'question_type': 'yes_no',
                'order_index': 1,
                'is_required': True,
                'help_text': 'Ответьте да или нет'
            },
            {
                'question_text': 'Максимальная интенсивность влечения (0-10)',
                'question_type': 'numeric',
                'order_index': 2,
                'is_required': True,
                'config': json.dumps({'min': 0, 'max': 10}),
                'help_text': '0 - не было, 10 - максимальное'
            },
            {
                'question_text': 'Что спровоцировало влечение?',
                'question_type': 'choice',
                'order_index': 3,
                'is_required': True,
                'config': json.dumps({
                    'options': [
                        'Стресс',
                        'Скука',
                        'Социальная ситуация',
                        'Определенное место',
                        'Эмоциональное состояние',
                        'Физический дискомфорт',
                        'Другое'
                    ],
                    'multiple': True
                }),
                'help_text': 'Можно выбрать несколько триггеров'
            },
            {
                'question_text': 'Какие стратегии помогли справиться?',
                'question_type': 'text',
                'order_index': 4,
                'is_required': True,
                'help_text': 'Опишите, что вам помогло'
            },
            {
                'question_text': 'Были ли срывы?',
                'question_type': 'yes_no',
                'order_index': 5,
                'is_required': True,
                'help_text': 'Честно ответьте да или нет'
            },
            {
                'question_text': 'Если да, опишите ситуацию',
                'question_type': 'text',
                'order_index': 6,
                'is_required': False,
                'help_text': 'Что произошло? Без самоосуждения'
            },
            {
                'question_text': 'Что можно сделать иначе в следующий раз?',
                'question_type': 'text',
                'order_index': 7,
                'is_required': True,
                'help_text': 'План действий на будущее'
            }
        ]
    }


def get_gratitude_journal_template() -> Dict[str, Any]:
    """
    Возвращает шаблон дневника благодарности.

    Returns:
        Dict с данными шаблона и вопросами
    """
    return {
        'name': 'Дневник благодарности',
        'description': 'Ежедневная практика благодарности для улучшения настроения',
        'is_system': True,
        'icon': '🙏',
        'questions': [
            {
                'question_text': 'За что я благодарен сегодня? (3 вещи)',
                'question_type': 'text',
                'order_index': 1,
                'is_required': True,
                'help_text': 'Запишите минимум три вещи, за которые вы благодарны'
            },
            {
                'question_text': 'Кто сделал мой день лучше?',
                'question_type': 'text',
                'order_index': 2,
                'is_required': True,
                'help_text': 'Люди, которые помогли или поддержали вас'
            },
            {
                'question_text': 'Какое маленькое удовольствие я получил сегодня?',
                'question_type': 'text',
                'order_index': 3,
                'is_required': True,
                'help_text': 'Вкусная еда, красивый закат, приятная музыка...'
            }
        ]
    }


def get_sleep_journal_template() -> Dict[str, Any]:
    """
    Возвращает шаблон дневника сна.

    Returns:
        Dict с данными шаблона и вопросами
    """
    return {
        'name': 'Дневник сна',
        'description': 'Отслеживание качества и паттернов сна',
        'is_system': True,
        'icon': '😴',
        'questions': [
            {
                'question_text': 'Во сколько вы легли спать?',
                'question_type': 'time',
                'order_index': 1,
                'is_required': True,
                'help_text': 'Формат: ЧЧ:ММ, например 23:30'
            },
            {
                'question_text': 'Во сколько проснулись?',
                'question_type': 'time',
                'order_index': 2,
                'is_required': True,
                'help_text': 'Формат: ЧЧ:ММ, например 07:00'
            },
            {
                'question_text': 'Сколько раз просыпались ночью?',
                'question_type': 'numeric',
                'order_index': 3,
                'is_required': True,
                'config': json.dumps({'min': 0, 'max': 20}),
                'help_text': '0 если не просыпались'
            },
            {
                'question_text': 'Качество сна (1-10)',
                'question_type': 'numeric',
                'order_index': 4,
                'is_required': True,
                'config': json.dumps({'min': 1, 'max': 10}),
                'help_text': '1 - очень плохое, 10 - отличное'
            },
            {
                'question_text': 'Были ли кошмары?',
                'question_type': 'yes_no',
                'order_index': 5,
                'is_required': True,
                'help_text': 'Ответьте да или нет'
            },
            {
                'question_text': 'Что делали перед сном?',
                'question_type': 'choice',
                'order_index': 6,
                'is_required': True,
                'config': json.dumps({
                    'options': [
                        'Читал',
                        'Смотрел телефон',
                        'Медитировал',
                        'Смотрел ТВ',
                        'Разговаривал',
                        'Другое'
                    ],
                    'multiple': True
                }),
                'help_text': 'Можно выбрать несколько активностей'
            }
        ]
    }


def load_system_surveys(conn: sqlite3.Connection) -> None:
    """
    Загружает системные опросы в базу данных.
    Проверяет существование перед загрузкой (идемпотентно).

    Args:
        conn: Соединение с базой данных SQLite
    """
    cursor = conn.cursor()

    # Получаем все системные шаблоны
    templates = [
        get_cbt_journal_template(),
        get_addiction_journal_template(),
        get_gratitude_journal_template(),
        get_sleep_journal_template()
    ]

    for template_data in templates:
        # Проверяем, существует ли уже такой опрос
        cursor.execute("""
            SELECT id FROM survey_templates
            WHERE name = ? AND is_system = 1
        """, (template_data['name'],))

        existing = cursor.fetchone()

        if existing:
            logger.info(f"Системный опрос '{template_data['name']}' уже существует, пропускаем")
            continue

        # Вставляем шаблон
        cursor.execute("""
            INSERT INTO survey_templates (name, description, is_system, icon, is_active)
            VALUES (?, ?, 1, ?, 1)
        """, (
            template_data['name'],
            template_data['description'],
            template_data['icon']
        ))

        template_id = cursor.lastrowid
        logger.info(f"Создан системный опрос '{template_data['name']}' (ID: {template_id})")

        # Вставляем вопросы
        for question in template_data['questions']:
            cursor.execute("""
                INSERT INTO survey_questions
                (template_id, question_text, question_type, order_index, is_required, config, help_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                template_id,
                question['question_text'],
                question['question_type'],
                question['order_index'],
                question['is_required'],
                question.get('config'),
                question.get('help_text')
            ))

        logger.info(f"Добавлено {len(template_data['questions'])} вопросов для '{template_data['name']}'")

    conn.commit()
    logger.info("Системные опросы успешно загружены")


if __name__ == '__main__':
    # Для тестирования
    logging.basicConfig(level=logging.INFO)

    from src.data.storage import _get_db_connection

    conn = _get_db_connection()
    try:
        load_system_surveys(conn)
        print("Системные опросы загружены!")
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        conn.close()
