import unittest
import os
import sys
from freezegun import freeze_time
from datetime import time

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.date_helpers import (
    parse_date_range, get_period_name, get_today, 
    is_valid_time_format, format_date, local_to_utc
)

class TestDateHelpers(unittest.TestCase):
    """Test cases for date helper functions."""

    def test_parse_date_range(self):
        """Test parsing date range strings."""
        # Test "all time" range
        start_date, end_date = parse_date_range("date_range_all")
        self.assertIsNone(start_date)
        self.assertIsNone(end_date)
        
        # Test specific date range
        start_date, end_date = parse_date_range("date_range_2023-01-01_2023-01-31")
        self.assertEqual(start_date, "2023-01-01")
        self.assertEqual(end_date, "2023-01-31")

    def test_get_period_name(self):
        """Test getting human-readable period names."""
        # Test "all time" period
        period_name = get_period_name("date_range_all")
        self.assertEqual(period_name, "за все время")
        
        # Test week period
        period_name = get_period_name("date_range_2023-01-01_2023-01-07")
        self.assertEqual(period_name, "за последнюю неделю")
        
        # Test month period
        period_name = get_period_name("date_range_2023-01-01_2023-01-30")
        self.assertEqual(period_name, "за последний месяц")
        
        # Test quarter period
        period_name = get_period_name("date_range_2023-01-01_2023-03-31")
        self.assertEqual(period_name, "за последние 3 месяца")
        
        # Test custom period
        period_name = get_period_name("date_range_2023-01-15_2023-02-15")
        self.assertEqual(period_name, "с 2023-01-15 по 2023-02-15")

    @freeze_time("2023-05-15")
    def test_get_today(self):
        """Test getting today's date string."""
        today = get_today()
        self.assertEqual(today, "2023-05-15")

    def test_is_valid_time_format(self):
        """Test validation of time format strings."""
        # Valid time formats
        self.assertTrue(is_valid_time_format("00:00"))
        self.assertTrue(is_valid_time_format("12:30"))
        self.assertTrue(is_valid_time_format("23:59"))
        
        # Invalid time formats
        self.assertFalse(is_valid_time_format("24:00"))  # Hour too large
        self.assertFalse(is_valid_time_format("12:60"))  # Minute too large
        self.assertFalse(is_valid_time_format("12:30:00"))  # Includes seconds
        self.assertFalse(is_valid_time_format("12-30"))  # Wrong separator
        self.assertFalse(is_valid_time_format("12:3"))  # Minute not two digits
        self.assertFalse(is_valid_time_format("1:30"))  # Hour not two digits
        self.assertFalse(is_valid_time_format("ab:cd"))  # Not numbers
        self.assertFalse(is_valid_time_format(""))  # Empty string
        self.assertFalse(is_valid_time_format("12"))  # Missing minutes

    def test_format_date(self):
        """Test formatting date strings."""
        # Test with default format (DD.MM.YYYY)
        formatted = format_date("2023-05-15")
        self.assertEqual(formatted, "15.05.2023")
        
        # Test with custom format
        formatted = format_date("2023-05-15", output_format="%d/%m/%Y")
        self.assertEqual(formatted, "15/05/2023")
        
        # Test with invalid date (should return original)
        formatted = format_date("invalid-date")
        self.assertEqual(formatted, "invalid-date")
        
        # Test with empty string
        formatted = format_date("")
        self.assertEqual(formatted, "")

    @freeze_time("2023-05-15")  # Anchor ‘today’ so the date part is stable
    def test_various_offsets(self):
        """Validate conversion for several representative offsets."""
        test_matrix = [
            # local time,  offset (h), expected UTC,  description
            (time(12, 0), 0, "12:00", "UTC itself"),
            (time(12, 0), 3, "09:00", "UTC+03:00 → earlier"),
            (time(23, 45), -2, "01:45", "UTC−02:00 → next day"),
            (time(0, 30), 5.5, "19:00", "UTC+05:30 → prev day"),
            (time(0, 0), -10, "10:00", "UTC−10:00 → same day"),
            (time(18, 45), -3.5, "22:15", "UTC−03:30 fractional"),
            (time(10, 0), 4.25, "05:45", "UTC+04:15 fractional"),
        ]

        for local_t, offset, expected, note in test_matrix:
            with self.subTest(msg=note, local_time=local_t, offset=offset):
                utc_clock = local_to_utc(local_t, offset)
                self.assertEqual(
                    utc_clock,
                    expected,
                    f"{note}: {local_t} @ UTC{offset:+} → {expected}",
                )


if __name__ == '__main__':
    unittest.main()
