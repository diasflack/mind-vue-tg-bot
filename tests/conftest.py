"""
Test configuration and fixtures for MindVueBot tests.
"""

import pytest
import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add the src directory to the path so tests can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

@pytest.fixture
def sample_entry():
    """Sample entry data for testing."""
    return {
        "date": "2023-05-01",
        "mood": "8",
        "sleep": "7",
        "balance": "6",
        "mania": "3",
        "depression": "2",
        "anxiety": "4", 
        "irritability": "3",
        "productivity": "8",
        "sociability": "7",
        "comment": "Test comment"
    }

@pytest.fixture
def sample_entries():
    """Sample list of entries for testing."""
    return [
        {
            "date": "2023-05-01",
            "mood": "8",
            "sleep": "7",
            "balance": "6",
            "mania": "3",
            "depression": "2",
            "anxiety": "4",
            "irritability": "3",
            "productivity": "8",
            "sociability": "7",
            "comment": "First test entry"
        },
        {
            "date": "2023-05-02", 
            "mood": "7",
            "sleep": "8",
            "balance": "7",
            "mania": "2",
            "depression": "3",
            "anxiety": "3",
            "irritability": "2",
            "productivity": "9",
            "sociability": "8",
            "comment": "Second test entry"
        },
        {
            "date": "2023-05-03",
            "mood": "9",
            "sleep": "6",
            "balance": "8", 
            "mania": "4",
            "depression": "1",
            "anxiety": "2",
            "irritability": "1",
            "productivity": "7",
            "sociability": "9",
            "comment": "Third test entry"
        }
    ]

@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for test data."""
    test_dir = tempfile.mkdtemp()
    yield test_dir
    shutil.rmtree(test_dir)

@pytest.fixture
def mock_config(temp_test_dir):
    """Mock configuration values for tests."""
    import src.config
    
    # Store original values
    original_values = {}
    config_attrs = ['DATA_FOLDER', 'SECRET_SALT', 'SYSTEM_SALT', 'TELEGRAM_BOT_TOKEN']
    
    for attr in config_attrs:
        if hasattr(src.config, attr):
            original_values[attr] = getattr(src.config, attr)
    
    # Set test values
    src.config.DATA_FOLDER = temp_test_dir
    src.config.SECRET_SALT = b"test_secret_salt_16b"
    src.config.SYSTEM_SALT = b"test_system_salt_16b"
    src.config.TELEGRAM_BOT_TOKEN = "test_token_12345"
    
    # Add conversation states if they don't exist
    if not hasattr(src.config, 'MOOD'):
        src.config.MOOD = 1
    if not hasattr(src.config, 'SLEEP'):
        src.config.SLEEP = 2
    if not hasattr(src.config, 'COMMENT'):
        src.config.COMMENT = 3
    if not hasattr(src.config, 'BALANCE'):
        src.config.BALANCE = 4
    
    yield src.config
    
    # Restore original values
    for attr, value in original_values.items():
        setattr(src.config, attr, value)

@pytest.fixture
def mock_telegram_update():
    """Mock Telegram update object."""
    update = MagicMock()
    update.effective_chat.id = 123456789
    update.effective_user.username = "test_user"
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"
    update.message = MagicMock()
    update.message.text = "test message"
    return update

@pytest.fixture
def mock_telegram_context():
    """Mock Telegram context object."""
    context = MagicMock()
    context.user_data = {}
    context.bot_data = {}
    context.chat_data = {}
    return context

@pytest.fixture(autouse=True)
def clean_conversation_manager():
    """Clear conversation manager state before each test."""
    try:
        import src.utils.conversation_manager
        if hasattr(src.utils.conversation_manager, 'active_conversations'):
            src.utils.conversation_manager.active_conversations.clear()
    except ImportError:
        pass  # Module might not exist yet
    
    yield
    
    # Clean up after test
    try:
        if hasattr(src.utils.conversation_manager, 'active_conversations'):
            src.utils.conversation_manager.active_conversations.clear()
    except ImportError:
        pass

@pytest.fixture
def mock_pandas_dataframe(sample_entries):
    """Mock pandas DataFrame with sample entries."""
    try:
        import pandas as pd
        return pd.DataFrame(sample_entries)
    except ImportError:
        # If pandas is not available, return a mock
        mock_df = MagicMock()
        mock_df.__iter__ = lambda x: iter(sample_entries)
        mock_df.__len__ = lambda x: len(sample_entries)
        return mock_df

# Environment variable patches for tests that need them
@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    env_vars = {
        'TELEGRAM_BOT_TOKEN': 'test_token_12345',
        'DATA_FOLDER': '/tmp/test_data',
        'SECRET_SALT': 'dGVzdF9zZWNyZXRfc2FsdA==',  # base64 encoded
        'SYSTEM_SALT': 'dGVzdF9zeXN0ZW1fc2FsdA=='   # base64 encoded
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars
