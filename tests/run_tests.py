#!/usr/bin/env python
"""
Test runner for the Telegram Mood Tracker Bot.
Discovers and runs all tests in the tests directory.
"""

import unittest
import sys
import os

def run_tests():
    """Discover and run all tests."""
    # Add the parent directory to sys.path so test modules can import the app modules
    sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
    
    # Configure the test loader
    loader = unittest.TestLoader()
    
    # Discover tests in the tests directory
    test_suite = loader.discover('tests', pattern='*test*.py')
    
    # Create a runner and run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return the test result for CI/CD pipelines
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
