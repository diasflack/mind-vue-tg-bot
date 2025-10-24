"""
Unit tests for notification system.
Tests for save_user() function and notification handlers.
"""

import unittest
import os
import sys
import tempfile
import shutil
import sqlite3
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data.storage import (
    save_user, get_users_for_notification,
    get_all_users_with_notifications, _get_db_connection
)
import src.config
import src.data.storage


class TestSaveUserFunction(unittest.TestCase):
    """Test cases for the save_user() function - critical bug fix verification."""

    def setUp(self):
        """Set up test environment with a temporary database."""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()

        # Mock the DATA_FOLDER and DB_FILE config
        self.original_data_folder = src.config.DATA_FOLDER
        src.config.DATA_FOLDER = self.test_dir

        # Reset the database connection
        src.data.storage._db_connection = None

        # Test user data
        self.test_chat_id = 123456789
        self.test_username = "testuser"
        self.test_first_name = "Test User"

    def tearDown(self):
        """Clean up the test environment."""
        # Close the database connection
        try:
            if src.data.storage._db_connection:
                src.data.storage._db_connection.close()
                src.data.storage._db_connection = None
        except:
            pass

        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

        # Restore the original DATA_FOLDER
        src.config.DATA_FOLDER = self.original_data_folder

    def _get_user_from_db(self, chat_id):
        """Helper method to get user data directly from database."""
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT chat_id, username, first_name, notification_time FROM users WHERE chat_id = ?",
            (chat_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                'chat_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'notification_time': row[3]
            }
        return None

    def test_save_user_creates_new_user(self):
        """Test that save_user creates a new user with notification_time."""
        # Save a new user with notification time
        result = save_user(
            self.test_chat_id,
            self.test_username,
            self.test_first_name,
            notification_time="10:00"
        )

        self.assertTrue(result)

        # Verify in database
        user = self._get_user_from_db(self.test_chat_id)
        self.assertIsNotNone(user)
        self.assertEqual(user['chat_id'], self.test_chat_id)
        self.assertEqual(user['username'], self.test_username)
        self.assertEqual(user['first_name'], self.test_first_name)
        self.assertEqual(user['notification_time'], "10:00")

    def test_save_user_updates_existing_user(self):
        """Test that save_user updates an existing user."""
        # Create initial user
        save_user(self.test_chat_id, "oldname", "Old Name", notification_time="09:00")

        # Update user
        result = save_user(
            self.test_chat_id,
            self.test_username,
            self.test_first_name,
            notification_time="11:00"
        )

        self.assertTrue(result)

        # Verify update
        user = self._get_user_from_db(self.test_chat_id)
        self.assertEqual(user['username'], self.test_username)
        self.assertEqual(user['first_name'], self.test_first_name)
        self.assertEqual(user['notification_time'], "11:00")

    def test_save_user_with_none_notification_time_CRITICAL(self):
        """
        CRITICAL BUG FIX TEST:
        Test that save_user correctly sets notification_time to NULL when passed None.

        This test verifies the fix for the critical bug where notification_time=None
        was not updating the database, making it impossible to disable notifications.
        """
        # Step 1: Create user with notification enabled
        save_user(self.test_chat_id, self.test_username, self.test_first_name, notification_time="10:00")
        user = self._get_user_from_db(self.test_chat_id)
        self.assertEqual(user['notification_time'], "10:00")

        # Step 2: Disable notifications by setting notification_time=None
        result = save_user(
            self.test_chat_id,
            self.test_username,
            self.test_first_name,
            notification_time=None
        )

        self.assertTrue(result)

        # Step 3: Verify that notification_time is now NULL in database
        user = self._get_user_from_db(self.test_chat_id)
        self.assertIsNone(user['notification_time'],
            "CRITICAL: notification_time should be NULL after disabling, but it's not! "
            "This means the bug fix didn't work."
        )

    def test_save_user_disable_and_reenable_notifications(self):
        """Test the complete cycle: enable -> disable -> enable notifications."""
        # Enable notifications
        save_user(self.test_chat_id, self.test_username, self.test_first_name, notification_time="10:00")
        user = self._get_user_from_db(self.test_chat_id)
        self.assertEqual(user['notification_time'], "10:00")

        # Disable notifications
        save_user(self.test_chat_id, self.test_username, self.test_first_name, notification_time=None)
        user = self._get_user_from_db(self.test_chat_id)
        self.assertIsNone(user['notification_time'])

        # Re-enable with different time
        save_user(self.test_chat_id, self.test_username, self.test_first_name, notification_time="14:30")
        user = self._get_user_from_db(self.test_chat_id)
        self.assertEqual(user['notification_time'], "14:30")

    def test_save_user_with_none_for_new_user(self):
        """Test that a new user can be created with notification_time=None."""
        result = save_user(
            self.test_chat_id,
            self.test_username,
            self.test_first_name,
            notification_time=None
        )

        self.assertTrue(result)

        user = self._get_user_from_db(self.test_chat_id)
        self.assertIsNotNone(user)
        self.assertIsNone(user['notification_time'])


class TestNotificationQueries(unittest.TestCase):
    """Test cases for notification-related database queries."""

    def setUp(self):
        """Set up test environment with a temporary database."""
        self.test_dir = tempfile.mkdtemp()
        self.original_data_folder = src.config.DATA_FOLDER
        src.config.DATA_FOLDER = self.test_dir
        src.data.storage._db_connection = None

    def tearDown(self):
        """Clean up the test environment."""
        try:
            if src.data.storage._db_connection:
                src.data.storage._db_connection.close()
                src.data.storage._db_connection = None
        except:
            pass
        shutil.rmtree(self.test_dir)
        src.config.DATA_FOLDER = self.original_data_folder

    def test_get_users_for_notification_at_specific_time(self):
        """Test getting users who should receive notifications at a specific time."""
        # Create users with different notification times
        save_user(111, "user1", "User 1", notification_time="10:00")
        save_user(222, "user2", "User 2", notification_time="10:00")
        save_user(333, "user3", "User 3", notification_time="14:30")
        save_user(444, "user4", "User 4", notification_time=None)

        # Get users for 10:00
        users = get_users_for_notification("10:00")

        # Should return exactly 2 users
        self.assertEqual(len(users), 2)
        chat_ids = [u['chat_id'] for u in users]
        self.assertIn(111, chat_ids)
        self.assertIn(222, chat_ids)
        self.assertNotIn(333, chat_ids)
        self.assertNotIn(444, chat_ids)

    def test_get_users_for_notification_no_matches(self):
        """Test getting users when no one has notifications at that time."""
        save_user(111, "user1", "User 1", notification_time="10:00")
        save_user(222, "user2", "User 2", notification_time=None)

        # Get users for 14:00 (no one scheduled)
        users = get_users_for_notification("14:00")

        self.assertEqual(len(users), 0)

    def test_get_all_users_with_notifications(self):
        """Test getting all users with active notifications."""
        save_user(111, "user1", "User 1", notification_time="10:00")
        save_user(222, "user2", "User 2", notification_time="14:30")
        save_user(333, "user3", "User 3", notification_time=None)

        users = get_all_users_with_notifications()

        # Should return only users with notification_time set
        self.assertEqual(len(users), 2)
        chat_ids = [u['chat_id'] for u in users]
        self.assertIn(111, chat_ids)
        self.assertIn(222, chat_ids)
        self.assertNotIn(333, chat_ids)

    def test_get_all_users_with_notifications_after_disable(self):
        """Test that disabled users are excluded from notification list."""
        # Enable notifications for users
        save_user(111, "user1", "User 1", notification_time="10:00")
        save_user(222, "user2", "User 2", notification_time="14:30")

        # Verify both are in the list
        users = get_all_users_with_notifications()
        self.assertEqual(len(users), 2)

        # Disable notifications for user 111
        save_user(111, "user1", "User 1", notification_time=None)

        # Verify only user 222 is in the list now
        users = get_all_users_with_notifications()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['chat_id'], 222)


class TestNotificationHandlers(unittest.TestCase):
    """Test cases for notification handler functions."""

    def setUp(self):
        """Set up test environment for handler tests."""
        self.test_dir = tempfile.mkdtemp()
        self.original_data_folder = src.config.DATA_FOLDER
        src.config.DATA_FOLDER = self.test_dir
        src.data.storage._db_connection = None

    def tearDown(self):
        """Clean up the test environment."""
        try:
            if src.data.storage._db_connection:
                src.data.storage._db_connection.close()
                src.data.storage._db_connection = None
        except:
            pass
        shutil.rmtree(self.test_dir)
        src.config.DATA_FOLDER = self.original_data_folder

    @patch('src.handlers.notifications.save_user')
    @patch('src.handlers.notifications.MAIN_KEYBOARD', MagicMock())
    def test_cancel_notify_command(self, mock_save_user):
        """Test the /cancel_notify command handler."""
        from src.handlers.notifications import cancel_notify_command

        # Create mock update and context
        mock_update = MagicMock()
        mock_update.effective_chat.id = 123
        mock_update.effective_user.username = "testuser"
        mock_update.effective_user.first_name = "Test"
        mock_update.effective_message.reply_text = AsyncMock()

        mock_context = MagicMock()

        # Run the command
        import asyncio
        asyncio.run(cancel_notify_command(mock_update, mock_context))

        # Verify save_user was called with notification_time=None
        mock_save_user.assert_called_once_with(
            123, "testuser", "Test", notification_time=None
        )

    @patch('src.handlers.notifications.save_user')
    @patch('src.handlers.notifications.MAIN_KEYBOARD', MagicMock())
    def test_notification_callback_disable(self, mock_save_user):
        """Test the notification_callback handler for disable action."""
        from src.handlers.notifications import notification_callback

        # Create mock update with callback_query
        mock_update = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.message.chat_id = 123
        mock_update.callback_query.data = "notify_disable"
        mock_update.effective_user.username = "testuser"
        mock_update.effective_user.first_name = "Test"

        mock_context_obj = MagicMock()
        mock_context_obj.bot.send_message = AsyncMock()

        # Run the handler
        import asyncio
        asyncio.run(notification_callback(mock_update, mock_context_obj))

        # Verify callback was answered
        mock_update.callback_query.answer.assert_called_once()

        # Verify save_user was called with notification_time=None
        mock_save_user.assert_called_once_with(
            123, "testuser", "Test", notification_time=None
        )


class TestDatabaseIndexes(unittest.TestCase):
    """Test that required database indexes exist for performance."""

    def setUp(self):
        """Set up test environment with a temporary database."""
        self.test_dir = tempfile.mkdtemp()
        self.original_data_folder = src.config.DATA_FOLDER
        src.config.DATA_FOLDER = self.test_dir
        src.data.storage._db_connection = None

    def tearDown(self):
        """Clean up the test environment."""
        try:
            if src.data.storage._db_connection:
                src.data.storage._db_connection.close()
                src.data.storage._db_connection = None
        except:
            pass
        shutil.rmtree(self.test_dir)
        src.config.DATA_FOLDER = self.original_data_folder

    def test_notification_time_index_exists(self):
        """Test that the performance index on notification_time exists."""
        conn = _get_db_connection()
        cursor = conn.cursor()

        # Query for indexes on users table
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index'
            AND tbl_name='users'
            AND name='idx_users_notification_time'
        """)

        result = cursor.fetchone()
        self.assertIsNotNone(result,
            "Index idx_users_notification_time should exist for performance optimization"
        )


if __name__ == '__main__':
    unittest.main()
