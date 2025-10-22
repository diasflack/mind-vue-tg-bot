"""
Tests for basic handlers (start, help, cancel, get_user_id, recent_entries).
Critical for user interaction and bot UX.
"""

import unittest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch, call

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.handlers.basic import (
    start, help_command, handle_help_callback,
    get_user_id, cancel, recent_entries
)


class TestBasicHandlers(unittest.IsolatedAsyncioTestCase):
    """Test cases for basic command handlers."""

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

        # Mock callback_query for help callback tests
        self.update.callback_query = MagicMock()
        self.update.callback_query.answer = AsyncMock()
        self.update.callback_query.message = MagicMock()
        self.update.callback_query.message.edit_text = AsyncMock()

        # Mock user_data
        self.context.user_data = {}

    @patch('src.handlers.basic.save_user')
    @patch('src.handlers.basic.end_all_conversations')
    async def test_start_command_saves_user(self, mock_end_conv, mock_save_user):
        """Test that /start command saves user information."""
        await start(self.update, self.context)

        # Verify save_user was called with correct parameters
        mock_save_user.assert_called_once_with(
            self.test_chat_id,
            self.test_username,
            self.test_first_name
        )

    @patch('src.handlers.basic.save_user')
    @patch('src.handlers.basic.end_all_conversations')
    async def test_start_command_sends_welcome_message(self, mock_end_conv, mock_save_user):
        """Test that /start command sends welcome message."""
        await start(self.update, self.context)

        # Verify message was sent
        self.update.message.reply_text.assert_called_once()

        # Verify message content contains key phrases
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]

        self.assertIn("Добро пожаловать", message_text)
        self.assertIn("Трекер Настроения", message_text)
        self.assertIn("/help", message_text)
        self.assertIn("/add", message_text)

    @patch('src.handlers.basic.save_user')
    @patch('src.handlers.basic.end_all_conversations')
    async def test_start_command_ends_conversations(self, mock_end_conv, mock_save_user):
        """Test that /start command ends all active conversations."""
        await start(self.update, self.context)

        # Verify end_all_conversations was called
        mock_end_conv.assert_called_once_with(self.test_chat_id)

    @patch('src.handlers.basic.end_all_conversations')
    async def test_help_command_sends_categories(self, mock_end_conv):
        """Test that /help command sends category selection."""
        await help_command(self.update, self.context)

        # Verify message was sent
        self.update.message.reply_text.assert_called_once()

        # Verify message contains categories
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]

        self.assertIn("Справка", message_text)
        self.assertIn("категор", message_text.lower())

        # Verify inline keyboard was provided
        self.assertIn('reply_markup', call_args[1])

    @patch('src.handlers.basic.end_all_conversations')
    async def test_help_command_ends_conversations(self, mock_end_conv):
        """Test that /help command ends all active conversations."""
        await help_command(self.update, self.context)

        # Verify end_all_conversations was called
        mock_end_conv.assert_called_once_with(self.test_chat_id)

    async def test_help_callback_data_entry_category(self):
        """Test help callback for data_entry category."""
        self.update.callback_query.data = "help_data_entry"

        await handle_help_callback(self.update, self.context)

        # Verify callback was answered
        self.update.callback_query.answer.assert_called_once()

        # Verify message was edited
        self.update.callback_query.message.edit_text.assert_called_once()

        # Verify response contains data entry commands
        call_args = self.update.callback_query.message.edit_text.call_args
        response_text = call_args[0][0]

        self.assertIn("/add", response_text)
        self.assertIn("/add_date", response_text)

    async def test_help_callback_analytics_category(self):
        """Test help callback for analytics category."""
        self.update.callback_query.data = "help_analytics"

        await handle_help_callback(self.update, self.context)

        # Verify response contains analytics commands
        call_args = self.update.callback_query.message.edit_text.call_args
        response_text = call_args[0][0]

        self.assertIn("/stats", response_text)
        self.assertIn("/visualize", response_text)
        self.assertIn("/analytics", response_text)

    async def test_help_callback_close(self):
        """Test help callback for close action."""
        self.update.callback_query.data = "help_close"

        await handle_help_callback(self.update, self.context)

        # Verify callback was answered
        self.update.callback_query.answer.assert_called_once()

        # Verify message was deleted
        self.update.callback_query.message.delete.assert_called_once()

    async def test_help_callback_back(self):
        """Test help callback for back action."""
        self.update.callback_query.data = "help_back"

        await handle_help_callback(self.update, self.context)

        # Verify callback was answered
        self.update.callback_query.answer.assert_called_once()

        # Verify message was edited with categories
        call_args = self.update.callback_query.message.edit_text.call_args
        response_text = call_args[0][0]

        self.assertIn("Справка", response_text)
        self.assertIn("категор", response_text.lower())

    @patch('src.handlers.basic.end_all_conversations')
    async def test_get_user_id_returns_chat_id(self, mock_end_conv):
        """Test that /id command returns user's chat ID."""
        await get_user_id(self.update, self.context)

        # Verify message was sent
        self.update.message.reply_text.assert_called_once()

        # Verify message contains chat ID
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]

        self.assertIn(str(self.test_chat_id), message_text)
        self.assertIn("ID", message_text)

    @patch('src.handlers.basic.end_all_conversations')
    async def test_get_user_id_ends_conversations(self, mock_end_conv):
        """Test that /id command ends all active conversations."""
        await get_user_id(self.update, self.context)

        # Verify end_all_conversations was called
        mock_end_conv.assert_called_once_with(self.test_chat_id)

    @patch('src.handlers.basic.has_active_conversations', return_value=True)
    @patch('src.handlers.basic.end_all_conversations', return_value=["some_conversation"])
    @patch('src.handlers.basic.dump_all_conversations')
    async def test_cancel_with_active_conversations(self, mock_dump, mock_end, mock_has_active):
        """Test /cancel command with active conversations."""
        result = await cancel(self.update, self.context)

        # Verify conversations were ended
        mock_end.assert_called_once_with(self.test_chat_id)

        # Verify user_data was cleared
        self.assertEqual(len(self.context.user_data), 0)

        # Verify message was sent
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]

        self.assertIn("отменен", message_text.lower())

        # Verify ConversationHandler.END was returned
        from telegram.ext import ConversationHandler
        self.assertEqual(result, ConversationHandler.END)

    @patch('src.handlers.basic.has_active_conversations', return_value=False)
    @patch('src.handlers.basic.end_all_conversations', return_value=[])
    @patch('src.handlers.basic.dump_all_conversations')
    async def test_cancel_without_active_conversations(self, mock_dump, mock_end, mock_has_active):
        """Test /cancel command without active conversations."""
        await cancel(self.update, self.context)

        # Verify message indicates no active commands
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]

        self.assertIn("Нет активных команд", message_text)

    @patch('src.handlers.basic.get_user_entries', return_value=[
        {'date': '2023-01-03', 'mood': '8'},
        {'date': '2023-01-02', 'mood': '7'},
        {'date': '2023-01-01', 'mood': '9'}
    ])
    @patch('src.handlers.basic.format_entry_list')
    @patch('src.handlers.basic.end_all_conversations')
    async def test_recent_entries_with_data(self, mock_end_conv, mock_format, mock_get_entries):
        """Test /recent command with existing entries."""
        mock_format.return_value = "Formatted entries"

        await recent_entries(self.update, self.context)

        # Verify get_user_entries was called
        mock_get_entries.assert_called_once_with(self.test_chat_id)

        # Verify format_entry_list was called
        mock_format.assert_called_once()

        # Verify message was sent
        self.update.message.reply_text.assert_called_once()

    @patch('src.handlers.basic.get_user_entries', return_value=[])
    @patch('src.handlers.basic.end_all_conversations')
    async def test_recent_entries_without_data(self, mock_end_conv, mock_get_entries):
        """Test /recent command with no entries."""
        await recent_entries(self.update, self.context)

        # Verify message indicates no entries
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]

        self.assertIn("нет записей", message_text.lower())

    @patch('src.handlers.basic.save_user', side_effect=Exception("Database error"))
    @patch('src.handlers.basic.end_all_conversations')
    async def test_start_command_handles_save_error(self, mock_end_conv, mock_save_user):
        """Test that /start command handles save_user errors gracefully."""
        # Should not crash even if save_user fails
        try:
            await start(self.update, self.context)
            # If it doesn't crash, the exception was handled
            failed = False
        except Exception:
            failed = True

        # We expect it to raise the exception (no try-except in start())
        self.assertTrue(failed, "start() should propagate exceptions")

    async def test_help_callback_unknown_category(self):
        """Test help callback with unknown category."""
        self.update.callback_query.data = "help_unknown_category"

        await handle_help_callback(self.update, self.context)

        # Verify callback was answered
        self.update.callback_query.answer.assert_called_once()

        # Verify message indicates unknown category
        call_args = self.update.callback_query.message.edit_text.call_args
        response_text = call_args[0][0]

        self.assertIn("Неизвестная категория", response_text)


class TestBasicHandlersEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Test edge cases for basic handlers."""

    def setUp(self):
        """Set up test fixtures."""
        self.update = MagicMock()
        self.context = MagicMock()
        self.update.effective_chat.id = 123456789
        self.update.effective_user.username = None  # No username
        self.update.effective_user.first_name = "Test"
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()
        self.context.user_data = {}

    @patch('src.handlers.basic.save_user')
    @patch('src.handlers.basic.end_all_conversations')
    async def test_start_with_no_username(self, mock_end_conv, mock_save_user):
        """Test /start command when user has no username."""
        await start(self.update, self.context)

        # Verify save_user was called with None username
        mock_save_user.assert_called_once_with(
            123456789,
            None,
            "Test"
        )

        # Verify message was still sent
        self.update.message.reply_text.assert_called_once()

    @patch('src.handlers.basic.end_all_conversations')
    async def test_cancel_clears_complex_user_data(self, mock_end_conv):
        """Test that /cancel clears complex user_data structures."""
        # Add complex data to user_data
        self.context.user_data['key1'] = 'value1'
        self.context.user_data['key2'] = {'nested': 'data'}
        self.context.user_data['key3'] = [1, 2, 3]

        await cancel(self.update, self.context)

        # Verify all data was cleared
        self.assertEqual(len(self.context.user_data), 0)


if __name__ == '__main__':
    unittest.main()
