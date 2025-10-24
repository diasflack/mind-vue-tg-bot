"""
Tests for stats and delete handlers (critical user functions).
"""

import unittest
import os
import sys
import io
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.handlers.stats import stats, download_diary, prepare_csv_from_entries
from src.handlers.delete import delete_command, delete_choice, delete_by_date
from telegram.ext import ConversationHandler


class TestStatsHandlers(unittest.IsolatedAsyncioTestCase):
    """Test stats and download functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.update = MagicMock()
        self.context = MagicMock()
        self.test_chat_id = 123456789

        self.update.effective_chat.id = self.test_chat_id
        self.update.effective_message = MagicMock()
        self.update.effective_message.reply_text = AsyncMock()

        # Mock status message
        self.mock_status_msg = MagicMock()
        self.mock_status_msg.delete = AsyncMock()
        self.update.effective_message.reply_text.return_value = self.mock_status_msg

    @patch('src.handlers.stats.get_user_entries', return_value=[])
    async def test_stats_no_entries(self, mock_get_entries):
        """Test /stats command with no entries."""
        result = await stats(self.update, self.context)

        # Verify get_user_entries was called
        mock_get_entries.assert_called_once_with(self.test_chat_id)

        # Verify status message was deleted
        self.mock_status_msg.delete.assert_called_once()

        # Verify "no entries" message was sent
        self.assertEqual(self.update.effective_message.reply_text.call_count, 2)
        second_call_args = self.update.effective_message.reply_text.call_args_list[1]
        message_text = second_call_args[0][0]
        self.assertIn("нет записей", message_text.lower())

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)

    @patch('src.handlers.stats.format_stats_summary', return_value="Stats summary")
    @patch('src.handlers.stats.get_user_entries', return_value=[
        {'date': '2023-01-01', 'mood': '8', 'sleep': '7'},
        {'date': '2023-01-02', 'mood': '9', 'sleep': '8'}
    ])
    async def test_stats_with_entries(self, mock_get_entries, mock_format):
        """Test /stats command with existing entries."""
        result = await stats(self.update, self.context)

        # Verify get_user_entries was called
        mock_get_entries.assert_called_once_with(self.test_chat_id)

        # Verify format_stats_summary was called with DataFrame
        mock_format.assert_called_once()
        call_args = mock_format.call_args[0][0]
        self.assertIsInstance(call_args, pd.DataFrame)
        self.assertEqual(len(call_args), 2)

        # Verify status message was deleted
        self.mock_status_msg.delete.assert_called_once()

        # Verify stats were sent
        second_call_args = self.update.effective_message.reply_text.call_args_list[1]
        message_text = second_call_args[0][0]
        self.assertEqual(message_text, "Stats summary")

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)

    @patch('src.handlers.stats.get_user_entries', return_value=[])
    async def test_download_no_entries(self, mock_get_entries):
        """Test /download command with no entries."""
        self.update.message = MagicMock()

        # Mock status message that gets deleted
        mock_status_msg = MagicMock()
        mock_status_msg.delete = AsyncMock()

        # reply_text will be called twice: status message, then "no entries"
        self.update.message.reply_text = AsyncMock(return_value=mock_status_msg)

        result = await download_diary(self.update, self.context)

        # Verify get_user_entries was called
        mock_get_entries.assert_called_once_with(self.test_chat_id)

        # Verify status message was deleted
        mock_status_msg.delete.assert_called_once()

        # Verify reply_text was called twice (status + no entries message)
        self.assertEqual(self.update.message.reply_text.call_count, 2)

        # Check the second call (no entries message)
        second_call_args = self.update.message.reply_text.call_args_list[1]
        message_text = second_call_args[0][0]
        self.assertIn("нет записей", message_text.lower())

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)

    @patch('src.handlers.stats.get_user_entries', return_value=[
        {'date': '2023-01-01', 'mood': '8', 'sleep': '7', 'comment': 'Good'},
        {'date': '2023-01-02', 'mood': '9', 'sleep': '8', 'comment': 'Great'}
    ])
    async def test_download_with_entries(self, mock_get_entries):
        """Test /download command with existing entries."""
        self.update.message = MagicMock()

        # Mock status message that gets deleted
        mock_status_msg = MagicMock()
        mock_status_msg.delete = AsyncMock()

        # reply_text will be called twice: status message, then success message
        self.update.message.reply_text = AsyncMock(return_value=mock_status_msg)

        # Mock send_document on context.bot
        self.context.bot = MagicMock()
        self.context.bot.send_document = AsyncMock()

        result = await download_diary(self.update, self.context)

        # Verify get_user_entries was called
        mock_get_entries.assert_called_once_with(self.test_chat_id)

        # Verify status message was deleted
        mock_status_msg.delete.assert_called_once()

        # Verify document was sent
        self.context.bot.send_document.assert_called_once()
        send_doc_args = self.context.bot.send_document.call_args
        self.assertEqual(send_doc_args[1]['filename'], 'my_mood_diary.csv')

        # Verify success message was sent (second reply_text call)
        self.assertEqual(self.update.message.reply_text.call_count, 2)
        second_call_args = self.update.message.reply_text.call_args_list[1]
        message_text = second_call_args[0][0]
        self.assertIn("отправлен", message_text.lower())

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)

    def test_prepare_csv_from_entries(self):
        """Test CSV preparation from entries."""
        entries = [
            {'date': '2023-01-01', 'mood': '8', 'sleep': '7'},
            {'date': '2023-01-02', 'mood': '9', 'sleep': '8'}
        ]

        csv_bytes = prepare_csv_from_entries(entries)

        # Verify result is BytesIO
        self.assertIsInstance(csv_bytes, io.BytesIO)

        # Verify CSV content
        csv_content = csv_bytes.getvalue().decode('utf-8')
        self.assertIn('date', csv_content)
        self.assertIn('mood', csv_content)
        self.assertIn('2023-01-01', csv_content)
        self.assertIn('2023-01-02', csv_content)

    def test_prepare_csv_empty_entries(self):
        """Test CSV preparation with empty entries."""
        entries = []

        csv_bytes = prepare_csv_from_entries(entries)

        # Should still return BytesIO
        self.assertIsInstance(csv_bytes, io.BytesIO)


class TestDeleteHandlers(unittest.IsolatedAsyncioTestCase):
    """Test delete functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.update = MagicMock()
        self.context = MagicMock()
        self.test_chat_id = 123456789

        self.update.effective_chat.id = self.test_chat_id
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()

        # Mock callback_query
        self.update.callback_query = MagicMock()
        self.update.callback_query.answer = AsyncMock()
        self.update.callback_query.message = MagicMock()
        self.update.callback_query.message.edit_text = AsyncMock()

        self.context.user_data = {}

    async def test_delete_command_start(self):
        """Test /delete command starts conversation."""
        result = await delete_command(self.update, self.context)

        # Verify message was sent with options
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("удален", message_text.lower())  # matches "удаления"

        # Verify keyboard with options was provided
        keyboard_arg = call_args[1]['reply_markup']
        self.assertIsNotNone(keyboard_arg)

        # Verify returned DELETE_ENTRY_CONFIRM state
        from src.config import DELETE_ENTRY_CONFIRM
        self.assertEqual(result, DELETE_ENTRY_CONFIRM)

    @patch('src.handlers.delete.delete_all_entries', return_value=True)
    async def test_delete_choice_confirm_all(self, mock_delete_all):
        """Test confirming delete all entries."""
        self.update.callback_query.data = "confirm_delete_all"
        self.update.callback_query.message.chat_id = self.test_chat_id
        self.update.callback_query.message.reply_text = AsyncMock()

        result = await delete_choice(self.update, self.context)

        # Verify delete_all_entries was called
        mock_delete_all.assert_called_once_with(self.test_chat_id)

        # Verify callback was answered
        self.update.callback_query.answer.assert_called_once()

        # Verify success message was sent
        call_args_list = self.update.callback_query.message.edit_text.call_args_list
        message_text = call_args_list[0][0][0]
        self.assertIn("удалены", message_text.lower())

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)

    async def test_delete_choice_cancel(self):
        """Test canceling delete."""
        self.update.callback_query.data = "delete_cancel"
        self.update.callback_query.message.reply_text = AsyncMock()

        result = await delete_choice(self.update, self.context)

        # Verify callback was answered
        self.update.callback_query.answer.assert_called_once()

        # Verify cancellation message was sent
        call_args = self.update.callback_query.message.edit_text.call_args
        message_text = call_args[0][0]
        self.assertIn("отменено", message_text.lower())

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)

    async def test_delete_choice_by_date(self):
        """Test selecting delete by date option."""
        self.update.callback_query.data = "delete_by_date"

        result = await delete_choice(self.update, self.context)

        # Verify callback was answered
        self.update.callback_query.answer.assert_called_once()

        # Verify message asks for date
        call_args = self.update.callback_query.message.edit_text.call_args
        message_text = call_args[0][0]
        self.assertIn("дату", message_text.lower())

        # Verify returned next state
        self.assertIsNotNone(result)

    async def test_delete_choice_all_asks_confirmation(self):
        """Test that deleting all asks for confirmation."""
        self.update.callback_query.data = "delete_all"

        result = await delete_choice(self.update, self.context)

        # Verify callback was answered
        self.update.callback_query.answer.assert_called_once()

        # Verify confirmation message was sent
        call_args = self.update.callback_query.message.edit_text.call_args
        message_text = call_args[0][0]
        self.assertIn("уверены", message_text.lower())
        self.assertIn("ВСЕ", message_text)

        # Verify returned same state for confirmation
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
