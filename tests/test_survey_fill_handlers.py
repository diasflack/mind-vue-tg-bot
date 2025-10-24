"""
Тесты для обработчиков заполнения опросов (Phase 2.5).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update
from telegram.ext import ConversationHandler

from src.handlers.survey_handlers import (
    list_surveys,
    start_fill_survey,
    handle_survey_answer,
    cancel_survey,
    survey_conversation_handler,
    _validate_answer
)
from src.config import SURVEY_ANSWER


@pytest.fixture
def mock_update():
    """Создает mock Update объект."""
    update = MagicMock(spec=Update)
    update.effective_chat.id = 123
    update.effective_user.id = 123
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    update.message.text = "test"
    return update


@pytest.fixture
def mock_context():
    """Создает mock Context объект."""
    context = MagicMock()
    context.user_data = {}
    context.args = []
    return context


@pytest.mark.asyncio
async def test_list_surveys_command(mock_update, mock_context):
    """Проверяет команду /surveys - список доступных опросов."""
    with patch('src.handlers.survey_handlers.get_available_templates') as mock_get_templates:
        with patch('src.handlers.survey_handlers._get_db_connection'):
            mock_get_templates.return_value = [
                {
                    'id': 1,
                    'name': 'Test Survey',
                    'description': 'Test Description',
                    'icon': '📝',
                    'is_system': True
                }
            ]

            await list_surveys(mock_update, mock_context)

    # Проверяем, что было отправлено сообщение
    mock_update.message.reply_text.assert_called_once()

    # Проверяем, что в сообщении есть название опроса
    call_args = mock_update.message.reply_text.call_args
    message = call_args[0][0]
    assert 'Test Survey' in message
    assert '📝' in message


@pytest.mark.asyncio
async def test_start_fill_survey_no_args(mock_update, mock_context):
    """Проверяет начало заполнения без указания имени опроса."""
    mock_context.args = []

    result = await start_fill_survey(mock_update, mock_context)

    # Должен вернуть ConversationHandler.END
    assert result == ConversationHandler.END

    # Проверяем, что отправлено сообщение с инструкцией
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_start_fill_survey_valid(mock_update, mock_context):
    """Проверяет начало заполнения опроса с валидным именем."""
    mock_context.args = ['Test', 'Survey']

    with patch('src.handlers.survey_handlers.get_template_by_name') as mock_by_name:
        with patch('src.handlers.survey_handlers.get_template_questions') as mock_questions:
            with patch('src.handlers.survey_handlers._get_db_connection'):
                with patch('src.handlers.survey_handlers.register_conversation'):
                    mock_by_name.return_value = {
                        'id': 1,
                        'name': 'Test Survey',
                        'description': 'Test Description'
                    }

                    mock_questions.return_value = [
                        {
                            'id': 1,
                            'question_text': 'What is your name?',
                            'question_type': 'text',
                            'order_index': 1,
                            'is_required': True,
                            'config': None,
                            'help_text': 'Enter your name'
                        }
                    ]

                    result = await start_fill_survey(mock_update, mock_context)

    # Проверяем, что диалог начался
    assert result == SURVEY_ANSWER

    # Проверяем, что данные сохранены в context
    assert 'survey' in mock_context.user_data
    assert mock_context.user_data['survey']['template_id'] == 1


def test_validate_text_question():
    """Проверяет валидацию текстового вопроса."""
    question = {
        'question_type': 'text',
        'is_required': True
    }

    # Валидный ответ
    is_valid, error = _validate_answer("Some text", question)
    assert is_valid is True

    # Пустой ответ
    is_valid, error = _validate_answer("", question)
    assert is_valid is False


def test_validate_numeric_question():
    """Проверяет валидацию числового вопроса."""
    question = {
        'question_type': 'numeric',
        'config': '{"min": 1, "max": 10}',
        'is_required': True
    }

    # Валидное число
    is_valid, error = _validate_answer("5", question)
    assert is_valid is True

    # Число вне диапазона
    is_valid, error = _validate_answer("15", question)
    assert is_valid is False

    # Не число
    is_valid, error = _validate_answer("abc", question)
    assert is_valid is False


def test_validate_yes_no_question():
    """Проверяет валидацию yes/no вопроса."""
    question = {
        'question_type': 'yes_no',
        'is_required': True
    }

    # Валидные ответы
    for answer in ['да', 'нет', 'yes', 'no', 'Да', 'NO']:
        is_valid, error = _validate_answer(answer, question)
        assert is_valid is True, f"Answer '{answer}' should be valid"

    # Невалидный ответ
    is_valid, error = _validate_answer("maybe", question)
    assert is_valid is False


def test_validate_time_question():
    """Проверяет валидацию time вопроса."""
    question = {
        'question_type': 'time',
        'is_required': True
    }

    # Валидные форматы
    for time in ['14:30', '08:00', '23:59', '0:00']:
        is_valid, error = _validate_answer(time, question)
        assert is_valid is True, f"Time '{time}' should be valid"

    # Невалидные форматы
    for time in ['25:00', '14:60', '14-30', 'abc']:
        is_valid, error = _validate_answer(time, question)
        assert is_valid is False, f"Time '{time}' should be invalid"


def test_validate_choice_question():
    """Проверяет валидацию choice вопроса."""
    question = {
        'question_type': 'choice',
        'config': '{"options": ["Option 1", "Option 2", "Option 3"]}',
        'is_required': True
    }

    # Валидный выбор по номеру
    is_valid, error = _validate_answer("1", question)
    assert is_valid is True

    is_valid, error = _validate_answer("2", question)
    assert is_valid is True

    # Множественный выбор
    is_valid, error = _validate_answer("1,2", question)
    assert is_valid is True

    # Невалидный номер
    is_valid, error = _validate_answer("5", question)
    assert is_valid is False


@pytest.mark.asyncio
async def test_cancel_survey(mock_update, mock_context):
    """Проверяет отмену заполнения опроса."""
    mock_context.user_data['survey'] = {
        'template_id': 1,
        'current_question': 1,
        'answers': {'1': 'some answer'}
    }

    with patch('src.handlers.survey_handlers.end_conversation'):
        result = await cancel_survey(mock_update, mock_context)

    # Проверяем, что диалог завершен
    assert result == ConversationHandler.END

    # Проверяем, что данные очищены
    assert 'survey' not in mock_context.user_data

    # Проверяем сообщение
    mock_update.message.reply_text.assert_called_once()


def test_conversation_handler_exists():
    """Проверяет, что ConversationHandler создан."""
    assert survey_conversation_handler is not None
    assert isinstance(survey_conversation_handler, ConversationHandler)


def test_states_defined_in_config():
    """Проверяет, что необходимые состояния определены в config."""
    from src.config import SURVEY_ANSWER

    assert SURVEY_ANSWER is not None
    assert isinstance(SURVEY_ANSWER, int)
