import unittest
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analytics.pattern_detection import (
    analyze_trends, analyze_correlations, analyze_patterns,
    generate_insights, format_analytics_summary
)


class TestAnalytics(unittest.TestCase):
    """Test cases for analytics and pattern detection functionality."""

    def setUp(self):
        """Set up test data for analytics."""
        # Create sample entries spanning multiple days
        self.test_entries = []

        # Create entries for the last 30 days
        today = datetime.now().date()
        for i in range(30):
            date = today - timedelta(days=i)
            entry = {
                "date": date.strftime("%Y-%m-%d"),
                "mood": str(5 + (i % 5)),  # Mood cycles between 5-9
                "sleep": str(4 + (i % 3)),  # Sleep cycles between 4-6
                "balance": str(6),
                "mania": str(3),
                "depression": str(8 - (i % 3)),  # Depression cycles between 6-8
                "anxiety": str(7 - (i % 3)),  # Anxiety cycles between 5-7
                "irritability": str(4),
                "productivity": str(6 + (i % 3)),  # Productivity cycles between 6-8
                "sociability": str(5)
            }
            self.test_entries.append(entry)

        # Limited set of entries for testing failure cases
        self.limited_entries = self.test_entries[:3]

        # Empty entries
        self.empty_entries = []

    def test_analyze_trends_sufficient_data(self):
        """Test trend analysis with sufficient data."""
        result = analyze_trends(self.test_entries)

        # Check that analysis was successful
        self.assertEqual(result['status'], 'success')

        # Check that trends were found
        self.assertTrue('trends' in result)

        # Check specific trend components
        trends = result['trends']
        self.assertTrue(trends['weekly']['available'])
        self.assertTrue('best_day' in trends['weekly'])
        self.assertTrue('worst_day' in trends['weekly'])

    def test_analyze_trends_insufficient_data(self):
        """Test trend analysis with insufficient data."""
        result = analyze_trends(self.limited_entries)

        # Check that insufficient data was reported
        self.assertEqual(result['status'], 'insufficient_data')

    def test_analyze_correlations(self):
        """Test correlation analysis."""
        result = analyze_correlations(self.test_entries)

        # Check that analysis was successful
        self.assertEqual(result['status'], 'success')

        # Check that correlations were found
        self.assertTrue('correlations' in result)

        # Check specific correlation components
        correlations = result['correlations']
        self.assertTrue('positive' in correlations)
        self.assertTrue('negative' in correlations)

    def test_analyze_patterns_sufficient_data(self):
        """Test pattern analysis with sufficient data."""
        result = analyze_patterns(self.test_entries)

        # Check that analysis was successful
        self.assertEqual(result['status'], 'success')

        # Check that patterns were found
        self.assertTrue('patterns' in result)

        # Check specific pattern components
        patterns = result['patterns']
        self.assertTrue('weekday_mood' in patterns)
        self.assertTrue('weekend_vs_weekday' in patterns)

    def test_analyze_patterns_insufficient_data(self):
        """Test pattern analysis with insufficient data."""
        result = analyze_patterns(self.limited_entries)

        # Check that insufficient data was reported
        self.assertEqual(result['status'], 'insufficient_data')

    def test_generate_insights_sufficient_data(self):
        """Test insight generation with sufficient data."""
        result = generate_insights(self.test_entries)

        # Check that generation was successful
        self.assertEqual(result['status'], 'success')

        # Check that insights were found
        self.assertTrue('insights' in result)
        self.assertIsInstance(result['insights'], list)

    def test_generate_insights_insufficient_data(self):
        """Test insight generation with insufficient data."""
        result = generate_insights(self.limited_entries)

        # Check that insufficient data was reported
        self.assertEqual(result['status'], 'insufficient_data')

    def test_format_analytics_summary(self):
        """Test formatting analytics summary."""
        # Call the formatting function
        summary = format_analytics_summary(self.test_entries)

        # Check that the summary is a non-empty string
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)

        # Check for insufficient data message with empty entries
        summary_empty = format_analytics_summary(self.empty_entries)
        self.assertIn("Недостаточно данных", summary_empty)


if __name__ == '__main__':
    unittest.main()