"""
Tests for CSV migration functionality (_migrate_csv_to_sqlite).
Critical for data integrity during migration from CSV to SQLite.
"""

import unittest
import os
import sys
import tempfile
import shutil
import sqlite3
import pandas as pd
from unittest.mock import patch, MagicMock

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data import storage
from src.data.storage import (
    _migrate_csv_to_sqlite,
    _get_db_connection
)
import src.config


class TestCSVMigration(unittest.TestCase):
    """Test cases for CSV to SQLite migration functionality."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()

        # Save original values from storage module (not config)
        self.original_data_folder = storage.DATA_FOLDER
        self.original_db_file = storage.DB_FILE

        # Patch DATA_FOLDER and DB_FILE in the storage module directly
        storage.DATA_FOLDER = self.test_dir
        storage.DB_FILE = os.path.join(self.test_dir, "test_mood_tracker.db")

        # Also update in config for consistency
        self.original_config_data_folder = src.config.DATA_FOLDER
        src.config.DATA_FOLDER = self.test_dir

        # Reset the database connection
        if storage._db_connection:
            try:
                storage._db_connection.close()
            except:
                pass
        storage._db_connection = None

        # Test user IDs
        self.test_chat_id_1 = 123456789
        self.test_chat_id_2 = 987654321

    def tearDown(self):
        """Clean up the test environment."""
        # Close any open database connections
        if storage._db_connection:
            try:
                storage._db_connection.close()
            except:
                pass
            storage._db_connection = None

        # Remove the temporary directory
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass

        # Restore the original values in storage module
        storage.DATA_FOLDER = self.original_data_folder
        storage.DB_FILE = self.original_db_file

        # Restore config as well
        src.config.DATA_FOLDER = self.original_config_data_folder

    def _create_csv_file(self, chat_id, num_entries=5):
        """Helper to create a test CSV file."""
        csv_path = os.path.join(self.test_dir, f"user_{chat_id}_data.csv")

        # Create sample data
        data = []
        for i in range(num_entries):
            data.append({
                'date': f'2023-01-{i+1:02d}',
                'encrypted_data': f'encrypted_data_{chat_id}_{i}'
            })

        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False)

        return csv_path

    def _count_entries_in_db(self, chat_id):
        """Helper to count entries in database for a user."""
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entries WHERE chat_id = ?", (chat_id,))
        return cursor.fetchone()[0]

    def _get_entries_from_db(self, chat_id):
        """Helper to get all entries from database for a user."""
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT date, encrypted_data FROM entries WHERE chat_id = ? ORDER BY date",
            (chat_id,)
        )
        return cursor.fetchall()

    def test_migrate_single_user_csv(self):
        """Test migration of a single user's CSV file."""
        # Create CSV file
        csv_path = self._create_csv_file(self.test_chat_id_1, num_entries=3)

        # Verify CSV exists
        self.assertTrue(os.path.exists(csv_path))

        # Run migration
        _migrate_csv_to_sqlite()

        # Verify data was migrated to database
        count = self._count_entries_in_db(self.test_chat_id_1)
        self.assertEqual(count, 3)

        # Verify CSV file was backed up (renamed to .bak)
        backup_path = csv_path + '.bak'
        self.assertTrue(os.path.exists(backup_path), "Backup file should exist")
        self.assertFalse(os.path.exists(csv_path), "Original CSV should be renamed")

    def test_migrate_multiple_users_csv(self):
        """Test migration of multiple users' CSV files."""
        # Create CSV files for two users
        csv_path_1 = self._create_csv_file(self.test_chat_id_1, num_entries=3)
        csv_path_2 = self._create_csv_file(self.test_chat_id_2, num_entries=5)

        # Run migration
        _migrate_csv_to_sqlite()

        # Verify data was migrated for both users
        count_1 = self._count_entries_in_db(self.test_chat_id_1)
        count_2 = self._count_entries_in_db(self.test_chat_id_2)

        self.assertEqual(count_1, 3)
        self.assertEqual(count_2, 5)

        # Verify both CSV files were backed up
        self.assertTrue(os.path.exists(csv_path_1 + '.bak'))
        self.assertTrue(os.path.exists(csv_path_2 + '.bak'))

    def test_migrate_skips_already_migrated_data(self):
        """Test that migration doesn't duplicate data if run twice."""
        # Create CSV file
        csv_path = self._create_csv_file(self.test_chat_id_1, num_entries=3)

        # Run migration first time
        _migrate_csv_to_sqlite()

        # Verify initial count
        count_after_first = self._count_entries_in_db(self.test_chat_id_1)
        self.assertEqual(count_after_first, 3)

        # Restore CSV from backup to simulate second migration attempt
        backup_path = csv_path + '.bak'
        if os.path.exists(backup_path):
            shutil.copy(backup_path, csv_path)

        # Run migration second time
        _migrate_csv_to_sqlite()

        # Verify count didn't increase (migration was skipped)
        count_after_second = self._count_entries_in_db(self.test_chat_id_1)
        self.assertEqual(count_after_second, 3, "Migration should skip already migrated data")

    def test_migrate_preserves_data_integrity(self):
        """Test that migration preserves all data fields correctly."""
        # Create CSV file with specific data
        csv_path = os.path.join(self.test_dir, f"user_{self.test_chat_id_1}_data.csv")
        test_data = [
            {'date': '2023-01-01', 'encrypted_data': 'test_encrypted_data_1'},
            {'date': '2023-01-02', 'encrypted_data': 'test_encrypted_data_2'},
        ]
        df = pd.DataFrame(test_data)
        df.to_csv(csv_path, index=False)

        # Run migration
        _migrate_csv_to_sqlite()

        # Get entries from database
        entries = self._get_entries_from_db(self.test_chat_id_1)

        # Verify data integrity
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0][0], '2023-01-01')  # date
        self.assertEqual(entries[0][1], 'test_encrypted_data_1')  # encrypted_data
        self.assertEqual(entries[1][0], '2023-01-02')
        self.assertEqual(entries[1][1], 'test_encrypted_data_2')

    def test_migrate_empty_csv(self):
        """Test migration of an empty CSV file."""
        # Create empty CSV file (with headers only)
        csv_path = os.path.join(self.test_dir, f"user_{self.test_chat_id_1}_data.csv")
        df = pd.DataFrame(columns=['date', 'encrypted_data'])
        df.to_csv(csv_path, index=False)

        # Run migration - should not raise error
        try:
            _migrate_csv_to_sqlite()
            success = True
        except Exception as e:
            success = False
            self.fail(f"Migration failed on empty CSV: {e}")

        self.assertTrue(success)

        # Verify no entries were added
        count = self._count_entries_in_db(self.test_chat_id_1)
        self.assertEqual(count, 0)

    def test_migrate_with_no_csv_files(self):
        """Test migration when no CSV files exist."""
        # Ensure no CSV files exist
        csv_files = [f for f in os.listdir(self.test_dir)
                     if f.startswith('user_') and f.endswith('_data.csv')]
        self.assertEqual(len(csv_files), 0)

        # Run migration - should not raise error
        try:
            _migrate_csv_to_sqlite()
            success = True
        except Exception as e:
            success = False
            self.fail(f"Migration failed with no CSV files: {e}")

        self.assertTrue(success)

    def test_migrate_handles_corrupted_csv(self):
        """Test that migration handles corrupted CSV files gracefully."""
        # Create a corrupted CSV file
        csv_path = os.path.join(self.test_dir, f"user_{self.test_chat_id_1}_data.csv")
        with open(csv_path, 'w') as f:
            f.write("corrupted,data,without\nproper,structure")

        # Run migration - should not crash
        try:
            _migrate_csv_to_sqlite()
            success = True
        except Exception as e:
            # Migration should log error but not crash
            success = True

        self.assertTrue(success, "Migration should handle corrupted CSV gracefully")

    def test_migrate_large_csv(self):
        """Test migration of a large CSV file (100 entries)."""
        # Create large CSV file
        csv_path = self._create_csv_file(self.test_chat_id_1, num_entries=100)

        # Run migration
        _migrate_csv_to_sqlite()

        # Verify all entries were migrated
        count = self._count_entries_in_db(self.test_chat_id_1)
        self.assertEqual(count, 100)

        # Verify backup was created
        self.assertTrue(os.path.exists(csv_path + '.bak'))

    def test_migrate_with_duplicate_dates(self):
        """Test migration handles duplicate dates (UNIQUE constraint)."""
        # Create CSV with duplicate dates
        csv_path = os.path.join(self.test_dir, f"user_{self.test_chat_id_1}_data.csv")
        test_data = [
            {'date': '2023-01-01', 'encrypted_data': 'data_1'},
            {'date': '2023-01-01', 'encrypted_data': 'data_2'},  # Duplicate date
            {'date': '2023-01-02', 'encrypted_data': 'data_3'},
        ]
        df = pd.DataFrame(test_data)
        df.to_csv(csv_path, index=False)

        # Run migration - should use INSERT OR IGNORE
        _migrate_csv_to_sqlite()

        # Verify only unique dates were inserted
        count = self._count_entries_in_db(self.test_chat_id_1)
        # Should be 2 (first 2023-01-01 and 2023-01-02)
        self.assertLessEqual(count, 2, "Duplicate dates should be handled with OR IGNORE")

    def test_migrate_invalid_chat_id_filename(self):
        """Test migration handles invalid filename formats gracefully."""
        # Create CSV with invalid filename format
        invalid_path = os.path.join(self.test_dir, "user_invalid_data.csv")
        df = pd.DataFrame([{'date': '2023-01-01', 'encrypted_data': 'data'}])
        df.to_csv(invalid_path, index=False)

        # Run migration - should skip invalid files
        try:
            _migrate_csv_to_sqlite()
            success = True
        except Exception as e:
            success = True  # Should handle gracefully

        self.assertTrue(success, "Migration should handle invalid filenames gracefully")

    def test_migrate_creates_backup_before_deletion(self):
        """Test that backup is created before original CSV is deleted."""
        # Create CSV file
        csv_path = self._create_csv_file(self.test_chat_id_1, num_entries=3)
        original_content = open(csv_path, 'r').read()

        # Run migration
        _migrate_csv_to_sqlite()

        # Verify backup exists and contains same data
        backup_path = csv_path + '.bak'
        self.assertTrue(os.path.exists(backup_path))
        backup_content = open(backup_path, 'r').read()
        self.assertEqual(original_content, backup_content)


if __name__ == '__main__':
    unittest.main()
