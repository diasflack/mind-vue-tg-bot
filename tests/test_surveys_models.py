"""
Тесты для моделей данных системы опросов (Phase 2.2).
"""

import pytest
import json
from src.data.models import (
    SurveyTemplate, SurveyQuestion, SurveyResponse,
    QUESTION_TYPES
)


def test_question_types_constant():
    """Проверяет константу типов вопросов."""
    assert 'numeric' in QUESTION_TYPES
    assert 'text' in QUESTION_TYPES
    assert 'choice' in QUESTION_TYPES
    assert 'yes_no' in QUESTION_TYPES
    assert 'time' in QUESTION_TYPES
    assert 'scale' in QUESTION_TYPES


def test_survey_template_creation():
    """Проверяет создание шаблона опроса."""
    template = SurveyTemplate(
        id=1,
        name="Test Survey",
        description="Test Description",
        is_system=False,
        creator_chat_id=123,
        icon="📝",
        created_at="2025-01-15 10:00:00",
        is_active=True
    )

    assert template.id == 1
    assert template.name == "Test Survey"
    assert template.description == "Test Description"
    assert template.is_system is False
    assert template.creator_chat_id == 123
    assert template.icon == "📝"
    assert template.is_active is True


def test_survey_template_minimal():
    """Проверяет создание шаблона с минимальными полями."""
    template = SurveyTemplate(
        id=1,
        name="Minimal Survey"
    )

    assert template.id == 1
    assert template.name == "Minimal Survey"
    assert template.description is None
    assert template.is_system is False
    assert template.creator_chat_id is None
    assert template.icon is None
    assert template.created_at is None
    assert template.is_active is True


def test_survey_question_creation():
    """Проверяет создание вопроса опроса."""
    question = SurveyQuestion(
        id=1,
        template_id=1,
        question_text="Как ваше настроение?",
        question_type="scale",
        order_index=1,
        is_required=True,
        config='{"min": 1, "max": 10}',
        help_text="Оцените по шкале"
    )

    assert question.id == 1
    assert question.template_id == 1
    assert question.question_text == "Как ваше настроение?"
    assert question.question_type == "scale"
    assert question.order_index == 1
    assert question.is_required is True
    assert question.config == '{"min": 1, "max": 10}'
    assert question.help_text == "Оцените по шкале"


def test_survey_question_type_validation():
    """Проверяет валидацию типа вопроса."""
    # Валидный тип
    question = SurveyQuestion(
        id=1,
        template_id=1,
        question_text="Test?",
        question_type="numeric",
        order_index=1
    )
    assert question.question_type == "numeric"

    # Невалидный тип - должна быть ошибка
    with pytest.raises(ValueError, match="Недопустимый тип вопроса"):
        SurveyQuestion(
            id=1,
            template_id=1,
            question_text="Test?",
            question_type="invalid_type",
            order_index=1
        )


def test_survey_question_minimal():
    """Проверяет создание вопроса с минимальными полями."""
    question = SurveyQuestion(
        id=1,
        template_id=1,
        question_text="Test?",
        question_type="text",
        order_index=1
    )

    assert question.id == 1
    assert question.is_required is True  # По умолчанию True
    assert question.config is None
    assert question.help_text is None


def test_config_json_parsing():
    """Проверяет парсинг JSON конфигурации."""
    question = SurveyQuestion(
        id=1,
        template_id=1,
        question_text="Choose option",
        question_type="choice",
        order_index=1,
        config='{"options": ["Option 1", "Option 2", "Option 3"], "multiple": true}'
    )

    # Парсим конфигурацию
    config = json.loads(question.config)
    assert config['options'] == ["Option 1", "Option 2", "Option 3"]
    assert config['multiple'] is True


def test_numeric_question_config():
    """Проверяет конфигурацию для numeric типа."""
    question = SurveyQuestion(
        id=1,
        template_id=1,
        question_text="Rate 1-10",
        question_type="numeric",
        order_index=1,
        config='{"min": 1, "max": 10}'
    )

    config = json.loads(question.config)
    assert config['min'] == 1
    assert config['max'] == 10


def test_survey_response_creation():
    """Проверяет создание ответа на опрос."""
    response = SurveyResponse(
        id=1,
        chat_id=123,
        template_id=1,
        response_date="2025-01-15",
        response_time="10:00:00",
        encrypted_data="encrypted_json_data",
        created_at="2025-01-15 10:00:00"
    )

    assert response.id == 1
    assert response.chat_id == 123
    assert response.template_id == 1
    assert response.response_date == "2025-01-15"
    assert response.response_time == "10:00:00"
    assert response.encrypted_data == "encrypted_json_data"
    assert response.created_at == "2025-01-15 10:00:00"


def test_survey_response_minimal():
    """Проверяет создание ответа с минимальными полями."""
    response = SurveyResponse(
        id=1,
        chat_id=123,
        template_id=1,
        response_date="2025-01-15",
        response_time="10:00:00",
        encrypted_data="encrypted_data"
    )

    assert response.id == 1
    assert response.created_at is None


def test_survey_template_to_dict():
    """Проверяет сериализацию шаблона в dict."""
    template = SurveyTemplate(
        id=1,
        name="Test Survey",
        description="Description",
        is_system=True,
        icon="📝"
    )

    data = template.to_dict()

    assert data['id'] == 1
    assert data['name'] == "Test Survey"
    assert data['description'] == "Description"
    assert data['is_system'] is True
    assert data['icon'] == "📝"
    assert 'creator_chat_id' in data
    assert 'is_active' in data


def test_survey_template_from_dict():
    """Проверяет десериализацию шаблона из dict."""
    data = {
        'id': 1,
        'name': 'Test Survey',
        'description': 'Description',
        'is_system': 1,  # SQLite возвращает int
        'creator_chat_id': 123,
        'icon': '📝',
        'created_at': '2025-01-15 10:00:00',
        'is_active': 1
    }

    template = SurveyTemplate.from_dict(data)

    assert template.id == 1
    assert template.name == "Test Survey"
    assert template.is_system is True
    assert template.creator_chat_id == 123


def test_survey_question_to_dict():
    """Проверяет сериализацию вопроса в dict."""
    question = SurveyQuestion(
        id=1,
        template_id=1,
        question_text="Test?",
        question_type="text",
        order_index=1,
        is_required=True,
        config='{"key": "value"}',
        help_text="Help"
    )

    data = question.to_dict()

    assert data['id'] == 1
    assert data['template_id'] == 1
    assert data['question_text'] == "Test?"
    assert data['question_type'] == "text"
    assert data['order_index'] == 1
    assert data['is_required'] is True
    assert data['config'] == '{"key": "value"}'
    assert data['help_text'] == "Help"


def test_survey_question_from_dict():
    """Проверяет десериализацию вопроса из dict."""
    data = {
        'id': 1,
        'template_id': 1,
        'question_text': 'Test?',
        'question_type': 'numeric',
        'order_index': 1,
        'is_required': 1,
        'config': '{"min": 1, "max": 10}',
        'help_text': 'Help text'
    }

    question = SurveyQuestion.from_dict(data)

    assert question.id == 1
    assert question.template_id == 1
    assert question.question_type == "numeric"
    assert question.is_required is True


def test_survey_response_to_dict():
    """Проверяет сериализацию ответа в dict."""
    response = SurveyResponse(
        id=1,
        chat_id=123,
        template_id=1,
        response_date="2025-01-15",
        response_time="10:00:00",
        encrypted_data="encrypted",
        created_at="2025-01-15 10:00:00"
    )

    data = response.to_dict()

    assert data['id'] == 1
    assert data['chat_id'] == 123
    assert data['template_id'] == 1
    assert data['response_date'] == "2025-01-15"
    assert data['response_time'] == "10:00:00"
    assert data['encrypted_data'] == "encrypted"


def test_survey_response_from_dict():
    """Проверяет десериализацию ответа из dict."""
    data = {
        'id': 1,
        'chat_id': 123,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:00:00',
        'encrypted_data': 'encrypted_data',
        'created_at': '2025-01-15 10:00:00'
    }

    response = SurveyResponse.from_dict(data)

    assert response.id == 1
    assert response.chat_id == 123
    assert response.response_date == "2025-01-15"


def test_survey_template_roundtrip():
    """Проверяет цикл сериализации/десериализации шаблона."""
    original = SurveyTemplate(
        id=1,
        name="Test",
        description="Desc",
        is_system=False,
        creator_chat_id=123,
        icon="📝"
    )

    data = original.to_dict()
    restored = SurveyTemplate.from_dict(data)

    assert restored.id == original.id
    assert restored.name == original.name
    assert restored.description == original.description
    assert restored.is_system == original.is_system
    assert restored.creator_chat_id == original.creator_chat_id
    assert restored.icon == original.icon


def test_survey_question_roundtrip():
    """Проверяет цикл сериализации/десериализации вопроса."""
    original = SurveyQuestion(
        id=1,
        template_id=1,
        question_text="Test?",
        question_type="choice",
        order_index=2,
        is_required=False,
        config='{"options": ["A", "B"]}',
        help_text="Choose"
    )

    data = original.to_dict()
    restored = SurveyQuestion.from_dict(data)

    assert restored.id == original.id
    assert restored.template_id == original.template_id
    assert restored.question_text == original.question_text
    assert restored.question_type == original.question_type
    assert restored.order_index == original.order_index
    assert restored.is_required == original.is_required
    assert restored.config == original.config
    assert restored.help_text == original.help_text
