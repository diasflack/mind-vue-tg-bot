#!/usr/bin/env python3
"""
Simple test runner that tests basic functionality without external dependencies.
"""

import sys
import os
import unittest
from pathlib import Path

# Add src to Python path
src_path = str(Path(__file__).parent / "src")
sys.path.insert(0, src_path)

class TestBasicStructure(unittest.TestCase):
    """Test basic project structure and imports."""
    
    def test_config_module_exists(self):
        """Test that config module can be imported."""
        try:
            import src.config
            self.assertTrue(hasattr(src.config, 'DATA_FOLDER'))
            print("✓ Config module loads successfully")
        except ImportError as e:
            self.fail(f"Config module import failed: {e}")
    
    def test_basic_utils_exist(self):
        """Test that basic utility modules exist."""
        try:
            from src.utils import date_helpers
            # Test that key functions exist
            self.assertTrue(hasattr(date_helpers, 'get_today'))
            self.assertTrue(hasattr(date_helpers, 'format_date'))
            print("✓ Date helpers module loads successfully")
        except ImportError as e:
            self.fail(f"Date helpers import failed: {e}")
    
    def test_date_helpers_basic_functionality(self):
        """Test basic date helper functions without external dependencies."""
        try:
            from src.utils.date_helpers import get_today, format_date, is_valid_time_format
            
            # Test get_today returns a string
            today = get_today()
            self.assertIsInstance(today, str)
            print(f"✓ get_today() returns: {today}")
            
            # Test format_date with a known input
            formatted = format_date("2023-05-01")
            self.assertEqual(formatted, "01.05.2023")
            print(f"✓ format_date works: {formatted}")
            
            # Test is_valid_time_format
            self.assertTrue(is_valid_time_format("12:30"))
            self.assertFalse(is_valid_time_format("25:00"))
            print("✓ is_valid_time_format works correctly")
            
        except Exception as e:
            self.fail(f"Date helpers functionality test failed: {e}")
    
    def test_conversation_manager(self):
        """Test conversation manager without external dependencies."""
        try:
            from src.utils.conversation_manager import (
                register_conversation, end_conversation, 
                has_active_conversations, is_conversation_active
            )
            
            # Test basic conversation flow
            chat_id = 12345
            handler = "test_handler"
            state = "test_state"
            
            # Clear any existing conversations
            from src.utils import conversation_manager
            conversation_manager.active_conversations.clear()
            
            # Test registration
            register_conversation(chat_id, handler, state)
            self.assertTrue(has_active_conversations(chat_id))
            self.assertTrue(is_conversation_active(chat_id, handler))
            print("✓ Conversation registration works")
            
            # Test ending conversation
            end_conversation(chat_id, handler)
            self.assertFalse(has_active_conversations(chat_id))
            self.assertFalse(is_conversation_active(chat_id, handler))
            print("✓ Conversation ending works")
            
        except Exception as e:
            self.fail(f"Conversation manager test failed: {e}")

class TestFileStructure(unittest.TestCase):
    """Test that all expected files exist."""
    
    def test_source_files_exist(self):
        """Test that main source files exist."""
        expected_files = [
            "src/config.py",
            "src/bot.py", 
            "src/utils/date_helpers.py",
            "src/utils/formatters.py",
            "src/utils/conversation_manager.py",
            "src/data/encryption.py",
            "src/data/storage.py",
            "src/data/models.py"
        ]
        
        for file_path in expected_files:
            with self.subTest(file=file_path):
                self.assertTrue(Path(file_path).exists(), f"Missing file: {file_path}")
        
        print(f"✓ All {len(expected_files)} expected source files exist")
    
    def test_test_files_exist(self):
        """Test that test files exist."""
        expected_test_files = [
            "tests/conftest.py",
            "tests/unit/test_utils.py",
            "tests/unit/test_encryption.py",
            "tests/unit/test_date_helpers.py"
        ]
        
        for file_path in expected_test_files:
            with self.subTest(file=file_path):
                self.assertTrue(Path(file_path).exists(), f"Missing test file: {file_path}")
        
        print(f"✓ All {len(expected_test_files)} expected test files exist")

def main():
    """Run the basic tests."""
    print("🧪 MindVueBot Basic Test Runner")
    print("=" * 50)
    print("Testing basic functionality without external dependencies...")
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBasicStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestFileStructure))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("🎉 All basic tests passed!")
        print("✅ Project structure is sound")
        print("✅ Core functionality works without dependencies")
        print("\n💡 Next steps:")
        print("   1. Install missing dependencies (pandas, pytest, telegram, etc.)")
        print("   2. Run full test suite with: python run_all_tests.py")
        print("   3. Fix any remaining test issues")
        return 0
    else:
        print("❌ Some basic tests failed!")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
