"""
Тесты для handlers редактирования пользовательских шаблонов (Phase 3.3).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from src.config import EDIT_SURVEY_SELECT, EDIT_QUESTION_SELECT


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


class TestEditSurveyStart:
    """Тесты для начала редактирования опроса."""

    @pytest.mark.asyncio
    async def test_edit_survey_as_owner(self, mock_update, mock_context):
        """Владелец может редактировать свой опрос."""
        from src.handlers.survey_edit import edit_survey_start

        mock_context.args = ['Мой опрос']

        mock_template = {
            'id': 1,
            'name': 'Мой опрос',
            'description': 'Описание',
            'created_by': 12345,
            'is_system': False,
            'is_active': True
        }

        with patch('src.handlers.survey_edit.get_user_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_edit.get_template_questions', return_value=[]):
                result = await edit_survey_start(mock_update, mock_context)

        assert result == EDIT_SURVEY_SELECT
        assert mock_context.user_data['template_id'] == 1
        assert mock_context.user_data['template_name'] == 'Мой опрос'
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_survey_not_owner(self, mock_update, mock_context):
        """Не владелец не может редактировать чужой опрос."""
        from src.handlers.survey_edit import edit_survey_start

        mock_context.args = ['Чужой опрос']

        # get_user_templates возвращает пустой список для chat_id=12345
        # так как мы запрашиваем шаблоны пользователя 12345, но реального шаблона у него нет
        with patch('src.handlers.survey_edit.get_user_templates', return_value=[]):
            result = await edit_survey_start(mock_update, mock_context)

        # Не должен найти шаблон (get_user_templates фильтрует по chat_id)
        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "не найден" in call_args.lower()

    @pytest.mark.asyncio
    async def test_edit_system_survey_forbidden(self, mock_update, mock_context):
        """Нельзя редактировать системные шаблоны."""
        from src.handlers.survey_edit import edit_survey_start

        mock_context.args = ['Системный']

        mock_template = {
            'id': 1,
            'name': 'Системный',
            'created_by': 12345,
            'is_system': True
        }

        with patch('src.handlers.survey_edit.get_user_templates', return_value=[mock_template]):
            result = await edit_survey_start(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "системн" in call_args.lower() or "нельзя" in call_args.lower()

    @pytest.mark.asyncio
    async def test_edit_survey_no_name(self, mock_update, mock_context):
        """Не указано название шаблона."""
        from src.handlers.survey_edit import edit_survey_start

        mock_context.args = []

        result = await edit_survey_start(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "укажите" in call_args.lower() or "название" in call_args.lower()


class TestEditSurveyName:
    """Тесты редактирования названия опроса."""

    @pytest.mark.asyncio
    async def test_edit_name_valid(self, mock_update, mock_context):
        """Успешное изменение названия."""
        from src.handlers.survey_edit import edit_survey_name

        mock_update.message.text = "Новое название"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Старое название'
        }

        with patch('src.handlers.survey_edit.get_user_templates', return_value=[]):
            with patch('src.handlers.survey_edit.update_template', return_value=True):
                result = await edit_survey_name(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "обновлен" in call_args.lower() or "изменен" in call_args.lower()

    @pytest.mark.asyncio
    async def test_edit_name_duplicate(self, mock_update, mock_context):
        """Новое название уже занято."""
        from src.handlers.survey_edit import edit_survey_name

        mock_update.message.text = "Занятое название"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Старое название'
        }

        existing = [
            {'id': 2, 'name': 'Занятое название', 'created_by': 12345}
        ]

        with patch('src.handlers.survey_edit.get_user_templates', return_value=existing):
            result = await edit_survey_name(mock_update, mock_context)

        assert result == EDIT_SURVEY_SELECT
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "уже существует" in call_args.lower() or "занят" in call_args.lower()

    @pytest.mark.asyncio
    async def test_edit_name_too_short(self, mock_update, mock_context):
        """Новое название слишком короткое."""
        from src.handlers.survey_edit import edit_survey_name

        mock_update.message.text = "Аб"
        mock_context.user_data = {'template_id': 1, 'template_name': 'Старое'}

        result = await edit_survey_name(mock_update, mock_context)

        assert result == EDIT_SURVEY_SELECT
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "3" in call_args or "короткое" in call_args.lower()


class TestEditSurveyDescription:
    """Тесты редактирования описания опроса."""

    @pytest.mark.asyncio
    async def test_edit_description_valid(self, mock_update, mock_context):
        """Успешное изменение описания."""
        from src.handlers.survey_edit import edit_survey_description

        mock_update.message.text = "Новое описание"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Опрос'
        }

        with patch('src.handlers.survey_edit.update_template', return_value=True):
            result = await edit_survey_description(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "обновлен" in call_args.lower() or "изменен" in call_args.lower()

    @pytest.mark.asyncio
    async def test_edit_description_too_long(self, mock_update, mock_context):
        """Описание слишком длинное."""
        from src.handlers.survey_edit import edit_survey_description

        mock_update.message.text = "А" * 501
        mock_context.user_data = {'template_id': 1, 'template_name': 'Опрос'}

        result = await edit_survey_description(mock_update, mock_context)

        assert result == EDIT_SURVEY_SELECT
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "500" in call_args or "длинн" in call_args.lower()


class TestEditQuestion:
    """Тесты редактирования вопросов."""

    @pytest.mark.asyncio
    async def test_edit_question_text(self, mock_update, mock_context):
        """Изменение текста вопроса."""
        from src.handlers.survey_edit import edit_question_text

        mock_update.message.text = "Новый текст вопроса"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Опрос',
            'question_id': 10
        }

        with patch('src.handlers.survey_edit.update_question', return_value=True):
            result = await edit_question_text(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "обновлен" in call_args.lower() or "изменен" in call_args.lower()

    @pytest.mark.asyncio
    async def test_edit_question_text_too_short(self, mock_update, mock_context):
        """Новый текст вопроса слишком короткий."""
        from src.handlers.survey_edit import edit_question_text

        mock_update.message.text = "Короче"
        mock_context.user_data = {
            'template_id': 1,
            'question_id': 10
        }

        result = await edit_question_text(mock_update, mock_context)

        assert result == EDIT_QUESTION_SELECT
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "10" in call_args or "короткий" in call_args.lower()


class TestDeleteQuestion:
    """Тесты удаления вопроса."""

    @pytest.mark.asyncio
    async def test_delete_question_success(self, mock_update, mock_context):
        """Успешное удаление вопроса."""
        from src.handlers.survey_edit import delete_question_confirm

        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Опрос',
            'question_id': 10
        }

        with patch('src.handlers.survey_edit.delete_question', return_value=True):
            result = await delete_question_confirm(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "удален" in call_args.lower()

    @pytest.mark.asyncio
    async def test_delete_question_failed(self, mock_update, mock_context):
        """Ошибка при удалении вопроса."""
        from src.handlers.survey_edit import delete_question_confirm

        mock_context.user_data = {
            'template_id': 1,
            'question_id': 10
        }

        with patch('src.handlers.survey_edit.delete_question', return_value=False):
            result = await delete_question_confirm(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "ошибк" in call_args.lower() or "не удалось" in call_args.lower()
