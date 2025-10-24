"""
Tests for entry handlers (add/add_date conversation flows).
Critical for main user interaction with the bot.
"""

import unittest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.handlers.entry import (
    start_entry, mood, sleep, comment, balance, mania,
    depression, anxiety, irritability, productivity, sociability,
    custom_cancel, start_entry_with_date, select_date, manual_date_input,
    custom_cancel_date
)
from src.config import (
    MOOD, SLEEP, COMMENT, BALANCE, MANIA, DEPRESSION,
    ANXIETY, IRRITABILITY, PRODUCTIVITY, SOCIABILITY,
    DATE_SELECTION, MANUAL_DATE_INPUT
)
from telegram.ext import ConversationHandler


class TestEntryHandlersBasic(unittest.IsolatedAsyncioTestCase):
    """Test basic entry conversation flow."""

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

    @patch('src.handlers.entry.get_user_entries', return_value=[])
    @patch('src.handlers.entry.save_user')
    @patch('src.handlers.entry.end_all_conversations')
    @patch('src.handlers.entry.register_conversation')
    @patch('src.handlers.entry.get_today', return_value='2023-01-15')
    async def test_start_entry_no_existing_entry(self, mock_get_today, mock_register, mock_end_all, mock_save_user, mock_get_entries):
        """Test starting entry process with no existing entry for today."""
        result = await start_entry(self.update, self.context)

        # Verify conversations were managed correctly
        mock_end_all.assert_called_once_with(self.test_chat_id)
        mock_register.assert_called_once_with(self.test_chat_id, "entry_handler", MOOD)

        # Verify user was saved
        mock_save_user.assert_called_once_with(
            self.test_chat_id,
            self.test_username,
            self.test_first_name
        )

        # Verify entry was initialized in user_data
        self.assertIn('entry', self.context.user_data)
        self.assertEqual(self.context.user_data['entry']['date'], '2023-01-15')

        # Verify message was sent
        self.update.effective_message.reply_text.assert_called_once()
        call_args = self.update.effective_message.reply_text.call_args
        message_text = call_args[0][0]

        self.assertIn("настроение", message_text.lower())
        self.assertNotIn("заменит существующую", message_text)

        # Verify returned state is MOOD
        self.assertEqual(result, MOOD)

    @patch('src.handlers.entry.get_user_entries', return_value=[{'date': '2023-01-15', 'mood': '8'}])
    @patch('src.handlers.entry.save_user')
    @patch('src.handlers.entry.end_all_conversations')
    @patch('src.handlers.entry.register_conversation')
    @patch('src.handlers.entry.get_today', return_value='2023-01-15')
    async def test_start_entry_with_existing_entry(self, mock_get_today, mock_register, mock_end_all, mock_save_user, mock_get_entries):
        """Test starting entry process when entry already exists for today."""
        result = await start_entry(self.update, self.context)

        # Verify message includes replacement warning
        call_args = self.update.effective_message.reply_text.call_args
        message_text = call_args[0][0]

        self.assertIn("заменит существующую", message_text)

        # Verify returned state is MOOD
        self.assertEqual(result, MOOD)


class TestEntryValidation(unittest.IsolatedAsyncioTestCase):
    """Test validation for entry fields."""

    def setUp(self):
        """Set up test fixtures."""
        self.update = MagicMock()
        self.context = MagicMock()
        self.test_chat_id = 123456789

        self.update.effective_chat.id = self.test_chat_id
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()
        self.context.user_data = {'entry': {}}

    @patch('src.handlers.entry.register_conversation')
    async def test_mood_valid_input(self, mock_register):
        """Test mood handler with valid input (1-10)."""
        self.update.message.text = "7"

        result = await mood(self.update, self.context)

        # Verify mood was saved
        self.assertEqual(self.context.user_data['entry']['mood'], "7")

        # Verify next question was asked
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("сна", message_text.lower())

        # Verify returned state is SLEEP
        self.assertEqual(result, SLEEP)

    @patch('src.handlers.entry.register_conversation')
    async def test_mood_invalid_input_not_number(self, mock_register):
        """Test mood handler with invalid input (not a number)."""
        self.update.message.text = "abc"

        result = await mood(self.update, self.context)

        # Verify mood was NOT saved
        self.assertNotIn('mood', self.context.user_data['entry'])

        # Verify error message was sent
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("введите число", message_text.lower())

        # Verify returned state is still MOOD
        self.assertEqual(result, MOOD)

    @patch('src.handlers.entry.register_conversation')
    async def test_mood_invalid_input_out_of_range_low(self, mock_register):
        """Test mood handler with input below valid range."""
        self.update.message.text = "0"

        result = await mood(self.update, self.context)

        # Verify mood was NOT saved
        self.assertNotIn('mood', self.context.user_data['entry'])

        # Verify error message was sent
        self.update.message.reply_text.assert_called_once()

        # Verify returned state is still MOOD
        self.assertEqual(result, MOOD)

    @patch('src.handlers.entry.register_conversation')
    async def test_mood_invalid_input_out_of_range_high(self, mock_register):
        """Test mood handler with input above valid range."""
        self.update.message.text = "11"

        result = await mood(self.update, self.context)

        # Verify mood was NOT saved
        self.assertNotIn('mood', self.context.user_data['entry'])

        # Verify returned state is still MOOD
        self.assertEqual(result, MOOD)

    @patch('src.handlers.entry.register_conversation')
    async def test_sleep_valid_input(self, mock_register):
        """Test sleep handler with valid input."""
        self.update.message.text = "8"
        self.context.user_data['entry']['mood'] = "7"

        result = await sleep(self.update, self.context)

        # Verify sleep was saved
        self.assertEqual(self.context.user_data['entry']['sleep'], "8")

        # Verify next question was asked
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("комментарий", message_text.lower())

        # Verify returned state is COMMENT
        self.assertEqual(result, COMMENT)

    @patch('src.handlers.entry.register_conversation')
    async def test_comment_any_text_accepted(self, mock_register):
        """Test comment handler accepts any text."""
        test_comments = [
            "Хороший день",
            "Bad day",
            "123",
            "Mixed feelings... 🎭",
            "",  # Empty comment should also be accepted
        ]

        for test_comment in test_comments:
            with self.subTest(comment=test_comment):
                # Reset user_data
                self.context.user_data = {'entry': {'mood': '7', 'sleep': '8'}}
                self.update.message.text = test_comment

                result = await comment(self.update, self.context)

                # Verify comment was saved
                self.assertEqual(self.context.user_data['entry']['comment'], test_comment)

                # Verify returned state is BALANCE
                self.assertEqual(result, BALANCE)

    @patch('src.handlers.entry.register_conversation')
    async def test_balance_valid_boundary_values(self, mock_register):
        """Test balance handler with boundary values (1 and 10)."""
        for value in ["1", "10"]:
            with self.subTest(value=value):
                self.context.user_data = {'entry': {}}
                self.update.message.text = value

                result = await balance(self.update, self.context)

                # Verify balance was saved
                self.assertEqual(self.context.user_data['entry']['balance'], value)

                # Verify returned state is MANIA
                self.assertEqual(result, MANIA)

    @patch('src.handlers.entry.register_conversation')
    async def test_numeric_fields_negative_number(self, mock_register):
        """Test numeric fields reject negative numbers."""
        self.context.user_data = {'entry': {}}
        self.update.message.text = "-5"

        result = await mood(self.update, self.context)

        # Verify mood was NOT saved
        self.assertNotIn('mood', self.context.user_data['entry'])

        # Verify returned state is still MOOD
        self.assertEqual(result, MOOD)

    @patch('src.handlers.entry.register_conversation')
    async def test_numeric_fields_float_number(self, mock_register):
        """Test numeric fields reject float numbers."""
        self.context.user_data = {'entry': {}}
        self.update.message.text = "7.5"

        result = await mood(self.update, self.context)

        # Verify mood was NOT saved
        self.assertNotIn('mood', self.context.user_data['entry'])

        # Verify returned state is still MOOD
        self.assertEqual(result, MOOD)


class TestEntryConversationFlow(unittest.IsolatedAsyncioTestCase):
    """Test complete conversation flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.update = MagicMock()
        self.context = MagicMock()
        self.test_chat_id = 123456789

        self.update.effective_chat.id = self.test_chat_id
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()

    @patch('src.handlers.entry.register_conversation')
    @patch('src.handlers.entry.format_entry_summary', return_value="Summary")
    @patch('src.handlers.entry.save_data', return_value=True)
    @patch('src.handlers.entry.end_conversation')
    async def test_full_entry_flow(self, mock_end_conv, mock_save_data, mock_format, mock_register):
        """Test complete entry flow from mood to sociability."""
        # Initialize entry
        self.context.user_data = {'entry': {'date': '2023-01-15'}}

        # Mood
        self.update.message.text = "7"
        result = await mood(self.update, self.context)
        self.assertEqual(result, SLEEP)

        # Sleep
        self.update.message.text = "8"
        result = await sleep(self.update, self.context)
        self.assertEqual(result, COMMENT)

        # Comment
        self.update.message.text = "Good day"
        result = await comment(self.update, self.context)
        self.assertEqual(result, BALANCE)

        # Balance
        self.update.message.text = "6"
        result = await balance(self.update, self.context)
        self.assertEqual(result, MANIA)

        # Mania
        self.update.message.text = "3"
        result = await mania(self.update, self.context)
        self.assertEqual(result, DEPRESSION)

        # Depression
        self.update.message.text = "2"
        result = await depression(self.update, self.context)
        self.assertEqual(result, ANXIETY)

        # Anxiety
        self.update.message.text = "4"
        result = await anxiety(self.update, self.context)
        self.assertEqual(result, IRRITABILITY)

        # Irritability
        self.update.message.text = "3"
        result = await irritability(self.update, self.context)
        self.assertEqual(result, PRODUCTIVITY)

        # Productivity
        self.update.message.text = "8"
        result = await productivity(self.update, self.context)
        self.assertEqual(result, SOCIABILITY)

        # Sociability (final step)
        self.update.message.text = "7"
        result = await sociability(self.update, self.context)

        # Verify data was saved
        mock_save_data.assert_called_once()
        saved_data = mock_save_data.call_args[0][0]

        self.assertEqual(saved_data['mood'], "7")
        self.assertEqual(saved_data['sleep'], "8")
        self.assertEqual(saved_data['comment'], "Good day")
        self.assertEqual(saved_data['balance'], "6")
        self.assertEqual(saved_data['mania'], "3")
        self.assertEqual(saved_data['depression'], "2")
        self.assertEqual(saved_data['anxiety'], "4")
        self.assertEqual(saved_data['irritability'], "3")
        self.assertEqual(saved_data['productivity'], "8")
        self.assertEqual(saved_data['sociability'], "7")

        # Verify conversation ended
        mock_end_conv.assert_called_once()

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)


class TestEntryCancel(unittest.IsolatedAsyncioTestCase):
    """Test cancel functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.update = MagicMock()
        self.context = MagicMock()
        self.test_chat_id = 123456789

        self.update.effective_chat.id = self.test_chat_id
        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()

    @patch('src.handlers.entry.end_conversation')
    async def test_cancel_clears_entry_data(self, mock_end_conv):
        """Test that cancel clears entry data from user_data."""
        self.context.user_data = {
            'entry': {
                'date': '2023-01-15',
                'mood': '7',
                'sleep': '8'
            }
        }

        result = await custom_cancel(self.update, self.context)

        # Verify entry was removed
        self.assertNotIn('entry', self.context.user_data)

        # Verify conversation ended
        mock_end_conv.assert_called_once_with(self.test_chat_id, "entry_handler")

        # Verify message was sent
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("отменено", message_text.lower())

        # Verify returned ConversationHandler.END
        self.assertEqual(result, ConversationHandler.END)


class TestEntryWithDate(unittest.IsolatedAsyncioTestCase):
    """Test entry with date selection."""

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

        # Mock callback_query for date selection
        self.update.callback_query = MagicMock()
        self.update.callback_query.answer = AsyncMock()
        self.update.callback_query.edit_message_text = AsyncMock()
        self.update.callback_query.message = MagicMock()
        self.update.callback_query.message.edit_text = AsyncMock()

        # Mock effective_chat.send_message for sending keyboards
        self.update.effective_chat = MagicMock()
        self.update.effective_chat.id = self.test_chat_id
        self.update.effective_chat.send_message = AsyncMock()

        self.context.user_data = {}

    @patch('src.handlers.entry.save_user')
    @patch('src.handlers.entry.end_all_conversations')
    @patch('src.handlers.entry.register_conversation')
    async def test_start_entry_with_date(self, mock_register, mock_end_all, mock_save_user):
        """Test starting entry with date selection."""
        result = await start_entry_with_date(self.update, self.context)

        # Verify conversations were managed correctly
        mock_end_all.assert_called_once_with(self.test_chat_id)
        mock_register.assert_called_once_with(self.test_chat_id, "entry_date_handler", DATE_SELECTION)

        # Verify entry was initialized without date
        self.assertIn('entry', self.context.user_data)
        self.assertNotIn('date', self.context.user_data['entry'])

        # Verify returned state is DATE_SELECTION
        self.assertEqual(result, DATE_SELECTION)

    @patch('src.handlers.entry.get_user_entries', return_value=[])
    @patch('src.handlers.entry.register_conversation')
    async def test_select_date_from_quick_options(self, mock_register, mock_get_entries):
        """Test selecting date from quick date options."""
        self.update.callback_query.data = "date_yesterday"
        self.context.user_data = {'entry': {}}

        result = await select_date(self.update, self.context)

        # Verify callback was answered
        self.update.callback_query.answer.assert_called_once()

        # Verify date was saved (yesterday's date will be saved)
        self.assertIn('date', self.context.user_data['entry'])

        # Verify message was edited
        self.update.callback_query.edit_message_text.assert_called_once()

        # Verify keyboard was sent
        self.update.effective_chat.send_message.assert_called_once()

        # Verify returned MOOD state
        from src.config import MOOD
        self.assertEqual(result, MOOD)

    @patch('src.handlers.entry.register_conversation')
    async def test_select_manual_date_input(self, mock_register):
        """Test selecting manual date input option."""
        self.update.callback_query.data = "date_manual"
        self.context.user_data = {'entry': {}}

        result = await select_date(self.update, self.context)

        # Verify callback was answered
        self.update.callback_query.answer.assert_called_once()

        # Verify returned MANUAL_DATE_INPUT state
        self.assertEqual(result, MANUAL_DATE_INPUT)

    @patch('src.utils.date_helpers.parse_user_date', return_value='2023-01-20')
    @patch('src.utils.date_helpers.is_valid_entry_date', return_value=(True, None))
    @patch('src.handlers.entry.get_user_entries', return_value=[])
    @patch('src.handlers.entry.register_conversation')
    async def test_manual_date_input_valid(self, mock_register, mock_get_entries, mock_is_valid, mock_parse):
        """Test manual date input with valid date."""
        self.update.message.text = "20.01.2023"
        self.context.user_data = {'entry': {}}

        result = await manual_date_input(self.update, self.context)

        # Verify date was parsed
        mock_parse.assert_called_once_with("20.01.2023")

        # Verify date was validated
        mock_is_valid.assert_called_once_with('2023-01-20')

        # Verify date was saved
        self.assertEqual(self.context.user_data['entry']['date'], '2023-01-20')

        # Verify next question was asked
        self.update.message.reply_text.assert_called()

    @patch('src.utils.date_helpers.parse_user_date', return_value=None)
    @patch('src.handlers.entry.register_conversation')
    async def test_manual_date_input_invalid(self, mock_register, mock_parse):
        """Test manual date input with invalid date."""
        self.update.message.text = "invalid-date"
        self.context.user_data = {'entry': {}}

        result = await manual_date_input(self.update, self.context)

        # Verify parse was called
        mock_parse.assert_called_once_with("invalid-date")

        # Verify error message was sent
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]
        self.assertIn("Неверный", message_text)

        # Verify returned state is still MANUAL_DATE_INPUT
        self.assertEqual(result, MANUAL_DATE_INPUT)


if __name__ == '__main__':
    unittest.main()
