# Tests for Telegram Mood Tracker Bot

This directory contains the tests for the Telegram Mood Tracker Bot.

## Test Structure

The test suite is organized as follows:

- **`encryption_test.py`**: Tests for the encryption/decryption functionality
- **`storage_test.py`**: Tests for data storage and retrieval operations
- **`analytics_test.py`**: Tests for the analytics and pattern detection functionality
- **`visualization_test.py`**: Tests for the data visualization functionality
- **`formatters_test.py`**: Tests for the data formatting functions
- **`date_helpers_test.py`**: Tests for date manipulation and validation
- **`bot_test.py`**: Tests for core bot functionality and conversation flow
- **`run_tests.py`**: Script to discover and run all tests

## Running Tests

### Setup

Before running the tests, you need to set up the test environment. You can do this by running:

```bash
chmod +x setup_test_env.sh
./setup_test_env.sh
```

This will create a virtual environment, install all the necessary dependencies, and set up the test directory.

### Running All Tests

To run all tests, use the `run_tests.py` script:

```bash
python tests/run_tests.py
```

### Running Specific Tests

To run a specific test file:

```bash
python -m unittest tests/encryption_test.py
```

To run a specific test case:

```bash
python -m unittest tests.encryption_test.TestEncryption.test_encrypt_decrypt_cycle
```

### With pytest

If you prefer to use pytest:

```bash
# Run all tests
pytest tests/

# Run a specific test file
pytest tests/encryption_test.py

# Run a specific test
pytest tests/encryption_test.py::TestEncryption::test_encrypt_decrypt_cycle

# Generate coverage report
pytest --cov=src tests/
```

## Writing New Tests

When adding new functionality to the bot, it's important to add corresponding tests. Follow these guidelines:

1. Create a new test file if you're testing a new module
2. Subclass `unittest.TestCase` for your test class
3. Use descriptive test method names that explain what is being tested
4. Use `setUp` and `tearDown` methods for common setup and cleanup
5. Follow the existing test pattern for consistency
6. Mock external dependencies like Telegram API calls

## Mocking Telegram Bot API

Many of the tests need to mock the Telegram Bot API to avoid making actual API calls during testing. We use the `unittest.mock` module to create mocks for `Update`, `Context`, and other Telegram objects.

Example of mocking a Telegram update:

```python
from unittest.mock import MagicMock, AsyncMock

# Mock update object
update = MagicMock()
update.effective_chat.id = 123456789
update.message = AsyncMock()
update.message.text = "Test message"
```

## Testing Asynchronous Code

For testing asynchronous handlers, use `pytest-asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result == expected_value
```

## Coverage Report

To generate a coverage report, run:

```bash
pytest --cov=src tests/
```

For a more detailed HTML report:

```bash
pytest --cov=src --cov-report=html tests/
```

Then open `htmlcov/index.html` in a web browser to view the coverage report.
