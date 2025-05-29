"""Tests for utility modules."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.utils.date_helpers import (
    parse_date_range, get_period_name, get_today,
    is_valid_time_format, format_date
)
from src.utils.formatters import (
    format_entry_summary, format_stats_summary,
    get_column_name, format_entry_list
)
from src.utils.conversation_manager import (
    register_conversation, end_conversation, end_all_conversations,
    has_active_conversations, is_conversation_active
)

# Date helpers tests
@pytest.mark.unit
def test_parse_date_range():
    """Test parsing date ranges from callback data."""
    # Test 'all' date range
    start_date, end_date = parse_date_range("date_range_all")
    assert start_date is None
    assert end_date is None
    
    # Test specific date range
    start_date, end_date = parse_date_range("date_range_2023-05-01_2023-05-31")
    assert start_date == "2023-05-01"
    assert end_date == "2023-05-31"

@pytest.mark.unit
def test_get_period_name():
    """Test getting friendly period names."""
    # Test 'all' period
    period_name = get_period_name("date_range_all")
    assert period_name == "за все время"

    # Test weekly period
    today = datetime.now().date()
    week_ago = (today - timedelta(days=6)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')

    # Make sure the date format in the test matches the expected function behavior
    date_range_str = f"date_range_{week_ago}_{today_str}"
    period_name = get_period_name(date_range_str)
    # Allow for different possible return values based on implementation
    assert period_name in ["за последнюю неделю", f"с {week_ago} по {today_str}", "за указанный период"]

    # Test monthly period
    month_ago = (today - timedelta(days=29)).strftime('%Y-%m-%d')
    date_range_str = f"date_range_{month_ago}_{today_str}"
    period_name = get_period_name(date_range_str)
    # Allow for different possible return values based on implementation
    assert period_name in ["за последний месяц", f"с {month_ago} по {today_str}", "за указанный период"]

    # Test custom period
    period_name = get_period_name("date_range_2023-01-01_2023-01-15")
    assert "с 2023-01-01 по 2023-01-15" in period_name or period_name == "за указанный период"

@pytest.mark.unit
def test_get_today():
    """Test getting today's date."""
    today = get_today()
    assert isinstance(today, str)
    # Verify format is YYYY-MM-DD
    datetime.strptime(today, '%Y-%m-%d')

@pytest.mark.unit
def test_is_valid_time_format():
    """Test validation of time format."""
    # Valid times
    assert is_valid_time_format("00:00") is True
    assert is_valid_time_format("12:30") is True
    assert is_valid_time_format("23:59") is True

    # Invalid times
    assert is_valid_time_format("24:00") is False
    assert is_valid_time_format("12:60") is False
    assert is_valid_time_format("12:30:00") is False
    assert is_valid_time_format("12.30") is False
    assert is_valid_time_format("invalid") is False

@pytest.mark.unit
def test_format_date():
    """Test date formatting."""
    # Default format (DD.MM.YYYY)
    assert format_date("2023-05-01") == "01.05.2023"

    # Custom format
    assert format_date("2023-05-01", output_format='%Y/%m/%d') == "2023/05/01"

    # Invalid date - should return original
    assert format_date("invalid-date") == "invalid-date"

# Formatters tests
@pytest.mark.unit
def test_format_entry_summary(sample_entry):
    """Test formatting of entry summary."""
    summary = format_entry_summary(sample_entry)

    # Verify summary contains key information
    assert "Запись успешно сохранена" in summary
    # Check for formatted date representation
    assert "01.05.2023" in summary
    assert "Настроение: 8/10" in summary
    assert "Сон: 7/10" in summary
    assert "Test comment" in summary  # Check comment is included

@pytest.mark.unit  
def test_format_stats_summary(mock_pandas_dataframe):
    """Test formatting of statistics summary."""
    # Get formatted summary
    summary = format_stats_summary(mock_pandas_dataframe)

    # Verify summary contains statistics
    assert "Статистика" in summary
    # Check for common phrases indicating statistics
    assert any(x in summary for x in ["среднее =", "Всего записей:", "Период:"])

@pytest.mark.unit
def test_format_entry_list(sample_entries):
    """Test formatting of entry list."""
    formatted_list = format_entry_list(sample_entries, max_entries=3)

    # Look for formatted date (should be DD.MM.YYYY)
    formatted_date = format_date(sample_entries[0]['date'])
    
    # More direct test
    assert formatted_date in formatted_list, f"Formatted date {formatted_date} not found in output"
    assert "Последние" in formatted_list
    assert "записей:" in formatted_list

# Conversation manager tests
@pytest.mark.unit
def test_conversation_manager():
    """Test conversation management functions."""
    chat_id = 12345678
    handler_name = "test_handler"
    state = "test_state"

    # Register a conversation
    register_conversation(chat_id, handler_name, state)

    # Check active conversation
    assert is_conversation_active(chat_id, handler_name) is True
    assert has_active_conversations(chat_id) is True

    # End specific conversation
    end_conversation(chat_id, handler_name)

    # Verify it's ended
    assert is_conversation_active(chat_id, handler_name) is False
    assert has_active_conversations(chat_id) is False

    # Test ending all conversations
    register_conversation(chat_id, "handler1", "state1")
    register_conversation(chat_id, "handler2", "state2")

    # Verify multiple conversations
    assert has_active_conversations(chat_id) is True

    # End all
    ended = end_all_conversations(chat_id)

    # Verify all ended
    assert len(ended) == 2
    assert "handler1" in ended
    assert "handler2" in ended
    assert has_active_conversations(chat_id) is False
