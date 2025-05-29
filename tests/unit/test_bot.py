import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import src.config
from src.bot import create_application
from src.handlers.entry import start_entry, mood, sleep, comment, balance
from src.utils.conversation_manager import (
    register_conversation, end_conversation, 
    has_active_conversations, get_active_conversations
)

class TestBot(unittest.TestCase):
    """Test cases for core bot functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()

        # Mock the DATA_FOLDER config
        self.original_data_folder = src.config.DATA_FOLDER
        src.config.DATA_FOLDER = self.test_dir

        # Set a test token
        src.config.TELEGRAM_BOT_TOKEN = "test_token"

        # Mock the salt values
        src.config.SECRET_SALT = b"test_secret_salt"
        src.config.SYSTEM_SALT = b"test_system_salt"

        # Set up conversation manager
        # Clear any active conversations
        from src.utils.conversation_manager import active_conversations
        active_conversations.clear()

    def tearDown(self):
        """Clean up test environment."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)
        
        # Restore the original DATA_FOLDER
        src.config.DATA_FOLDER = self.original_data_folder

    def test_application_creation(self):
        """Test that the application can be created."""
        
        # Patch the config to use our test token
        with patch('src.config.TELEGRAM_BOT_TOKEN', 'test_token'):
            with patch('src.bot.TELEGRAM_BOT_TOKEN', 'test_token'):
                with patch('dotenv.load_dotenv'):
                    with patch('telegram.ext.Application.builder') as mock_builder:
                        # Create a more sophisticated mock that handles the builder pattern
                        mock_app = MagicMock()
                        
                        # Create a chain of mock methods that return themselves
                        mock_chain = MagicMock()
                        mock_chain.token.return_value = mock_chain
                        mock_chain.concurrent_updates.return_value = mock_chain
                        mock_chain.connect_timeout.return_value = mock_chain
                        mock_chain.read_timeout.return_value = mock_chain
                        mock_chain.write_timeout.return_value = mock_chain
                        mock_chain.build.return_value = mock_app
                        
                        mock_builder.return_value = mock_chain

                        app = create_application()

                        # Check that the app was returned (it may not be exactly the mock due to post-processing)
                        self.assertIsNotNone(app)

                        # Check that the token method was called with our test token
                        mock_chain.token.assert_called_once_with("test_token")


    def test_conversation_manager(self):
        """Test the conversation manager functionality."""
        chat_id = 123456789
        handler_name = "test_handler"
        state = 1
        
        # Register a conversation
        register_conversation(chat_id, handler_name, state)
        
        # Check if the conversation is active
        self.assertTrue(has_active_conversations(chat_id))
        
        # Get active conversations
        active = get_active_conversations(chat_id)
        self.assertEqual(active, {handler_name: state})
        
        # End the conversation
        end_conversation(chat_id, handler_name)
        
        # Check that the conversation is no longer active
        self.assertFalse(has_active_conversations(chat_id))

    async def test_entry_conversation_flow(self):
        """Test the entry conversation flow."""
        # Mock objects
        update = MagicMock()
        context = MagicMock()
        
        # Mock the chat_id
        chat_id = 123456789
        update.effective_chat.id = chat_id
        update.effective_user.username = "test_user"
        update.effective_user.first_name = "Test"
        
        # Mock message
        update.message = AsyncMock()
        
        # Set up context.user_data
        context.user_data = {}
        
        # Start entry conversation
        with patch('src.handlers.entry.get_today', return_value="2023-05-15"):
            with patch('src.handlers.entry.get_user_entries', return_value=[]):
                # Call start_entry
                result = await start_entry(update, context)
                
                # Check that the function returns the MOOD state
                self.assertEqual(result, src.config.MOOD)
                
                # Check that the user_data contains the entry with date
                self.assertIn('entry', context.user_data)
                self.assertEqual(context.user_data['entry']['date'], "2023-05-15")
                
                # Check that a reply was sent
                update.message.reply_text.assert_called_once()
        
        # Mock user's mood input
        update.message.text = "8"
        
        # Call mood handler
        result = await mood(update, context)
        
        # Check that the function returns the SLEEP state
        self.assertEqual(result, src.config.SLEEP)
        
        # Check that the user_data contains the mood value
        self.assertEqual(context.user_data['entry']['mood'], "8")
        
        # Mock user's sleep input
        update.message.text = "7"
        
        # Call sleep handler
        result = await sleep(update, context)
        
        # Check that the function returns the COMMENT state
        self.assertEqual(result, src.config.COMMENT)
        
        # Check that the user_data contains the sleep value
        self.assertEqual(context.user_data['entry']['sleep'], "7")
        
        # Mock user's comment
        update.message.text = "Test comment"
        
        # Call comment handler
        result = await comment(update, context)
        
        # Check that the function returns the BALANCE state
        self.assertEqual(result, src.config.BALANCE)
        
        # Check that the user_data contains the comment
        self.assertEqual(context.user_data['entry']['comment'], "Test comment")

    def test_conversation_state_transitions(self):
        """Test conversation state transitions in the conversation manager."""
        chat_id = 123456789
        handler1 = "handler1"
        handler2 = "handler2"
        
        # Register two conversations for the same user
        register_conversation(chat_id, handler1, 1)
        register_conversation(chat_id, handler2, 2)
        
        # Check that both conversations are active
        active = get_active_conversations(chat_id)
        self.assertEqual(active, {handler1: 1, handler2: 2})
        
        # End one conversation
        end_conversation(chat_id, handler1)
        
        # Check that only the second conversation is active
        active = get_active_conversations(chat_id)
        self.assertEqual(active, {handler2: 2})
        
        # Change the state of the active conversation
        register_conversation(chat_id, handler2, 3)
        
        # Check that the state was updated
        active = get_active_conversations(chat_id)
        self.assertEqual(active, {handler2: 3})

if __name__ == '__main__':
    unittest.main()
