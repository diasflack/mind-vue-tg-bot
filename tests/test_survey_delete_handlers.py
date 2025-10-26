"""
Тесты для handlers удаления и активации пользовательских шаблонов (Phase 3.4).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update
from telegram.ext import ConversationHandler

from src.config import DELETE_SURVEY_CONFIRM


@pytest.fixture
def mock_update():
    """Создает mock объект Update."""
    update = MagicMock(spec=Update)
    update.effective_chat.id = 12345
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Создает mock объект CallbackContext."""
    context = MagicMock()
    context.user_data = {}
    context.args = []
    return context


class TestDeleteSurvey:
    """Тесты для удаления опросов."""

    @pytest.mark.asyncio
    async def test_delete_survey_as_owner(self, mock_update, mock_context):
        """Владелец может удалить свой опрос."""
        from src.handlers.survey_delete import delete_survey_start

        mock_context.args = ['Мой опрос']

        mock_template = {
            'id': 1,
            'name': 'Мой опрос',
            'created_by': 12345,
            'is_system': False
        }

        with patch('src.handlers.survey_delete.get_user_templates', return_value=[mock_template]):
            result = await delete_survey_start(mock_update, mock_context)

        assert result == DELETE_SURVEY_CONFIRM
        assert mock_context.user_data['template_id'] == 1
        assert mock_context.user_data['template_name'] == 'Мой опрос'
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "удалить" in call_args.lower() or "подтвержд" in call_args.lower()

    @pytest.mark.asyncio
    async def test_delete_survey_not_owner(self, mock_update, mock_context):
        """Не владелец не может удалить чужой опрос."""
        from src.handlers.survey_delete import delete_survey_start

        mock_context.args = ['Чужой опрос']

        # Возвращаем пустой список (шаблон принадлежит другому пользователю)
        with patch('src.handlers.survey_delete.get_user_templates', return_value=[]):
            result = await delete_survey_start(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "не найден" in call_args.lower()

    @pytest.mark.asyncio
    async def test_delete_system_survey_forbidden(self, mock_update, mock_context):
        """Нельзя удалить системные шаблоны."""
        from src.handlers.survey_delete import delete_survey_start

        mock_context.args = ['Системный']

        mock_template = {
            'id': 1,
            'name': 'Системный',
            'created_by': 12345,
            'is_system': True
        }

        with patch('src.handlers.survey_delete.get_user_templates', return_value=[mock_template]):
            result = await delete_survey_start(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "системн" in call_args.lower() or "нельзя" in call_args.lower()

    @pytest.mark.asyncio
    async def test_confirm_delete_survey(self, mock_update, mock_context):
        """Подтверждение удаления опроса."""
        from src.handlers.survey_delete import confirm_delete_survey

        mock_update.message.text = "да"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Тестовый опрос'
        }

        with patch('src.handlers.survey_delete.delete_template', return_value=True):
            result = await confirm_delete_survey(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "удален" in call_args.lower()

    @pytest.mark.asyncio
    async def test_cancel_delete_survey(self, mock_update, mock_context):
        """Отмена удаления опроса."""
        from src.handlers.survey_delete import confirm_delete_survey

        mock_update.message.text = "нет"
        mock_context.user_data = {
            'template_id': 1,
            'template_name': 'Тестовый опрос'
        }

        result = await confirm_delete_survey(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "отмен" in call_args.lower()

    @pytest.mark.asyncio
    async def test_delete_no_template_name(self, mock_update, mock_context):
        """Не указано название шаблона для удаления."""
        from src.handlers.survey_delete import delete_survey_start

        mock_context.args = []

        result = await delete_survey_start(mock_update, mock_context)

        assert result == ConversationHandler.END
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "укажите" in call_args.lower() or "название" in call_args.lower()


class TestActivateSurvey:
    """Тесты для активации опросов."""

    @pytest.mark.asyncio
    async def test_activate_survey_with_questions(self, mock_update, mock_context):
        """Активация опроса с вопросами."""
        from src.handlers.survey_delete import activate_survey

        mock_context.args = ['Опрос с вопросами']

        mock_template = {
            'id': 1,
            'name': 'Опрос с вопросами',
            'created_by': 12345,
            'is_system': False,
            'is_active': False
        }

        mock_questions = [{'id': 1}, {'id': 2}]  # 2 вопроса

        with patch('src.handlers.survey_delete.get_user_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_delete.get_template_questions', return_value=mock_questions):
                with patch('src.handlers.survey_delete.update_template', return_value=True):
                    await activate_survey(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "активирован" in call_args.lower()

    @pytest.mark.asyncio
    async def test_activate_survey_no_questions(self, mock_update, mock_context):
        """Попытка активировать опрос без вопросов."""
        from src.handlers.survey_delete import activate_survey

        mock_context.args = ['Пустой опрос']

        mock_template = {
            'id': 1,
            'name': 'Пустой опрос',
            'created_by': 12345,
            'is_system': False,
            'is_active': False
        }

        with patch('src.handlers.survey_delete.get_user_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_delete.get_template_questions', return_value=[]):
                await activate_survey(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "вопрос" in call_args.lower() and ("нет" in call_args.lower() or "добавьте" in call_args.lower())

    @pytest.mark.asyncio
    async def test_activate_survey_already_active(self, mock_update, mock_context):
        """Активация уже активного опроса."""
        from src.handlers.survey_delete import activate_survey

        mock_context.args = ['Активный опрос']

        mock_template = {
            'id': 1,
            'name': 'Активный опрос',
            'created_by': 12345,
            'is_system': False,
            'is_active': True
        }

        with patch('src.handlers.survey_delete.get_user_templates', return_value=[mock_template]):
            await activate_survey(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "уже активен" in call_args.lower() or "активирован" in call_args.lower()

    @pytest.mark.asyncio
    async def test_activate_survey_not_found(self, mock_update, mock_context):
        """Попытка активировать несуществующий опрос."""
        from src.handlers.survey_delete import activate_survey

        mock_context.args = ['Несуществующий']

        with patch('src.handlers.survey_delete.get_user_templates', return_value=[]):
            await activate_survey(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "не найден" in call_args.lower()


class TestDeactivateSurvey:
    """Тесты для деактивации опросов."""

    @pytest.mark.asyncio
    async def test_deactivate_survey(self, mock_update, mock_context):
        """Деактивация активного опроса."""
        from src.handlers.survey_delete import deactivate_survey

        mock_context.args = ['Активный опрос']

        mock_template = {
            'id': 1,
            'name': 'Активный опрос',
            'created_by': 12345,
            'is_system': False,
            'is_active': True
        }

        with patch('src.handlers.survey_delete.get_user_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_delete.update_template', return_value=True):
                await deactivate_survey(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "деактивирован" in call_args.lower()

    @pytest.mark.asyncio
    async def test_deactivate_survey_already_inactive(self, mock_update, mock_context):
        """Деактивация уже неактивного опроса."""
        from src.handlers.survey_delete import deactivate_survey

        mock_context.args = ['Неактивный опрос']

        mock_template = {
            'id': 1,
            'name': 'Неактивный опрос',
            'created_by': 12345,
            'is_system': False,
            'is_active': False
        }

        with patch('src.handlers.survey_delete.get_user_templates', return_value=[mock_template]):
            await deactivate_survey(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "уже неактивен" in call_args.lower() or "деактивирован" in call_args.lower()

    @pytest.mark.asyncio
    async def test_deactivate_survey_not_found(self, mock_update, mock_context):
        """Попытка деактивировать несуществующий опрос."""
        from src.handlers.survey_delete import deactivate_survey

        mock_context.args = ['Несуществующий']

        with patch('src.handlers.survey_delete.get_user_templates', return_value=[]):
            await deactivate_survey(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "не найден" in call_args.lower()

    @pytest.mark.asyncio
    async def test_deactivate_system_survey_forbidden(self, mock_update, mock_context):
        """Нельзя деактивировать системные шаблоны."""
        from src.handlers.survey_delete import deactivate_survey

        mock_context.args = ['Системный']

        mock_template = {
            'id': 1,
            'name': 'Системный',
            'created_by': 12345,
            'is_system': True,
            'is_active': True
        }

        with patch('src.handlers.survey_delete.get_user_templates', return_value=[mock_template]):
            await deactivate_survey(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "системн" in call_args.lower() or "нельзя" in call_args.lower()
