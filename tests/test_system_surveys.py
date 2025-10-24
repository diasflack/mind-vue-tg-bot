"""
Тесты для системных шаблонов опросов (Phase 2.3).
"""

import pytest
import sqlite3
import json
from src.data.system_surveys import (
    get_cbt_journal_template,
    get_addiction_journal_template,
    get_gratitude_journal_template,
    get_sleep_journal_template,
    load_system_surveys
)


def test_cbt_journal_template():
    """Проверяет структуру шаблона КПТ дневника."""
    template = get_cbt_journal_template()

    assert template['name'] == "КПТ дневник"
    assert template['icon'] == "🧠"
    assert template['is_system'] is True
    assert 'description' in template

    # Проверяем вопросы
    questions = template['questions']
    assert len(questions) == 7

    # Проверяем типы вопросов
    assert questions[0]['question_type'] == 'text'  # Ситуация
    assert questions[1]['question_type'] == 'text'  # Автоматические мысли
    assert questions[2]['question_type'] == 'text'  # Эмоции
    assert questions[3]['question_type'] == 'numeric'  # Интенсивность (до)
    assert questions[4]['question_type'] == 'choice'  # Когнитивные искажения
    assert questions[5]['question_type'] == 'text'  # Альтернативная мысль
    assert questions[6]['question_type'] == 'numeric'  # Интенсивность (после)

    # Проверяем конфигурацию numeric вопроса
    config = json.loads(questions[3]['config'])
    assert config['min'] == 1
    assert config['max'] == 10

    # Проверяем конфигурацию choice вопроса
    config = json.loads(questions[4]['config'])
    assert 'options' in config
    assert len(config['options']) >= 7
    assert 'Катастрофизация' in config['options']
    assert config['multiple'] is True


def test_addiction_journal_template():
    """Проверяет структуру шаблона дневника зависимости."""
    template = get_addiction_journal_template()

    assert template['name'] == "Дневник зависимости"
    assert template['icon'] == "💪"
    assert template['is_system'] is True

    # Проверяем вопросы
    questions = template['questions']
    assert len(questions) == 7

    # Проверяем типы вопросов
    assert questions[0]['question_type'] == 'yes_no'  # Было ли влечение
    assert questions[1]['question_type'] == 'numeric'  # Интенсивность влечения
    assert questions[2]['question_type'] == 'choice'  # Триггеры
    assert questions[3]['question_type'] == 'text'  # Стратегии совладания
    assert questions[4]['question_type'] == 'yes_no'  # Были ли срывы
    assert questions[5]['question_type'] == 'text'  # Описание срыва
    assert questions[6]['question_type'] == 'text'  # Что делать иначе

    # Проверяем конфигурацию numeric вопроса
    config = json.loads(questions[1]['config'])
    assert config['min'] == 0
    assert config['max'] == 10

    # Проверяем конфигурацию choice вопроса
    config = json.loads(questions[2]['config'])
    assert 'options' in config
    assert 'Стресс' in config['options']
    assert 'Скука' in config['options']
    assert config['multiple'] is True

    # Проверяем, что описание срыва не обязательно
    assert questions[5]['is_required'] is False


def test_gratitude_journal_template():
    """Проверяет структуру шаблона дневника благодарности."""
    template = get_gratitude_journal_template()

    assert template['name'] == "Дневник благодарности"
    assert template['icon'] == "🙏"
    assert template['is_system'] is True

    # Проверяем вопросы
    questions = template['questions']
    assert len(questions) == 3

    # Все вопросы текстовые
    assert all(q['question_type'] == 'text' for q in questions)

    # Проверяем содержание вопросов
    assert "благодарен" in questions[0]['question_text'].lower()
    assert "кто" in questions[1]['question_text'].lower()
    assert "удовольствие" in questions[2]['question_text'].lower()


def test_sleep_journal_template():
    """Проверяет структуру шаблона дневника сна."""
    template = get_sleep_journal_template()

    assert template['name'] == "Дневник сна"
    assert template['icon'] == "😴"
    assert template['is_system'] is True

    # Проверяем вопросы
    questions = template['questions']
    assert len(questions) == 6

    # Проверяем типы вопросов
    assert questions[0]['question_type'] == 'time'  # Время засыпания
    assert questions[1]['question_type'] == 'time'  # Время пробуждения
    assert questions[2]['question_type'] == 'numeric'  # Количество пробуждений
    assert questions[3]['question_type'] == 'numeric'  # Качество сна
    assert questions[4]['question_type'] == 'yes_no'  # Кошмары
    assert questions[5]['question_type'] == 'choice'  # Активности перед сном

    # Проверяем конфигурацию numeric вопроса (качество)
    config = json.loads(questions[3]['config'])
    assert config['min'] == 1
    assert config['max'] == 10

    # Проверяем конфигурацию choice вопроса
    config = json.loads(questions[5]['config'])
    assert 'options' in config
    assert 'Читал' in config['options']
    assert 'Медитировал' in config['options']
    assert config['multiple'] is True


@pytest.fixture
def temp_db():
    """Создает временную БД для тестирования."""
    conn = sqlite3.connect(':memory:')
    conn.execute('PRAGMA foreign_keys = ON')

    # Создаем таблицы
    conn.execute('''
        CREATE TABLE survey_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            is_system BOOLEAN DEFAULT 0,
            creator_chat_id INTEGER,
            icon TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')

    conn.execute('''
        CREATE TABLE survey_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            is_required BOOLEAN DEFAULT 1,
            config TEXT,
            help_text TEXT,
            FOREIGN KEY (template_id) REFERENCES survey_templates(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    yield conn
    conn.close()


def test_system_surveys_loaded(temp_db):
    """Проверяет загрузку системных опросов в БД."""
    # Загружаем системные опросы
    load_system_surveys(temp_db)

    # Проверяем, что создано 4 шаблона
    cursor = temp_db.execute("SELECT COUNT(*) FROM survey_templates WHERE is_system = 1")
    assert cursor.fetchone()[0] == 4

    # Проверяем наличие всех опросов
    cursor = temp_db.execute("SELECT name FROM survey_templates WHERE is_system = 1")
    names = [row[0] for row in cursor.fetchall()]

    assert "КПТ дневник" in names
    assert "Дневник зависимости" in names
    assert "Дневник благодарности" in names
    assert "Дневник сна" in names

    # Проверяем, что загружены вопросы
    cursor = temp_db.execute("SELECT COUNT(*) FROM survey_questions")
    count = cursor.fetchone()[0]
    # КПТ(7) + Зависимость(7) + Благодарность(3) + Сон(6) = 23
    assert count == 23


def test_system_surveys_idempotent(temp_db):
    """Проверяет, что повторная загрузка не дублирует записи."""
    # Первая загрузка
    load_system_surveys(temp_db)

    cursor = temp_db.execute("SELECT COUNT(*) FROM survey_templates WHERE is_system = 1")
    count_first = cursor.fetchone()[0]

    # Вторая загрузка
    load_system_surveys(temp_db)

    cursor = temp_db.execute("SELECT COUNT(*) FROM survey_templates WHERE is_system = 1")
    count_second = cursor.fetchone()[0]

    # Количество не изменилось
    assert count_first == count_second == 4


def test_system_survey_icons():
    """Проверяет наличие иконок у всех системных опросов."""
    templates = [
        get_cbt_journal_template(),
        get_addiction_journal_template(),
        get_gratitude_journal_template(),
        get_sleep_journal_template()
    ]

    for template in templates:
        assert template['icon'] is not None
        assert len(template['icon']) > 0


def test_system_survey_descriptions():
    """Проверяет наличие описаний у всех системных опросов."""
    templates = [
        get_cbt_journal_template(),
        get_addiction_journal_template(),
        get_gratitude_journal_template(),
        get_sleep_journal_template()
    ]

    for template in templates:
        assert template['description'] is not None
        assert len(template['description']) > 0


def test_all_questions_have_order_index():
    """Проверяет, что все вопросы имеют порядковый номер."""
    templates = [
        get_cbt_journal_template(),
        get_addiction_journal_template(),
        get_gratitude_journal_template(),
        get_sleep_journal_template()
    ]

    for template in templates:
        for i, question in enumerate(template['questions'], start=1):
            assert question['order_index'] == i


def test_config_fields_are_valid_json():
    """Проверяет, что все config поля содержат валидный JSON."""
    templates = [
        get_cbt_journal_template(),
        get_addiction_journal_template(),
        get_gratitude_journal_template(),
        get_sleep_journal_template()
    ]

    for template in templates:
        for question in template['questions']:
            if question.get('config'):
                # Не должно упасть
                config = json.loads(question['config'])
                assert isinstance(config, dict)
