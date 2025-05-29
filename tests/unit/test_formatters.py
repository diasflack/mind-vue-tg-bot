import unittest
import os
import sys
import pandas as pd
from datetime import datetime

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.formatters import (
    format_entry_summary, format_stats_summary, 
    format_entry_list, get_column_name
)

class TestFormatters(unittest.TestCase):
    """Test cases for data formatting functionality."""

    def setUp(self):
        """Set up test data for formatting."""
        # Sample entry
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
        
        # Sample entry without comment
        self.entry_without_comment = self.sample_entry.copy()
        self.entry_without_comment.pop("comment")
        
        # Multiple entries
        self.multiple_entries = [
            self.sample_entry,
            {
                "date": "2023-01-02",
                "mood": "7",
                "sleep": "6",
                "comment": "Another comment",
                "balance": "5",
                "mania": "2",
                "depression": "3",
                "anxiety": "5",
                "irritability": "4",
                "productivity": "7",
                "sociability": "6"
            },
            {
                "date": "2023-01-03",
                "mood": "9",
                "sleep": "8",
                "comment": None,
                "balance": "7",
                "mania": "1",
                "depression": "1",
                "anxiety": "2",
                "irritability": "2",
                "productivity": "9",
                "sociability": "8"
            }
        ]
        
        # Sample DataFrame
        self.sample_df = pd.DataFrame(self.multiple_entries)

    def test_format_entry_summary(self):
        """Test formatting a single entry summary."""
        summary = format_entry_summary(self.sample_entry)
        
        # Check that the summary is a non-empty string
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)
        
        # Check for key fields in the summary
        self.assertIn("Дата: 01.01.2023", summary)
        self.assertIn("Настроение: 8/10", summary)
        self.assertIn("Комментарий: Test comment", summary)
        
        # Test entry without comment
        summary_no_comment = format_entry_summary(self.entry_without_comment)
        self.assertNotIn("Комментарий", summary_no_comment)

    def test_format_stats_summary(self):
        """Test formatting statistics summary."""
        stats_summary = format_stats_summary(self.sample_df)
        
        # Check that the summary is a non-empty string
        self.assertIsInstance(stats_summary, str)
        self.assertTrue(len(stats_summary) > 0)
        
        # Check for key fields in the summary
        self.assertIn("Статистика", stats_summary)
        self.assertIn("Настроение: среднее =", stats_summary)
        self.assertIn("Всего записей: 3", stats_summary)
        self.assertIn("Период: с", stats_summary)

    def test_format_entry_list(self):
        """Test formatting a list of entries."""
        entry_list = format_entry_list(self.multiple_entries)
        
        # Check that the list is a non-empty string
        self.assertIsInstance(entry_list, str)
        self.assertTrue(len(entry_list) > 0)
        
        # Check that all dates are included
        self.assertIn("01.01.2023", entry_list)
        self.assertIn("02.01.2023", entry_list)
        self.assertIn("03.01.2023", entry_list)
        
        # Check for key format elements
        self.assertIn("Последние 3 записей", entry_list)
        self.assertIn("Настроение:", entry_list)
        
        # Test with empty entries list
        empty_list = format_entry_list([])
        self.assertIn("У вас еще нет записей", empty_list)
        
        # Test with max_entries parameter
        limited_list = format_entry_list(self.multiple_entries, max_entries=2)
        self.assertIn("Последние 2 записей", limited_list)
        self.assertIn("И еще 1 записей", limited_list)

    def test_get_column_name(self):
        """Test getting localized column names."""
        column_names = [
            ("mood", "😊 Настроение"),
            ("sleep", "😴 Сон"),
            ("balance", "⚖️ Ровность настроения"),
            ("anxiety", "😰 Тревога"),
            ("depression", "😞 Депрессия"),
            ("unknown", "unknown")  # Should return the original for unknown columns
        ]
        
        for column, expected in column_names:
            self.assertEqual(get_column_name(column), expected)

    def test_format_entry_list_handles_errors(self):
        """Test that format_entry_list handles errors gracefully."""
        # Create a list with an entry missing required fields
        problematic_entries = self.multiple_entries.copy()
        problematic_entries.append({"date": "2023-01-04"})  # Missing required fields
        
        # Should not raise an exception
        result = format_entry_list(problematic_entries)
        self.assertIsInstance(result, str)

if __name__ == '__main__':
    unittest.main()
