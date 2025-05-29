import unittest
import os
import sys
import pandas as pd
import io
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.visualization.charts import create_time_series_chart, create_correlation_matrix
from src.visualization.heatmaps import create_monthly_heatmap, create_mood_distribution

class TestVisualization(unittest.TestCase):
    """Test cases for data visualization functionality."""

    def setUp(self):
        """Set up test data for visualization."""
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
        
        # Mock plt to avoid actually creating figures
        self.plt_patcher = patch('matplotlib.pyplot.savefig')
        self.mock_savefig = self.plt_patcher.start()
        # Fixed mock to accept **kwargs
        self.mock_savefig.side_effect = lambda buffer, *args, **kwargs: buffer.write(b'test image data')
        
        self.plt_close_patcher = patch('matplotlib.pyplot.close')
        self.mock_close = self.plt_close_patcher.start()


    def tearDown(self):
        """Clean up test environment."""
        self.plt_patcher.stop()
        self.plt_close_patcher.stop()

    def test_create_time_series_chart(self):
        """Test creating a time series chart."""
        # Test with a single column
        columns = ['mood']
        buffer = create_time_series_chart(self.test_entries, columns, chat_id=123456789)
        
        # Check that a buffer was returned
        self.assertIsInstance(buffer, io.BytesIO)
        
        # Check that the buffer contains data
        buffer.seek(0)
        data = buffer.read()
        self.assertTrue(len(data) > 0)
        
        # Test with multiple columns
        columns = ['mood', 'sleep', 'anxiety']
        buffer = create_time_series_chart(self.test_entries, columns, chat_id=123456789)
        
        # Check that a buffer was returned
        self.assertIsInstance(buffer, io.BytesIO)
        
        # Check that the buffer contains data
        buffer.seek(0)
        data = buffer.read()
        self.assertTrue(len(data) > 0)

    def test_create_correlation_matrix(self):
        """Test creating a correlation matrix."""
        columns = ['mood', 'sleep', 'anxiety', 'depression']
        buffer = create_correlation_matrix(self.test_entries, columns, chat_id=123456789)
        
        # Check that a buffer was returned
        self.assertIsInstance(buffer, io.BytesIO)
        
        # Check that the buffer contains data
        buffer.seek(0)
        data = buffer.read()
        self.assertTrue(len(data) > 0)

    def test_create_monthly_heatmap(self):
        """Test creating a monthly heatmap."""
        # Get the current year and month for the test
        year = datetime.now().year
        month = datetime.now().month
        
        buffer = create_monthly_heatmap(self.test_entries, year, month, 'mood', chat_id=123456789)
        
        # Check that a buffer was returned
        self.assertIsInstance(buffer, io.BytesIO)
        
        # Check that the buffer contains data
        buffer.seek(0)
        data = buffer.read()
        self.assertTrue(len(data) > 0)
        
        # Test with a different column
        buffer = create_monthly_heatmap(self.test_entries, year, month, 'sleep', chat_id=123456789)
        self.assertIsInstance(buffer, io.BytesIO)

    def test_create_mood_distribution(self):
        """Test creating a mood distribution chart."""
        buffer = create_mood_distribution(self.test_entries, 'mood', chat_id=123456789)
        
        # Check that a buffer was returned
        self.assertIsInstance(buffer, io.BytesIO)
        
        # Check that the buffer contains data
        buffer.seek(0)
        data = buffer.read()
        self.assertTrue(len(data) > 0)
        
        # Test with a different column
        buffer = create_mood_distribution(self.test_entries, 'anxiety', chat_id=123456789)
        self.assertIsInstance(buffer, io.BytesIO)

    def test_invalid_column(self):
        """Test handling of invalid column names."""
        # Testing with an invalid column name for monthly heatmap
        year = datetime.now().year
        month = datetime.now().month
        
        # This should return None for an invalid column
        buffer = create_monthly_heatmap(self.test_entries, year, month, 'invalid_column', chat_id=123456789)
        self.assertIsNone(buffer)
        
        # Testing with an invalid column name for mood distribution
        buffer = create_mood_distribution(self.test_entries, 'invalid_column', chat_id=123456789)
        self.assertIsNone(buffer)

if __name__ == '__main__':
    unittest.main()
