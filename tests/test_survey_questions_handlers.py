"""
Тесты для handlers добавления вопросов к пользовательским шаблонам (Phase 3.2).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from src.config import ADD_QUESTION_TYPE, ADD_QUESTION_TEXT, ADD_QUESTION_CONFIG


@pytest.fixture
def mock_update():
    """Создает mock объект Update."""
    update = MagicMock(spec=Update)
    update.effective_chat.id = 12345
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.callback_query = None
    return update


@pytest.fixture
def mock_callback_update():
    """Создает mock объект Update с callback_query."""
    update = MagicMock(spec=Update)
    update.effective_chat.id = 12345
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.message = MagicMock()
    update.callback_query.message.reply_text = AsyncMock()
    update.callback_query.data = ""
    return update


@pytest.fixture
def mock_context():
    """Создает mock объект CallbackContext."""
    context = MagicMock()
    context.user_data = {}
    context.args = []
    return context


class TestAddQuestionStart:
    """Тесты для начала добавления вопроса."""

    @pytest.mark.asyncio
    async def test_add_question_start_success(self, mock_update, mock_context):
        """Успешное начало добавления вопроса."""
        from src.handlers.survey_questions import add_question_start

        mock_context.args = ['Мой опрос']

        mock_template = {
            'id': 1,
            'name': 'Мой опрос',
            'created_by': 12345
        }

        with patch('src.handlers.survey_questions.get_user_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_questions.get_template_questions', return_value=[]):
                result = await add_question_start(mock_update, mock_context)

        assert result == ADD_QUESTION_TYPE
        assert mock_context.user_data['template_id'] == 1
        assert mock_context.user_data['template_name'] == 'Мой опрос'
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_question_no_template_name(self, mock_update, mock_context):
        """Не указано название шаблона."""
        from src.handlers.survey_questions import add_question_start

        mock_context.args = []

        result = await add_question_start(mock_update, mock_context)

        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "название" in call_args.lower()

    @pytest.mark.asyncio
    async def test_add_question_template_not_found(self, mock_update, mock_context):
        """Шаблон не найден."""
        from src.handlers.survey_questions import add_question_start

        mock_context.args = ['Несуществующий']

        with patch('src.handlers.survey_questions.get_user_templates', return_value=[]):
            result = await add_question_start(mock_update, mock_context)

        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "не найден" in call_args.lower()

    @pytest.mark.asyncio
    async def test_add_question_limit_reached(self, mock_update, mock_context):
        """Достигнут лимит вопросов (30)."""
        from src.handlers.survey_questions import add_question_start

        mock_context.args = ['Мой опрос']

        mock_template = {'id': 1, 'name': 'Мой опрос', 'created_by': 12345}
        mock_questions = [{'id': i} for i in range(30)]  # 30 вопросов

        with patch('src.handlers.survey_questions.get_user_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_questions.get_template_questions', return_value=mock_questions):
                result = await add_question_start(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "лимит" in call_args.lower() or "максимум" in call_args.lower()


class TestSelectQuestionType:
    """Тесты выбора типа вопроса."""

    @pytest.mark.asyncio
    async def test_select_type_text(self, mock_callback_update, mock_context):
        """Выбор типа text."""
        from src.handlers.survey_questions import select_question_type

        mock_callback_update.callback_query.data = "qtype_text"
        mock_context.user_data = {'template_id': 1, 'template_name': 'Тест'}

        result = await select_question_type(mock_callback_update, mock_context)

        assert result == ADD_QUESTION_TEXT
        assert mock_context.user_data['question_type'] == 'text'
        mock_callback_update.callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_type_numeric(self, mock_callback_update, mock_context):
        """Выбор типа numeric."""
        from src.handlers.survey_questions import select_question_type

        mock_callback_update.callback_query.data = "qtype_numeric"
        mock_context.user_data = {'template_id': 1, 'template_name': 'Тест'}

        result = await select_question_type(mock_callback_update, mock_context)

        assert result == ADD_QUESTION_TEXT
        assert mock_context.user_data['question_type'] == 'numeric'


class TestReceiveQuestionText:
    """Тесты получения текста вопроса."""

    @pytest.mark.asyncio
    async def test_receive_text_for_simple_type(self, mock_update, mock_context):
        """Получение текста для простого типа (text, yes_no)."""
        from src.handlers.survey_questions import receive_question_text

        mock_update.message.text = "Как ваше настроение?"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Тест',
            'question_type': 'text'
        }

        with patch('src.handlers.survey_questions.add_question_to_template', return_value=123):
            result = await receive_question_text(mock_update, mock_context)

        # Для простых типов сразу END и предложение добавить еще
        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_receive_text_for_numeric_type(self, mock_update, mock_context):
        """Получение текста для numeric - требует конфигурацию."""
        from src.handlers.survey_questions import receive_question_text

        mock_update.message.text = "Оцените от 1 до 10"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Тест',
            'question_type': 'numeric'
        }

        result = await receive_question_text(mock_update, mock_context)

        assert result == ADD_QUESTION_CONFIG
        assert mock_context.user_data['question_text'] == "Оцените от 1 до 10"
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_text_too_short(self, mock_update, mock_context):
        """Текст вопроса слишком короткий."""
        from src.handlers.survey_questions import receive_question_text

        mock_update.message.text = "Короче"  # Меньше 10 символов
        mock_context.user_data = {
            'template_id': 1,
            'question_type': 'text'
        }

        result = await receive_question_text(mock_update, mock_context)

        assert result == ADD_QUESTION_TEXT
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "10" in call_args or "короткий" in call_args.lower()

    @pytest.mark.asyncio
    async def test_receive_text_too_long(self, mock_update, mock_context):
        """Текст вопроса слишком длинный."""
        from src.handlers.survey_questions import receive_question_text

        mock_update.message.text = "А" * 501  # Больше 500 символов
        mock_context.user_data = {
            'template_id': 1,
            'question_type': 'text'
        }

        result = await receive_question_text(mock_update, mock_context)

        assert result == ADD_QUESTION_TEXT
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "500" in call_args


class TestConfigureQuestion:
    """Тесты конфигурации вопросов."""

    @pytest.mark.asyncio
    async def test_configure_numeric_valid(self, mock_update, mock_context):
        """Валидная конфигурация numeric вопроса."""
        from src.handlers.survey_questions import configure_question

        mock_update.message.text = "1 10"  # min max
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Тест',
            'question_type': 'numeric',
            'question_text': 'Оцените'
        }

        with patch('src.handlers.survey_questions.add_question_to_template', return_value=123):
            result = await configure_question(mock_update, mock_context)

        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_configure_numeric_invalid_format(self, mock_update, mock_context):
        """Невалидный формат конфигурации numeric."""
        from src.handlers.survey_questions import configure_question

        mock_update.message.text = "abc"
        mock_context.user_data = {
            'template_id': 1,
            'question_type': 'numeric',
            'question_text': 'Оцените'
        }

        result = await configure_question(mock_update, mock_context)

        assert result == ADD_QUESTION_CONFIG
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "формат" in call_args.lower() or "пример" in call_args.lower()

    @pytest.mark.asyncio
    async def test_configure_choice_valid(self, mock_update, mock_context):
        """Валидная конфигурация choice вопроса."""
        from src.handlers.survey_questions import configure_question

        mock_update.message.text = "single\nВариант 1\nВариант 2\nВариант 3"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Тест',
            'question_type': 'choice',
            'question_text': 'Выберите'
        }

        with patch('src.handlers.survey_questions.add_question_to_template', return_value=123):
            result = await configure_question(mock_update, mock_context)

        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_configure_choice_too_few_options(self, mock_update, mock_context):
        """Слишком мало вариантов для choice."""
        from src.handlers.survey_questions import configure_question

        mock_update.message.text = "single\nВариант 1"  # Только 1 вариант
        mock_context.user_data = {
            'template_id': 1,
            'question_type': 'choice',
            'question_text': 'Выберите'
        }

        result = await configure_question(mock_update, mock_context)

        assert result == ADD_QUESTION_CONFIG
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "минимум 2" in call_args.lower() or "мало" in call_args.lower()

    @pytest.mark.asyncio
    async def test_configure_scale_valid(self, mock_update, mock_context):
        """Валидная конфигурация scale вопроса."""
        from src.handlers.survey_questions import configure_question

        mock_update.message.text = "1 10 1"  # min max step
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Тест',
            'question_type': 'scale',
            'question_text': 'Оцените'
        }

        with patch('src.handlers.survey_questions.add_question_to_template', return_value=123):
            result = await configure_question(mock_update, mock_context)

        assert result == ConversationHandler.END


class TestSaveQuestion:
    """Тесты сохранения вопроса."""

    @pytest.mark.asyncio
    async def test_save_question_success(self, mock_update, mock_context):
        """Успешное сохранение вопроса."""
        from src.handlers.survey_questions import receive_question_text

        mock_update.message.text = "Это текстовый вопрос?"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Тест',
            'question_type': 'text'
        }

        with patch('src.handlers.survey_questions.add_question_to_template', return_value=123):
            result = await receive_question_text(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "добавлен" in call_args.lower()

    @pytest.mark.asyncio
    async def test_save_question_failed(self, mock_update, mock_context):
        """Ошибка при сохранении вопроса."""
        from src.handlers.survey_questions import receive_question_text

        mock_update.message.text = "Это текстовый вопрос?"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Тест',
            'question_type': 'text'
        }

        with patch('src.handlers.survey_questions.add_question_to_template', return_value=None):
            result = await receive_question_text(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "ошибк" in call_args.lower() or "не удалось" in call_args.lower()
