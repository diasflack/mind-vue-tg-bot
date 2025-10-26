"""
Тесты для обработчика добавления впечатлений (impression_handler).

TDD Phase 1.4: Эти тесты должны провалиться до реализации обработчика.
"""

import unittest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from telegram.ext import ConversationHandler


class TestImpressionHandler(unittest.IsolatedAsyncioTestCase):
    """Test impression conversation flow."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock Update and Context
        self.update = MagicMock()
        self.context = MagicMock()

        # Mock effective_chat and effective_user
        self.test_chat_id = 123456789
        self.test_username = "test_user"
        self.test_first_name = "Test"

        self.update.effective_chat.id = self.test_chat_id
        self.update.effective_user.username = self.test_username
        self.update.effective_user.first_name = self.test_first_name

        # Mock message and its reply methods
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()
        self.update.effective_message = self.update.message
        self.update.message.text = ""

        # Mock user_data
        self.context.user_data = {}

    @patch('src.handlers.impression_handler.save_user')
    @patch('src.handlers.impression_handler.end_all_conversations')
    @patch('src.handlers.impression_handler.register_conversation')
    async def test_start_impression(self, mock_register, mock_end_all, mock_save_user):
        """Тест: начало диалога добавления впечатления."""
        from src.handlers.impression_handler import start_impression, IMPRESSION_TEXT

        result = await start_impression(self.update, self.context)

        # Проверяем что диалоги управляются корректно
        mock_end_all.assert_called_once_with(self.test_chat_id)
        mock_register.assert_called_once()

        # Проверяем что пользователь сохранен
        mock_save_user.assert_called_once_with(
            self.test_chat_id,
            self.test_username,
            self.test_first_name
        )

        # Проверяем что impression инициализирован в user_data
        self.assertIn('impression', self.context.user_data)
        self.assertIn('impression_date', self.context.user_data['impression'])
        self.assertIn('impression_time', self.context.user_data['impression'])

        # Проверяем что сообщение отправлено
        self.update.effective_message.reply_text.assert_called_once()
        call_args = self.update.effective_message.reply_text.call_args
        message_text = call_args[0][0]

        self.assertIn("впечатление", message_text.lower())

        # Проверяем что возвращено правильное состояние
        self.assertEqual(result, IMPRESSION_TEXT)

    async def test_handle_impression_text(self):
        """Тест: обработка ввода текста впечатления."""
        from src.handlers.impression_handler import handle_impression_text, IMPRESSION_INTENSITY

        # Устанавливаем текст сообщения
        self.update.message.text = "Хочется выпить"
        self.context.user_data['impression'] = {}

        result = await handle_impression_text(self.update, self.context)

        # Проверяем что текст сохранен
        self.assertEqual(
            self.context.user_data['impression']['impression_text'],
            "Хочется выпить"
        )

        # Проверяем что запрошена интенсивность
        self.update.effective_message.reply_text.assert_called_once()
        call_args = self.update.effective_message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("интенсивность", message_text.lower())

        # Проверяем состояние
        self.assertEqual(result, IMPRESSION_INTENSITY)

    async def test_handle_impression_intensity_with_value(self):
        """Тест: обработка ввода интенсивности (число 1-10)."""
        from src.handlers.impression_handler import handle_impression_intensity, IMPRESSION_CATEGORY

        self.update.message.text = "7"
        self.context.user_data['impression'] = {}

        result = await handle_impression_intensity(self.update, self.context)

        # Проверяем что интенсивность сохранена
        self.assertEqual(self.context.user_data['impression']['intensity'], 7)

        # Проверяем что запрошена категория
        self.update.effective_message.reply_text.assert_called_once()

        # Проверяем состояние
        self.assertEqual(result, IMPRESSION_CATEGORY)

    async def test_handle_impression_intensity_skip(self):
        """Тест: пропуск интенсивности через /skip."""
        from src.handlers.impression_handler import handle_impression_intensity, IMPRESSION_CATEGORY

        self.update.message.text = "/skip"
        self.context.user_data['impression'] = {}

        result = await handle_impression_intensity(self.update, self.context)

        # Проверяем что интенсивность None
        self.assertIsNone(self.context.user_data['impression']['intensity'])

        # Проверяем состояние
        self.assertEqual(result, IMPRESSION_CATEGORY)

    async def test_handle_impression_intensity_invalid(self):
        """Тест: неправильная интенсивность (не 1-10)."""
        from src.handlers.impression_handler import handle_impression_intensity, IMPRESSION_INTENSITY

        self.update.message.text = "15"
        self.context.user_data['impression'] = {}

        result = await handle_impression_intensity(self.update, self.context)

        # Проверяем что интенсивность не сохранена
        self.assertNotIn('intensity', self.context.user_data['impression'])

        # Проверяем что отправлено сообщение об ошибке
        self.update.effective_message.reply_text.assert_called_once()
        call_args = self.update.effective_message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("1", message_text)
        self.assertIn("10", message_text)

        # Остаемся в том же состоянии
        self.assertEqual(result, IMPRESSION_INTENSITY)

    async def test_handle_impression_category_selection(self):
        """Тест: выбор категории."""
        from src.handlers.impression_handler import handle_impression_category, IMPRESSION_TAGS

        self.update.message.text = "1"  # craving
        self.context.user_data['impression'] = {}

        result = await handle_impression_category(self.update, self.context)

        # Проверяем что категория сохранена
        self.assertIn('category', self.context.user_data['impression'])

        # Проверяем состояние
        self.assertEqual(result, IMPRESSION_TAGS)

    async def test_handle_impression_category_skip(self):
        """Тест: пропуск категории."""
        from src.handlers.impression_handler import handle_impression_category, IMPRESSION_TAGS

        self.update.message.text = "/skip"
        self.context.user_data['impression'] = {}

        result = await handle_impression_category(self.update, self.context)

        # Проверяем что категория None
        self.assertIsNone(self.context.user_data['impression']['category'])

        # Проверяем состояние
        self.assertEqual(result, IMPRESSION_TAGS)

    @patch('src.handlers.impression_handler.save_impression')
    @patch('src.handlers.impression_handler.create_tag')
    @patch('src.handlers.impression_handler.attach_tags_to_impression')
    @patch('src.handlers.impression_handler._get_db_connection')
    async def test_handle_impression_tags_with_tags(
        self, mock_db, mock_attach, mock_create_tag, mock_save
    ):
        """Тест: ввод тегов и сохранение."""
        from src.handlers.impression_handler import handle_impression_tags

        # Mock database connection
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn

        # Mock save_impression returns True
        mock_save.return_value = True

        # Mock create_tag returns tag IDs
        mock_create_tag.side_effect = [1, 2]  # два тега

        # Mock attach_tags returns True
        mock_attach.return_value = True

        self.update.message.text = "алкоголь, стресс"
        self.context.user_data['impression'] = {
            'impression_text': "Хочется выпить",
            'impression_date': "2025-10-24",
            'impression_time': "18:45:00",
            'category': "craving",
            'intensity': 7
        }

        result = await handle_impression_tags(self.update, self.context)

        # Проверяем что теги созданы
        self.assertEqual(mock_create_tag.call_count, 2)

        # Проверяем что впечатление сохранено
        mock_save.assert_called_once()

        # Проверяем что теги привязаны
        mock_attach.assert_called_once()

        # Проверяем что отправлено подтверждение
        self.update.effective_message.reply_text.assert_called()

        # Проверяем что диалог завершен
        self.assertEqual(result, ConversationHandler.END)

    @patch('src.handlers.impression_handler.save_impression')
    @patch('src.handlers.impression_handler._get_db_connection')
    async def test_handle_impression_tags_skip(self, mock_db, mock_save):
        """Тест: пропуск тегов и сохранение без тегов."""
        from src.handlers.impression_handler import handle_impression_tags

        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_save.return_value = True

        self.update.message.text = "/skip"
        self.context.user_data['impression'] = {
            'impression_text': "Тест",
            'impression_date': "2025-10-24",
            'impression_time': "12:00:00",
            'category': None,
            'intensity': None
        }

        result = await handle_impression_tags(self.update, self.context)

        # Проверяем что впечатление сохранено
        mock_save.assert_called_once()

        # Проверяем что диалог завершен
        self.assertEqual(result, ConversationHandler.END)

    @patch('src.handlers.impression_handler.end_conversation')
    async def test_cancel_impression(self, mock_end_conv):
        """Тест: отмена добавления впечатления через /cancel."""
        from src.handlers.impression_handler import cancel_impression

        self.context.user_data['impression'] = {'test': 'data'}

        result = await cancel_impression(self.update, self.context)

        # Проверяем что диалог завершен в менеджере
        mock_end_conv.assert_called_once()

        # Проверяем что данные удалены
        self.assertNotIn('impression', self.context.user_data)

        # Проверяем что отправлено сообщение об отмене
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("отмен", message_text.lower())

        # Проверяем что возвращен END
        self.assertEqual(result, ConversationHandler.END)

    def test_conversation_handler_exists(self):
        """Тест: ConversationHandler создан и экспортирован."""
        from src.handlers import impression_handler

        self.assertTrue(hasattr(impression_handler, 'impression_conversation_handler'))
        handler = impression_handler.impression_conversation_handler
        self.assertIsInstance(handler, ConversationHandler)

    def test_states_defined_in_config(self):
        """Тест: состояния определены в config.py."""
        from src.config import IMPRESSION_TEXT, IMPRESSION_INTENSITY, IMPRESSION_CATEGORY, IMPRESSION_TAGS

        # Проверяем что все состояния определены и являются числами
        self.assertIsInstance(IMPRESSION_TEXT, int)
        self.assertIsInstance(IMPRESSION_INTENSITY, int)
        self.assertIsInstance(IMPRESSION_CATEGORY, int)
        self.assertIsInstance(IMPRESSION_TAGS, int)

        # Проверяем что они уникальны
        states = [IMPRESSION_TEXT, IMPRESSION_INTENSITY, IMPRESSION_CATEGORY, IMPRESSION_TAGS]
        self.assertEqual(len(states), len(set(states)), "States must be unique")


if __name__ == '__main__':
    unittest.main()
