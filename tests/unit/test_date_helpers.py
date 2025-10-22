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

    @freeze_time("2023-05-15")  # Anchor 'today' so the date part is stable
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

    @freeze_time("2023-05-15")
    def test_extreme_timezones(self):
        """Test extreme timezone offsets (UTC-12 to UTC+14)."""
        test_cases = [
            # Extreme negative offset (Baker Island, Howland Island)
            (time(12, 0), -12, "00:00", "UTC-12:00 (Baker Island) → next day boundary"),
            (time(0, 0), -12, "12:00", "UTC-12:00 midnight → noon UTC"),
            (time(23, 59), -12, "11:59", "UTC-12:00 almost midnight"),

            # Extreme positive offset (Line Islands, Kiribati)
            (time(12, 0), 14, "22:00", "UTC+14:00 (Kiribati) → previous day"),
            (time(0, 0), 14, "10:00", "UTC+14:00 midnight → morning UTC prev day"),
            (time(14, 0), 14, "00:00", "UTC+14:00 2pm → midnight UTC"),

            # UTC+13 (Tonga, Samoa)
            (time(13, 0), 13, "00:00", "UTC+13:00 1pm → midnight UTC"),
            (time(0, 30), 13, "11:30", "UTC+13:00 past midnight"),

            # UTC-11 (American Samoa)
            (time(11, 0), -11, "22:00", "UTC-11:00 11am → 10pm UTC prev day"),
            (time(23, 0), -11, "10:00", "UTC-11:00 11pm → 10am UTC next day"),
        ]

        for local_t, offset, expected, description in test_cases:
            with self.subTest(msg=description, local_time=local_t, offset=offset):
                result = local_to_utc(local_t, offset)
                self.assertEqual(
                    result,
                    expected,
                    f"{description}: {local_t} @ UTC{offset:+} → {expected}, got {result}",
                )

    @freeze_time("2023-05-15")
    def test_midnight_crossovers(self):
        """Test critical midnight boundary cases."""
        test_cases = [
            # Crossing midnight backwards (local time after midnight → UTC before midnight)
            (time(0, 0), 1, "23:00", "UTC+1 midnight → 11pm UTC previous day"),
            (time(0, 1), 2, "22:01", "UTC+2 just past midnight"),
            (time(1, 0), 3, "22:00", "UTC+3 1am → 10pm UTC previous day"),

            # Crossing midnight forwards (local time before midnight → UTC after midnight)
            (time(23, 0), -1, "00:00", "UTC-1 11pm → midnight UTC next day"),
            (time(23, 59), -1, "00:59", "UTC-1 almost midnight"),
            (time(22, 0), -2, "00:00", "UTC-2 10pm → midnight UTC next day"),

            # Edge case: exactly at midnight with zero offset
            (time(0, 0), 0, "00:00", "UTC midnight stays midnight"),

            # Multiple day wrap-around scenarios
            (time(1, 30), 5, "20:30", "UTC+5 early morning → evening before"),
            (time(22, 30), -5, "03:30", "UTC-5 late evening → early morning after"),
        ]

        for local_t, offset, expected, description in test_cases:
            with self.subTest(msg=description, local_time=local_t, offset=offset):
                result = local_to_utc(local_t, offset)
                self.assertEqual(
                    result,
                    expected,
                    f"{description}: {local_t} @ UTC{offset:+} → {expected}, got {result}",
                )

    @freeze_time("2023-05-15")
    def test_negative_offsets(self):
        """Test comprehensive negative timezone offsets."""
        test_cases = [
            # Americas timezones
            (time(10, 0), -5, "15:00", "UTC-5 (EST) 10am → 3pm UTC"),
            (time(14, 30), -5, "19:30", "UTC-5 (EST) afternoon"),
            (time(8, 0), -8, "16:00", "UTC-8 (PST) 8am → 4pm UTC"),
            (time(20, 0), -7, "03:00", "UTC-7 (MST) 8pm → 3am UTC next day"),

            # Edge cases with negative offsets
            (time(0, 0), -1, "01:00", "UTC-1 midnight → 1am UTC"),
            (time(12, 0), -6, "18:00", "UTC-6 noon → 6pm UTC"),
        ]

        for local_t, offset, expected, description in test_cases:
            with self.subTest(msg=description, local_time=local_t, offset=offset):
                result = local_to_utc(local_t, offset)
                self.assertEqual(
                    result,
                    expected,
                    f"{description}: {local_t} @ UTC{offset:+} → {expected}, got {result}",
                )


if __name__ == '__main__':
    unittest.main()
