"""
Тесты для расширенных функций работы с датами в модуле date_helpers.
"""

import pytest
from datetime import datetime, timedelta
from src.utils.date_helpers import (
    parse_user_date, is_valid_entry_date, format_date_for_user
)


class TestParseUserDate:
    """Тесты для функции parse_user_date."""

    def test_parse_dd_mm_yyyy_format(self):
        """Тест парсинга формата DD.MM.YYYY."""
        result = parse_user_date("25.05.2025")
        assert result == "2025-05-25"

    def test_parse_dd_mm_yy_format(self):
        """Тест парсинга формата DD.MM.YY."""
        result = parse_user_date("25.05.25")
        assert result == "2025-05-25"

    def test_parse_dd_mm_format_current_year(self):
        """Тест парсинга формата DD.MM (текущий год)."""
        current_year = datetime.now().year
        result = parse_user_date("25.05")
        assert result == f"{current_year}-05-25"

    def test_parse_dd_slash_mm_slash_yyyy_format(self):
        """Тест парсинга формата DD/MM/YYYY."""
        result = parse_user_date("25/05/2025")
        assert result == "2025-05-25"

    def test_parse_iso_format(self):
        """Тест парсинга ISO формата YYYY-MM-DD."""
        result = parse_user_date("2025-05-25")
        assert result == "2025-05-25"

    def test_invalid_date_format(self):
        """Тест обработки неверного формата даты."""
        result = parse_user_date("invalid_date")
        assert result is None

    def test_invalid_date_values(self):
        """Тест обработки невалидных значений дат."""
        result = parse_user_date("32.13.2025")  # Несуществующая дата
        assert result is None

    def test_empty_string(self):
        """Тест обработки пустой строки."""
        result = parse_user_date("")
        assert result is None

    def test_none_input(self):
        """Тест обработки None."""
        result = parse_user_date(None)
        assert result is None


class TestIsValidEntryDate:
    """Тесты для функции is_valid_entry_date."""

    def test_today_is_valid(self):
        """Тест: сегодняшняя дата валидна."""
        today = datetime.now().strftime('%Y-%m-%d')
        assert is_valid_entry_date(today) is True

    def test_yesterday_is_valid(self):
        """Тест: вчерашняя дата валидна."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        assert is_valid_entry_date(yesterday) is True

    def test_future_date_invalid(self):
        """Тест: будущая дата невалидна."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        assert is_valid_entry_date(tomorrow) is False

    def test_old_date_valid(self):
        """Тест: старая дата валидна."""
        old_date = "2020-01-01"
        assert is_valid_entry_date(old_date) is True

    def test_very_old_date_invalid(self):
        """Тест: очень старая дата невалидна."""
        very_old_date = "1999-12-31"
        assert is_valid_entry_date(very_old_date) is False

    def test_invalid_format(self):
        """Тест: неверный формат даты."""
        assert is_valid_entry_date("invalid") is False

    def test_none_input(self):
        """Тест: None входное значение."""
        assert is_valid_entry_date(None) is False


class TestFormatDateForUser:
    """Тесты для функции format_date_for_user."""

    def test_format_iso_to_user_format(self):
        """Тест форматирования ISO даты в пользовательский формат."""
        result = format_date_for_user("2025-05-25")
        assert result == "25.05.2025"

    def test_format_with_day_name(self):
        """Тест форматирования с названием дня недели."""
        result = format_date_for_user("2025-05-25", include_day_name=True)
        # Воскресенье 25.05.2025
        assert "25.05.2025" in result
        assert "воскресенье" in result.lower()

    def test_invalid_date_returns_original(self):
        """Тест: неверная дата возвращается как есть."""
        invalid_date = "invalid"
        result = format_date_for_user(invalid_date)
        assert result == invalid_date

    def test_none_input(self):
        """Тест: None возвращает пустую строку."""
        result = format_date_for_user(None)
        assert result == ""
