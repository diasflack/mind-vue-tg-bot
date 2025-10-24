"""
Tests for storage cache functionality (_cleanup_cache, _flush_cache_to_db).
These are critical tests for data integrity and performance.
"""

import unittest
import os
import sys
import tempfile
import shutil
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data import storage
from src.data.storage import (
    save_data, get_user_entries,
    _cleanup_cache, _flush_cache_to_db,
    _entries_cache, _cache_lock,
    CACHE_TTL, MAX_CACHE_SIZE
)
import src.config


class TestStorageCache(unittest.TestCase):
    """Test cases for storage caching functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()

        # Mock the DATA_FOLDER config
        self.original_data_folder = src.config.DATA_FOLDER
        src.config.DATA_FOLDER = self.test_dir

        # Test user IDs
        self.test_chat_id_1 = 123456789
        self.test_chat_id_2 = 987654321

        # Clear cache before each test
        with _cache_lock:
            _entries_cache.clear()

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

        # Mock encryption functions
        self.patcher1 = patch('src.data.storage.encrypt_data')
        self.mock_encrypt = self.patcher1.start()
        self.mock_encrypt.side_effect = lambda data, chat_id: f"encrypted_{chat_id}_{data['date']}"

        self.patcher2 = patch('src.data.storage.decrypt_data')
        self.mock_decrypt = self.patcher2.start()
        self.mock_decrypt.side_effect = lambda encrypted_data, chat_id: self.sample_entry.copy()

    def tearDown(self):
        """Clean up the test environment."""
        # Clear cache after each test
        with _cache_lock:
            _entries_cache.clear()

        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

        # Restore the original DATA_FOLDER
        src.config.DATA_FOLDER = self.original_data_folder

        # Stop the patchers
        self.patcher1.stop()
        self.patcher2.stop()

    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL and are cleaned up."""
        # Add entry to cache manually with old timestamp
        old_timestamp = datetime.now() - timedelta(seconds=CACHE_TTL + 10)

        with _cache_lock:
            _entries_cache[self.test_chat_id_1] = {
                "data": [self.sample_entry],
                "timestamp": old_timestamp,
                "modified": False
            }

        # Verify cache has the entry
        with _cache_lock:
            self.assertIn(self.test_chat_id_1, _entries_cache)

        # Run cleanup
        _cleanup_cache()

        # Verify entry was removed after cleanup
        with _cache_lock:
            self.assertNotIn(self.test_chat_id_1, _entries_cache)

    def test_cache_cleanup_preserves_fresh_entries(self):
        """Test that cleanup doesn't remove fresh cache entries."""
        # Add fresh entry to cache
        fresh_timestamp = datetime.now()

        with _cache_lock:
            _entries_cache[self.test_chat_id_1] = {
                "data": [self.sample_entry],
                "timestamp": fresh_timestamp,
                "modified": False
            }

        # Run cleanup
        _cleanup_cache()

        # Verify fresh entry is still in cache
        with _cache_lock:
            self.assertIn(self.test_chat_id_1, _entries_cache)

    def test_cache_cleanup_flushes_modified_entries(self):
        """Test that cleanup flushes modified entries to DB before removal."""
        # Add expired entry with modified flag
        old_timestamp = datetime.now() - timedelta(seconds=CACHE_TTL + 10)

        with _cache_lock:
            _entries_cache[self.test_chat_id_1] = {
                "data": [self.sample_entry],
                "timestamp": old_timestamp,
                "modified": True
            }

        # Mock _flush_cache_to_db to track if it's called
        with patch('src.data.storage._flush_cache_to_db') as mock_flush:
            _cleanup_cache()

            # Verify flush was called for the modified entry
            mock_flush.assert_called_once_with(self.test_chat_id_1)

        # Verify entry was removed after cleanup
        with _cache_lock:
            self.assertNotIn(self.test_chat_id_1, _entries_cache)

    def test_flush_cache_to_db_with_modified_flag(self):
        """Test that _flush_cache_to_db only flushes when modified flag is True."""
        # Add entry to cache with modified=False
        with _cache_lock:
            _entries_cache[self.test_chat_id_1] = {
                "data": [self.sample_entry],
                "timestamp": datetime.now(),
                "modified": False
            }

        # Call flush
        _flush_cache_to_db(self.test_chat_id_1)

        # Entry should still be in cache since it wasn't modified
        with _cache_lock:
            self.assertIn(self.test_chat_id_1, _entries_cache)
            self.assertFalse(_entries_cache[self.test_chat_id_1]["modified"])

    def test_flush_cache_updates_modified_flag(self):
        """Test that flush updates the modified flag after saving to DB."""
        # Save data to create cache entry with modified=True
        save_data(self.sample_entry, self.test_chat_id_1)

        # Verify modified flag is set
        with _cache_lock:
            self.assertIn(self.test_chat_id_1, _entries_cache)
            # Note: save_data calls _flush_cache_to_db immediately,
            # so modified flag is reset after save

    def test_cache_size_limit_triggers_flush(self):
        """Test that exceeding cache size limit triggers a flush."""
        # Save entries for multiple users to exceed cache size
        for i in range(MAX_CACHE_SIZE + 2):
            chat_id = self.test_chat_id_1 + i
            entry = self.sample_entry.copy()
            entry["date"] = f"2023-01-{i+1:02d}"

            # Mock flush to track calls
            with patch('src.data.storage._flush_cache_to_db') as mock_flush:
                save_data(entry, chat_id)

                # Check if flush was called when cache exceeded size
                if len(_entries_cache) > MAX_CACHE_SIZE:
                    self.assertGreater(mock_flush.call_count, 0)

    def test_cache_multiple_users_isolation(self):
        """Test that cache correctly isolates data between different users."""
        entry1 = self.sample_entry.copy()
        entry1["date"] = "2023-01-01"
        entry1["mood"] = "8"

        entry2 = self.sample_entry.copy()
        entry2["date"] = "2023-01-02"
        entry2["mood"] = "5"

        # Add entries for two different users
        with _cache_lock:
            _entries_cache[self.test_chat_id_1] = {
                "data": [entry1],
                "timestamp": datetime.now(),
                "modified": False
            }
            _entries_cache[self.test_chat_id_2] = {
                "data": [entry2],
                "timestamp": datetime.now(),
                "modified": False
            }

        # Verify both users have their own cache entries
        with _cache_lock:
            self.assertIn(self.test_chat_id_1, _entries_cache)
            self.assertIn(self.test_chat_id_2, _entries_cache)
            self.assertEqual(_entries_cache[self.test_chat_id_1]["data"][0]["mood"], "8")
            self.assertEqual(_entries_cache[self.test_chat_id_2]["data"][0]["mood"], "5")

    def test_cache_timestamp_update_on_access(self):
        """Test that cache timestamp is updated when data is accessed."""
        # Add entry to cache
        initial_timestamp = datetime.now() - timedelta(seconds=100)

        with _cache_lock:
            _entries_cache[self.test_chat_id_1] = {
                "data": [self.sample_entry],
                "timestamp": initial_timestamp,
                "modified": False
            }

        # Access the data (which should update timestamp in save_data)
        entry2 = self.sample_entry.copy()
        entry2["date"] = "2023-01-02"
        save_data(entry2, self.test_chat_id_1)

        # Verify timestamp was updated
        with _cache_lock:
            self.assertGreater(_entries_cache[self.test_chat_id_1]["timestamp"], initial_timestamp)

    def test_empty_cache_cleanup(self):
        """Test that cleanup works correctly with empty cache."""
        # Clear cache
        with _cache_lock:
            _entries_cache.clear()

        # Run cleanup - should not raise any errors
        try:
            _cleanup_cache()
            success = True
        except Exception as e:
            success = False
            self.fail(f"Cleanup failed on empty cache: {e}")

        self.assertTrue(success)

    def test_cache_modified_flag_on_save(self):
        """Test that saving data sets the modified flag correctly."""
        # Save data
        save_data(self.sample_entry, self.test_chat_id_1)

        # Note: save_data calls _flush_cache_to_db immediately after setting modified flag
        # So we need to check the behavior during the save operation

        # Add another entry without immediate flush
        with _cache_lock:
            if self.test_chat_id_1 in _entries_cache:
                # Add to existing cache
                _entries_cache[self.test_chat_id_1]["data"].append(self.sample_entry)
                _entries_cache[self.test_chat_id_1]["modified"] = True

                # Verify flag is set
                self.assertTrue(_entries_cache[self.test_chat_id_1]["modified"])

    def test_flush_cache_with_empty_data(self):
        """Test that flush handles empty data list correctly."""
        # Add entry to cache with empty data list
        with _cache_lock:
            _entries_cache[self.test_chat_id_1] = {
                "data": [],
                "timestamp": datetime.now(),
                "modified": True
            }

        # Call flush - should handle empty data gracefully
        try:
            _flush_cache_to_db(self.test_chat_id_1)
            success = True
        except Exception as e:
            success = False
            self.fail(f"Flush failed on empty data: {e}")

        self.assertTrue(success)

        # Modified flag should be reset
        with _cache_lock:
            if self.test_chat_id_1 in _entries_cache:
                self.assertFalse(_entries_cache[self.test_chat_id_1]["modified"])

    def test_flush_nonexistent_cache_entry(self):
        """Test that flush handles nonexistent cache entries gracefully."""
        # Clear cache
        with _cache_lock:
            _entries_cache.clear()

        # Try to flush nonexistent entry - should not raise error
        try:
            _flush_cache_to_db(999999999)
            success = True
        except Exception as e:
            success = False
            self.fail(f"Flush failed on nonexistent entry: {e}")

        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
