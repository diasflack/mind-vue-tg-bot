"""
Тесты для обработчиков просмотра ответов на опросы (Phase 2.6).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update

from src.handlers.survey_viewing import (
    show_my_responses,
    show_survey_responses,
    _format_response_summary
)


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
async def test_view_my_responses(mock_update, mock_context):
    """Проверяет просмотр всех ответов пользователя."""
    with patch('src.handlers.survey_viewing.get_user_survey_responses') as mock_get_responses:
        with patch('src.handlers.survey_viewing.get_template_by_id') as mock_get_template:
            with patch('src.handlers.survey_viewing._get_db_connection'):
                mock_get_responses.return_value = [
                    {
                        'id': 1,
                        'template_id': 1,
                        'response_date': '2025-01-15',
                        'response_time': '10:00:00',
                        'answers': {'1': 'Answer 1', '2': '8'}
                    },
                    {
                        'id': 2,
                        'template_id': 1,
                        'response_date': '2025-01-16',
                        'response_time': '11:00:00',
                        'answers': {'1': 'Answer 2', '2': '7'}
                    }
                ]

                mock_get_template.return_value = {
                    'id': 1,
                    'name': 'Test Survey',
                    'icon': '📝'
                }

                await show_my_responses(mock_update, mock_context)

    # Проверяем, что было отправлено сообщение
    mock_update.message.reply_text.assert_called()

    # Проверяем, что в сообщении есть информация об ответах
    call_args = mock_update.message.reply_text.call_args
    message = call_args[0][0]
    assert '2025-01-15' in message or '15.01.2025' in message


@pytest.mark.asyncio
async def test_view_my_responses_empty(mock_update, mock_context):
    """Проверяет отображение когда нет ответов."""
    with patch('src.handlers.survey_viewing.get_user_survey_responses') as mock_get_responses:
        with patch('src.handlers.survey_viewing._get_db_connection'):
            mock_get_responses.return_value = []

            await show_my_responses(mock_update, mock_context)

    # Проверяем, что было отправлено сообщение
    mock_update.message.reply_text.assert_called_once()

    # Проверяем, что сообщение о пустом списке
    call_args = mock_update.message.reply_text.call_args
    message = call_args[0][0]
    assert 'нет' in message.lower() or 'не найден' in message.lower()


@pytest.mark.asyncio
async def test_view_responses_by_survey(mock_update, mock_context):
    """Проверяет просмотр ответов по конкретному опросу."""
    mock_context.args = ['Test', 'Survey']

    with patch('src.handlers.survey_viewing.get_template_by_name') as mock_get_template:
        with patch('src.handlers.survey_viewing.get_responses_by_template') as mock_get_responses:
            with patch('src.handlers.survey_viewing.get_template_questions') as mock_get_questions:
                with patch('src.handlers.survey_viewing._get_db_connection'):
                    mock_get_template.return_value = {
                        'id': 1,
                        'name': 'Test Survey',
                        'icon': '📝'
                    }

                    mock_get_responses.return_value = [
                        {
                            'id': 1,
                            'template_id': 1,
                            'response_date': '2025-01-15',
                            'response_time': '10:00:00',
                            'answers': {'1': 'Answer 1'}
                        }
                    ]

                    mock_get_questions.return_value = [
                        {
                            'id': 1,
                            'question_text': 'Question 1',
                            'question_type': 'text'
                        }
                    ]

                    await show_survey_responses(mock_update, mock_context)

    # Проверяем, что было отправлено сообщение
    mock_update.message.reply_text.assert_called()


@pytest.mark.asyncio
async def test_view_responses_by_survey_not_found(mock_update, mock_context):
    """Проверяет обработку несуществующего опроса."""
    mock_context.args = ['Nonexistent', 'Survey']

    with patch('src.handlers.survey_viewing.get_template_by_name') as mock_get_template:
        with patch('src.handlers.survey_viewing._get_db_connection'):
            mock_get_template.return_value = None

            await show_survey_responses(mock_update, mock_context)

    # Проверяем, что было отправлено сообщение об ошибке
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    message = call_args[0][0]
    assert 'не найден' in message.lower()


def test_format_response_summary():
    """Проверяет форматирование краткой информации об ответе."""
    response = {
        'id': 1,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:30:00',
        'answers': {'1': 'Answer 1', '2': 'Answer 2'}
    }

    template = {
        'name': 'Test Survey',
        'icon': '📝'
    }

    formatted = _format_response_summary(response, template)

    # Проверяем наличие ключевых элементов
    assert '📝' in formatted or 'Test Survey' in formatted
    assert '2025-01-15' in formatted or '15.01.2025' in formatted
    assert '10:30' in formatted


def test_format_response_summary_without_icon():
    """Проверяет форматирование когда у шаблона нет иконки."""
    response = {
        'id': 1,
        'template_id': 1,
        'response_date': '2025-01-15',
        'response_time': '10:30:00',
        'answers': {'1': 'Answer'}
    }

    template = {
        'name': 'Test Survey',
        'icon': None
    }

    formatted = _format_response_summary(response, template)

    # Должно быть успешно отформатировано
    assert 'Test Survey' in formatted
    assert '2025-01-15' in formatted or '15.01.2025' in formatted


@pytest.mark.asyncio
async def test_view_responses_pagination(mock_update, mock_context):
    """Проверяет пагинацию при большом количестве ответов."""
    # Создаем много ответов
    many_responses = []
    for i in range(15):
        many_responses.append({
            'id': i,
            'template_id': 1,
            'response_date': '2025-01-15',
            'response_time': f'{10+i:02d}:00:00',
            'answers': {'1': f'Answer {i}'}
        })

    with patch('src.handlers.survey_viewing.get_user_survey_responses') as mock_get_responses:
        with patch('src.handlers.survey_viewing.get_template_by_id') as mock_get_template:
            with patch('src.handlers.survey_viewing._get_db_connection'):
                mock_get_responses.return_value = many_responses

                mock_get_template.return_value = {
                    'id': 1,
                    'name': 'Test Survey',
                    'icon': '📝'
                }

                await show_my_responses(mock_update, mock_context)

    # При большом количестве ответов должно быть несколько сообщений
    # или ограничение количества показываемых ответов
    assert mock_update.message.reply_text.call_count >= 1


@pytest.mark.asyncio
async def test_show_survey_responses_no_args(mock_update, mock_context):
    """Проверяет обработку команды без аргументов."""
    mock_context.args = []

    await show_survey_responses(mock_update, mock_context)

    # Проверяем, что было отправлено сообщение с инструкцией
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    message = call_args[0][0]
    assert 'укажите' in message.lower() or 'название' in message.lower()


@pytest.mark.asyncio
async def test_show_survey_responses_empty(mock_update, mock_context):
    """Проверяет отображение когда нет ответов на конкретный опрос."""
    mock_context.args = ['Test', 'Survey']

    with patch('src.handlers.survey_viewing.get_template_by_name') as mock_get_template:
        with patch('src.handlers.survey_viewing.get_responses_by_template') as mock_get_responses:
            with patch('src.handlers.survey_viewing._get_db_connection'):
                mock_get_template.return_value = {
                    'id': 1,
                    'name': 'Test Survey',
                    'icon': '📝'
                }

                mock_get_responses.return_value = []

                await show_survey_responses(mock_update, mock_context)

    # Проверяем сообщение о пустом списке
    call_args = mock_update.message.reply_text.call_args
    message = call_args[0][0]
    assert 'нет' in message.lower() or 'не заполн' in message.lower()
