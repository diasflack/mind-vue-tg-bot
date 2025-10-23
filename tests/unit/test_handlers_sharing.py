"""
Tests for sharing handlers (send and view shared diary functionality).
"""

import unittest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.handlers.sharing import (
    send_diary_start, send_diary_user_id, custom_cancel_send,
    view_shared_start, process_shared_password, custom_cancel_view,
    create_date_range_keyboard
)
from telegram.ext import ConversationHandler


class TestSendDiaryHandlers(unittest.IsolatedAsyncioTestCase):
    """Test send diary functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.update = MagicMock()
        self.context = MagicMock()
        self.test_chat_id = 123456789

        self.update.effective_chat.id = self.test_chat_id
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()

        self.context.user_data = {}

    @patch('src.handlers.sharing.get_user_entries', return_value=[])
    @patch('src.handlers.sharing.end_conversation')
    @patch('src.handlers.sharing.register_conversation')
    @patch('src.handlers.sharing.end_all_conversations')
    async def test_send_diary_start_no_entries(self, mock_end_all, mock_register, mock_end, mock_get_entries):
        """Test /send command with no entries."""
        result = await send_diary_start(self.update, self.context)

        # Verify conversations were managed
        mock_end_all.assert_called_once_with(self.test_chat_id)

        # Verify get_user_entries was called
        mock_get_entries.assert_called_once_with(self.test_chat_id)

        # Verify "no entries" message was sent
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("нет записей", message_text.lower())

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)

    @patch('src.handlers.sharing.get_user_entries', return_value=[
        {'date': '2023-01-01', 'mood': '8'},
        {'date': '2023-01-02', 'mood': '9'}
    ])
    @patch('src.handlers.sharing.register_conversation')
    @patch('src.handlers.sharing.end_all_conversations')
    async def test_send_diary_start_with_entries(self, mock_end_all, mock_register, mock_get_entries):
        """Test /send command with existing entries."""
        result = await send_diary_start(self.update, self.context)

        # Verify conversations were managed
        mock_end_all.assert_called_once_with(self.test_chat_id)

        # Verify message asks for recipient ID
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("ID", message_text)

        # Verify returned SEND_DIARY_USER_ID state
        from src.handlers.sharing import SEND_DIARY_USER_ID
        self.assertEqual(result, SEND_DIARY_USER_ID)

    @patch('src.handlers.sharing.create_date_range_keyboard')
    @patch('src.handlers.sharing.register_conversation')
    async def test_send_diary_user_id_valid(self, mock_register, mock_keyboard):
        """Test entering valid recipient ID."""
        self.update.message.text = "987654321"
        mock_keyboard.return_value = MagicMock()

        result = await send_diary_user_id(self.update, self.context)

        # Verify recipient ID was saved
        self.assertEqual(self.context.user_data['recipient_id'], 987654321)

        # Verify keyboard was created
        mock_keyboard.assert_called_once()

        # Verify message asks for date range
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("период", message_text.lower())

        # Verify returned SEND_DIARY_START_DATE state
        from src.handlers.sharing import SEND_DIARY_START_DATE
        self.assertEqual(result, SEND_DIARY_START_DATE)

    @patch('src.handlers.sharing.register_conversation')
    async def test_send_diary_user_id_invalid(self, mock_register):
        """Test entering invalid recipient ID."""
        self.update.message.text = "not-a-number"

        result = await send_diary_user_id(self.update, self.context)

        # Verify recipient ID was NOT saved
        self.assertNotIn('recipient_id', self.context.user_data)

        # Verify error message was sent
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("корректный", message_text.lower())

        # Verify returned same state (retry)
        from src.handlers.sharing import SEND_DIARY_USER_ID
        self.assertEqual(result, SEND_DIARY_USER_ID)

    @patch('src.handlers.sharing.end_conversation')
    async def test_custom_cancel_send(self, mock_end):
        """Test canceling send diary process."""
        self.context.user_data = {
            'recipient_id': 987654321,
            'selected_date_range': 'date_range_all',
            'sharing_password': 'test123'
        }

        result = await custom_cancel_send(self.update, self.context)

        # Verify conversation was ended
        mock_end.assert_called_once()

        # Verify user data was cleared
        self.assertNotIn('recipient_id', self.context.user_data)
        self.assertNotIn('selected_date_range', self.context.user_data)
        self.assertNotIn('sharing_password', self.context.user_data)

        # Verify cancellation message was sent
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("отменена", message_text.lower())

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)


class TestViewSharedHandlers(unittest.IsolatedAsyncioTestCase):
    """Test view shared diary functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.update = MagicMock()
        self.context = MagicMock()
        self.test_chat_id = 123456789
        self.test_username = "test_user"
        self.test_first_name = "Test"

        self.update.effective_chat.id = self.test_chat_id
        self.update.effective_user.username = self.test_username
        self.update.effective_user.first_name = self.test_first_name
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()

        self.context.user_data = {}

    @patch('src.handlers.sharing.ensure_user_exists')
    @patch('src.handlers.sharing.register_conversation')
    @patch('src.handlers.sharing.end_all_conversations')
    async def test_view_shared_start(self, mock_end_all, mock_register, mock_ensure):
        """Test /view_shared command start."""
        result = await view_shared_start(self.update, self.context)

        # Verify conversations were managed
        mock_end_all.assert_called_once_with(self.test_chat_id)

        # Verify user existence was ensured
        mock_ensure.assert_called_once_with(
            self.test_chat_id,
            self.test_username,
            self.test_first_name
        )

        # Verify two messages were sent (file request + password request)
        self.assertEqual(self.update.message.reply_text.call_count, 2)

        # Verify first message asks for file
        first_call_args = self.update.message.reply_text.call_args_list[0]
        first_message_text = first_call_args[0][0]
        self.assertIn("файл", first_message_text.lower())

        # Verify second message asks for password
        second_call_args = self.update.message.reply_text.call_args_list[1]
        second_message_text = second_call_args[0][0]
        self.assertIn("пароль", second_message_text.lower())

        # Verify returned SHARE_PASSWORD_ENTRY state
        from src.handlers.sharing import SHARE_PASSWORD_ENTRY
        self.assertEqual(result, SHARE_PASSWORD_ENTRY)

    @patch('src.handlers.sharing.end_conversation')
    async def test_process_shared_password(self, mock_end):
        """Test entering password for shared diary."""
        self.update.message.text = "test_password_123"

        result = await process_shared_password(self.update, self.context)

        # Verify conversation was ended
        mock_end.assert_called_once()

        # Verify message was sent
        self.update.message.reply_text.assert_called_once()

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)

    @patch('src.handlers.sharing.end_conversation')
    async def test_custom_cancel_view(self, mock_end):
        """Test canceling view shared diary process."""
        result = await custom_cancel_view(self.update, self.context)

        # Verify conversation was ended
        mock_end.assert_called_once()

        # Verify cancellation message was sent
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("отменен", message_text.lower())

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)


class TestDateRangeKeyboard(unittest.TestCase):
    """Test date range keyboard creation."""

    def test_create_date_range_keyboard(self):
        """Test creating date range selection keyboard."""
        keyboard = create_date_range_keyboard()

        # Verify keyboard has InlineKeyboardMarkup structure
        self.assertIsNotNone(keyboard)
        self.assertTrue(hasattr(keyboard, 'inline_keyboard'))

        # Verify keyboard has 4 buttons (7 days, 30 days, 90 days, all time)
        self.assertEqual(len(keyboard.inline_keyboard), 4)

        # Verify each row has one button
        for row in keyboard.inline_keyboard:
            self.assertEqual(len(row), 1)

        # Verify button texts
        button_texts = [row[0].text for row in keyboard.inline_keyboard]
        self.assertIn("7 дней", button_texts[0])
        self.assertIn("30 дней", button_texts[1])
        self.assertIn("90 дней", button_texts[2])
        self.assertIn("Всё время", button_texts[3])

        # Verify callback data patterns
        button_data = [row[0].callback_data for row in keyboard.inline_keyboard]
        self.assertTrue(all(data.startswith("share_") for data in button_data))
        self.assertTrue("date_range_all" in button_data[3])


if __name__ == '__main__':
    unittest.main()
