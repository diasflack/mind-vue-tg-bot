"""
Тесты для handlers создания пользовательских шаблонов опросов (Phase 3.1).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update
from telegram.ext import ConversationHandler

from src.config import CREATE_SURVEY_NAME, CREATE_SURVEY_DESC


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
    return context


class TestCreateSurveyStart:
    """Тесты для начала создания опроса."""

    @pytest.mark.asyncio
    async def test_create_survey_starts_successfully(self, mock_update, mock_context):
        """Успешное начало создания опроса."""
        from src.handlers.survey_create import create_survey_start

        with patch('src.handlers.survey_create.count_user_templates', return_value=5):
            result = await create_survey_start(mock_update, mock_context)

        assert result == CREATE_SURVEY_NAME
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "название" in call_args.lower()

    @pytest.mark.asyncio
    async def test_create_survey_limit_reached(self, mock_update, mock_context):
        """Попытка создать опрос при достижении лимита (20)."""
        from src.handlers.survey_create import create_survey_start

        with patch('src.handlers.survey_create.count_user_templates', return_value=20):
            result = await create_survey_start(mock_update, mock_context)

        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "лимит" in call_args.lower() or "максимум" in call_args.lower()

    @pytest.mark.asyncio
    async def test_create_survey_db_error(self, mock_update, mock_context):
        """Обработка ошибки БД при проверке лимита."""
        from src.handlers.survey_create import create_survey_start

        with patch('src.handlers.survey_create.count_user_templates', side_effect=Exception("DB error")):
            result = await create_survey_start(mock_update, mock_context)

        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "ошибк" in call_args.lower()


class TestReceiveSurveyName:
    """Тесты для получения названия опроса."""

    @pytest.mark.asyncio
    async def test_receive_name_valid(self, mock_update, mock_context):
        """Успешное получение корректного названия."""
        from src.handlers.survey_create import receive_survey_name

        mock_update.message.text = "Мой опрос"

        with patch('src.handlers.survey_create.get_user_templates', return_value=[]):
            result = await receive_survey_name(mock_update, mock_context)

        assert result == CREATE_SURVEY_DESC
        assert mock_context.user_data['survey_name'] == "Мой опрос"
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "описание" in call_args.lower()

    @pytest.mark.asyncio
    async def test_receive_name_too_short(self, mock_update, mock_context):
        """Название слишком короткое (меньше 3 символов)."""
        from src.handlers.survey_create import receive_survey_name

        mock_update.message.text = "Аб"

        result = await receive_survey_name(mock_update, mock_context)

        assert result == CREATE_SURVEY_NAME
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "3" in call_args or "символ" in call_args.lower()

    @pytest.mark.asyncio
    async def test_receive_name_too_long(self, mock_update, mock_context):
        """Название слишком длинное (больше 50 символов)."""
        from src.handlers.survey_create import receive_survey_name

        mock_update.message.text = "А" * 51

        result = await receive_survey_name(mock_update, mock_context)

        assert result == CREATE_SURVEY_NAME
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "50" in call_args or "длинн" in call_args.lower()

    @pytest.mark.asyncio
    async def test_receive_name_duplicate(self, mock_update, mock_context):
        """Название уже существует у пользователя."""
        from src.handlers.survey_create import receive_survey_name

        mock_update.message.text = "Существующий опрос"

        existing_templates = [
            {'name': 'Существующий опрос', 'id': 1}
        ]

        with patch('src.handlers.survey_create.get_user_templates', return_value=existing_templates):
            result = await receive_survey_name(mock_update, mock_context)

        assert result == CREATE_SURVEY_NAME
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "уже существует" in call_args.lower() or "занят" in call_args.lower()


class TestReceiveSurveyDescription:
    """Тесты для получения описания опроса."""

    @pytest.mark.asyncio
    async def test_receive_description_valid(self, mock_update, mock_context):
        """Успешное создание опроса с описанием."""
        from src.handlers.survey_create import receive_survey_description

        mock_context.user_data['survey_name'] = "Тестовый опрос"
        mock_update.message.text = "Описание тестового опроса"

        with patch('src.handlers.survey_create.create_user_template', return_value=123):
            result = await receive_survey_description(mock_update, mock_context)

        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "создан" in call_args.lower()

    @pytest.mark.asyncio
    async def test_receive_description_too_long(self, mock_update, mock_context):
        """Описание слишком длинное (больше 500 символов)."""
        from src.handlers.survey_create import receive_survey_description

        mock_context.user_data['survey_name'] = "Тестовый опрос"
        mock_update.message.text = "А" * 501

        result = await receive_survey_description(mock_update, mock_context)

        assert result == CREATE_SURVEY_DESC
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "500" in call_args or "длинн" in call_args.lower()

    @pytest.mark.asyncio
    async def test_receive_description_creation_failed(self, mock_update, mock_context):
        """Ошибка при создании шаблона в БД."""
        from src.handlers.survey_create import receive_survey_description

        mock_context.user_data['survey_name'] = "Тестовый опрос"
        mock_update.message.text = "Описание"

        with patch('src.handlers.survey_create.create_user_template', return_value=None):
            result = await receive_survey_description(mock_update, mock_context)

        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "не удалось" in call_args.lower() or "ошибк" in call_args.lower()

    @pytest.mark.asyncio
    async def test_receive_description_empty_context(self, mock_update, mock_context):
        """Отсутствует survey_name в context (некорректное состояние)."""
        from src.handlers.survey_create import receive_survey_description

        mock_update.message.text = "Описание"

        result = await receive_survey_description(mock_update, mock_context)

        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "ошибк" in call_args.lower()


class TestShowMySurveys:
    """Тесты для показа пользовательских опросов."""

    @pytest.mark.asyncio
    async def test_show_my_surveys_empty(self, mock_update, mock_context):
        """Показ когда нет пользовательских опросов."""
        from src.handlers.survey_create import show_my_surveys

        with patch('src.handlers.survey_create.get_user_templates', return_value=[]):
            await show_my_surveys(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "нет" in call_args.lower() or "не создали" in call_args.lower()

    @pytest.mark.asyncio
    async def test_show_my_surveys_single(self, mock_update, mock_context):
        """Показ одного опроса."""
        from src.handlers.survey_create import show_my_surveys

        templates = [
            {
                'id': 1,
                'name': 'Мой опрос',
                'description': 'Описание',
                'is_active': True,
                'created_at': '2025-01-15T10:00:00'
            }
        ]

        with patch('src.handlers.survey_create.get_user_templates', return_value=templates):
            with patch('src.handlers.survey_create.get_template_questions', return_value=[]):
                await show_my_surveys(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Мой опрос" in call_args
        assert "Описание" in call_args

    @pytest.mark.asyncio
    async def test_show_my_surveys_multiple_with_questions(self, mock_update, mock_context):
        """Показ нескольких опросов с вопросами."""
        from src.handlers.survey_create import show_my_surveys

        templates = [
            {
                'id': 1,
                'name': 'Активный опрос',
                'description': 'Описание 1',
                'is_active': True,
                'created_at': '2025-01-15T10:00:00'
            },
            {
                'id': 2,
                'name': 'Неактивный опрос',
                'description': 'Описание 2',
                'is_active': False,
                'created_at': '2025-01-14T10:00:00'
            }
        ]

        questions_template_1 = [{'id': 1}, {'id': 2}, {'id': 3}]
        questions_template_2 = []

        def mock_get_questions(conn, template_id):
            if template_id == 1:
                return questions_template_1
            return questions_template_2

        with patch('src.handlers.survey_create.get_user_templates', return_value=templates):
            with patch('src.handlers.survey_create.get_template_questions', side_effect=mock_get_questions):
                await show_my_surveys(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Активный опрос" in call_args
        assert "Неактивный опрос" in call_args
        assert "3" in call_args  # количество вопросов
        assert "✅" in call_args or "активен" in call_args.lower()

    @pytest.mark.asyncio
    async def test_show_my_surveys_db_error(self, mock_update, mock_context):
        """Обработка ошибки БД."""
        from src.handlers.survey_create import show_my_surveys

        with patch('src.handlers.survey_create.get_user_templates', side_effect=Exception("DB error")):
            await show_my_surveys(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "ошибк" in call_args.lower()


class TestCancelConversation:
    """Тесты для отмены создания опроса."""

    @pytest.mark.asyncio
    async def test_cancel_conversation(self, mock_update, mock_context):
        """Отмена создания опроса."""
        from src.handlers.survey_create import cancel_create_survey

        result = await cancel_create_survey(mock_update, mock_context)

        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "отмен" in call_args.lower()
