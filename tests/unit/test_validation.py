"""
Tests for validation utility module.
"""

import unittest
import os
import sys

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.validation import (
    validate_numeric_input,
    validate_comment,
    get_validation_error_message
)


class TestValidateNumericInput(unittest.TestCase):
    """Test validate_numeric_input function."""

    def test_valid_input_in_range(self):
        """Test valid numeric input within range."""
        is_valid, value = validate_numeric_input("5", min_val=1, max_val=10)
        self.assertTrue(is_valid)
        self.assertEqual(value, 5)

    def test_valid_input_at_min_boundary(self):
        """Test valid input at minimum boundary."""
        is_valid, value = validate_numeric_input("1", min_val=1, max_val=10)
        self.assertTrue(is_valid)
        self.assertEqual(value, 1)

    def test_valid_input_at_max_boundary(self):
        """Test valid input at maximum boundary."""
        is_valid, value = validate_numeric_input("10", min_val=1, max_val=10)
        self.assertTrue(is_valid)
        self.assertEqual(value, 10)

    def test_invalid_input_below_min(self):
        """Test invalid input below minimum."""
        is_valid, value = validate_numeric_input("0", min_val=1, max_val=10)
        self.assertFalse(is_valid)
        self.assertIsNone(value)

    def test_invalid_input_above_max(self):
        """Test invalid input above maximum."""
        is_valid, value = validate_numeric_input("11", min_val=1, max_val=10)
        self.assertFalse(is_valid)
        self.assertIsNone(value)

    def test_invalid_input_negative(self):
        """Test invalid negative input."""
        is_valid, value = validate_numeric_input("-5", min_val=1, max_val=10)
        self.assertFalse(is_valid)
        self.assertIsNone(value)

    def test_invalid_input_not_digit(self):
        """Test invalid non-digit input."""
        is_valid, value = validate_numeric_input("abc", min_val=1, max_val=10)
        self.assertFalse(is_valid)
        self.assertIsNone(value)

    def test_invalid_input_float(self):
        """Test invalid float input."""
        is_valid, value = validate_numeric_input("5.5", min_val=1, max_val=10)
        self.assertFalse(is_valid)
        self.assertIsNone(value)

    def test_invalid_input_with_spaces(self):
        """Test invalid input with spaces."""
        is_valid, value = validate_numeric_input("5 ", min_val=1, max_val=10)
        self.assertFalse(is_valid)
        self.assertIsNone(value)

    def test_custom_range(self):
        """Test validation with custom range."""
        is_valid, value = validate_numeric_input("50", min_val=1, max_val=100)
        self.assertTrue(is_valid)
        self.assertEqual(value, 50)


class TestValidateComment(unittest.TestCase):
    """Test validate_comment function."""

    def test_valid_comment(self):
        """Test valid comment."""
        is_valid, sanitized = validate_comment("Good day today")
        self.assertTrue(is_valid)
        self.assertEqual(sanitized, "Good day today")

    def test_empty_comment(self):
        """Test empty comment is valid."""
        is_valid, sanitized = validate_comment("")
        self.assertTrue(is_valid)
        self.assertEqual(sanitized, "")

    def test_comment_with_leading_trailing_spaces(self):
        """Test comment with spaces is trimmed."""
        is_valid, sanitized = validate_comment("  Hello  ")
        self.assertTrue(is_valid)
        self.assertEqual(sanitized, "Hello")

    def test_long_comment_truncated(self):
        """Test long comment is truncated."""
        long_comment = "A" * 600
        is_valid, sanitized = validate_comment(long_comment, max_length=500)
        self.assertTrue(is_valid)
        self.assertEqual(len(sanitized), 500)
        self.assertEqual(sanitized, "A" * 500)

    def test_comment_exactly_at_max_length(self):
        """Test comment at exactly max length."""
        comment = "A" * 500
        is_valid, sanitized = validate_comment(comment, max_length=500)
        self.assertTrue(is_valid)
        self.assertEqual(sanitized, comment)

    def test_comment_with_newlines(self):
        """Test comment with newlines is preserved."""
        comment = "Line 1\nLine 2\nLine 3"
        is_valid, sanitized = validate_comment(comment)
        self.assertTrue(is_valid)
        self.assertEqual(sanitized, comment)

    def test_comment_with_special_characters(self):
        """Test comment with special characters."""
        comment = "Test! @#$%^&*() 123"
        is_valid, sanitized = validate_comment(comment)
        self.assertTrue(is_valid)
        self.assertEqual(sanitized, comment)


class TestGetValidationErrorMessage(unittest.TestCase):
    """Test get_validation_error_message function."""

    def test_default_range(self):
        """Test error message with default range."""
        message = get_validation_error_message("настроение")
        self.assertEqual(message, "Пожалуйста, введите число от 1 до 10:")

    def test_custom_range(self):
        """Test error message with custom range."""
        message = get_validation_error_message("возраст", min_val=0, max_val=120)
        self.assertEqual(message, "Пожалуйста, введите число от 0 до 120:")

    def test_message_format(self):
        """Test error message format is consistent."""
        message = get_validation_error_message("test")
        self.assertIn("Пожалуйста", message)
        self.assertIn("введите число", message)


if __name__ == '__main__':
    unittest.main()
