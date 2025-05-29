import unittest
import os
import sys
import tempfile
import shutil
import pandas as pd
from unittest.mock import patch, MagicMock

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.storage import (
    save_data, get_user_entries, delete_entry_by_date, 
    delete_all_entries, has_entry_for_date
)
import src.config

class TestStorage(unittest.TestCase):
    """Test cases for storage functionality."""

    def setUp(self):
        """Set up test environment with a temporary directory and mock encryption."""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        
        # Mock the DATA_FOLDER config
        self.original_data_folder = src.config.DATA_FOLDER
        src.config.DATA_FOLDER = self.test_dir
        
        # Test user ID
        self.test_chat_id = 123456789
        
        # Sample entry data
        self.sample_entry = {
            "date": "2023-01-01",
            "mood": "8",
            "sleep": "7",
            "comment": "Test comment",
            "balance": "6",
            "mania": "3",
            "depression": "2",
            "anxiety": "4",
            "irritability": "3",
            "productivity": "8",
            "sociability": "7"
        }

        # Create a more sophisticated mock for encryption/decryption
        self.entries_cache = {}  # To store encrypted entries

        self.patcher1 = patch('src.data.storage.encrypt_data')
        self.mock_encrypt = self.patcher1.start()
        self.mock_encrypt.side_effect = lambda data, chat_id: self._mock_encrypt(data, chat_id)

        self.patcher2 = patch('src.data.storage.decrypt_data')
        self.mock_decrypt = self.patcher2.start()
        self.mock_decrypt.side_effect = lambda encrypted_data, chat_id: self._mock_decrypt(encrypted_data, chat_id)
        
        # Clean up any existing data for this test chat_id
        try:
            delete_all_entries(self.test_chat_id)
        except:
            pass  # Ignore errors during cleanup


    def _mock_encrypt(self, data, chat_id):
        """Better encryption simulation that maintains uniqueness."""
        key = f"{chat_id}_{data['date']}"
        encrypted = f"encrypted_{hash(str(data))}"
        self.entries_cache[encrypted] = data.copy()
        return encrypted

    def tearDown(self):
        """Clean up the test environment."""
        # Clean up any test data first
        try:
            delete_all_entries(self.test_chat_id)
        except:
            pass  # Ignore errors during cleanup
            
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)
        
        # Restore the original DATA_FOLDER
        src.config.DATA_FOLDER = self.original_data_folder
        
        # Stop the patchers
        self.patcher1.stop()
        self.patcher2.stop()


    def tearDown(self):
        """Clean up the test environment."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)
        
        # Restore the original DATA_FOLDER
        src.config.DATA_FOLDER = self.original_data_folder
        
        # Stop the patchers
        self.patcher1.stop()
        self.patcher2.stop()

    def test_save_and_retrieve_data(self):
        """Test that data can be saved and then retrieved."""
        # Save the sample entry
        result = save_data(self.sample_entry, self.test_chat_id)
        self.assertTrue(result)
        
        # Get the entries
        entries = get_user_entries(self.test_chat_id)
        
        # Should have one entry
        self.assertEqual(len(entries), 1)
        
        # Entry date should match
        self.assertEqual(entries[0]["date"], self.sample_entry["date"])

    def test_has_entry_for_date(self):
        """Test checking if an entry exists for a specific date."""
        # Save the sample entry
        save_data(self.sample_entry, self.test_chat_id)
        
        # Check if entry exists for the saved date
        has_entry = has_entry_for_date(self.test_chat_id, self.sample_entry["date"])
        self.assertTrue(has_entry)
        
        # Check if entry exists for a different date
        has_entry = has_entry_for_date(self.test_chat_id, "2023-02-01")
        self.assertFalse(has_entry)

    def test_delete_entry_by_date(self):
        """Test deleting an entry for a specific date."""
        # Save the sample entry
        save_data(self.sample_entry, self.test_chat_id)
        
        # Save another entry for a different date
        other_entry = self.sample_entry.copy()
        other_entry["date"] = "2023-02-01"
        save_data(other_entry, self.test_chat_id)
        
        # Delete the first entry
        result = delete_entry_by_date(self.test_chat_id, self.sample_entry["date"])
        self.assertTrue(result)
        
        # Check if the entry was deleted
        has_entry = has_entry_for_date(self.test_chat_id, self.sample_entry["date"])
        self.assertFalse(has_entry)
        
        # The other entry should still exist
        has_entry = has_entry_for_date(self.test_chat_id, other_entry["date"])
        self.assertTrue(has_entry)

    def test_delete_all_entries(self):
        """Test deleting all entries for a user."""
        # Save multiple entries
        save_data(self.sample_entry, self.test_chat_id)
        
        other_entry = self.sample_entry.copy()
        other_entry["date"] = "2023-02-01"
        save_data(other_entry, self.test_chat_id)
        
        # Delete all entries
        result = delete_all_entries(self.test_chat_id)
        self.assertTrue(result)
        
        # Get entries - should be empty
        entries = get_user_entries(self.test_chat_id)
        self.assertEqual(len(entries), 0)

    def test_entry_replacement(self):
        """Test that saving an entry for an existing date replaces the old entry."""
        # Save the sample entry
        save_data(self.sample_entry, self.test_chat_id)
        
        # Save a different entry for the same date
        updated_entry = self.sample_entry.copy()
        updated_entry["mood"] = "9"  # Change the mood value
        save_data(updated_entry, self.test_chat_id)
        
        # There should still be only one entry
        entries = get_user_entries(self.test_chat_id)
        self.assertEqual(len(entries), 1)

if __name__ == '__main__':
    unittest.main()
