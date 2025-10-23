"""
Тесты для рефакторинговых вспомогательных функций pattern_detection.
Проверяет работу новых функций, извлеченных из generate_insights.
"""

import unittest
from datetime import datetime, timedelta
from src.analytics.pattern_detection import (
    _analyze_correlation_insights,
    _analyze_trend_insights,
    _analyze_pattern_insights,
    _analyze_general_recommendations
)


class TestAnalyzeCorrelationInsights(unittest.TestCase):
    """Тесты для функции _analyze_correlation_insights."""

    def test_successful_positive_correlations(self):
        """Test generating insights from positive correlations."""
        corr_results = {
            'status': 'success',
            'correlations': {
                'positive': [
                    {'factor': 'sleep', 'correlation': 0.75},
                    {'factor': 'productivity', 'correlation': 0.85}
                ],
                'negative': []
            }
        }

        insights = _analyze_correlation_insights(corr_results)

        self.assertEqual(len(insights), 2)
        self.assertEqual(insights[0]['type'], 'correlation_positive')
        self.assertEqual(insights[0]['strength'], 'strong')
        self.assertIn('sleep', insights[0]['factor'])
        self.assertIn('корреляци', insights[0]['message'].lower())

    def test_successful_negative_correlations(self):
        """Test generating insights from negative correlations."""
        corr_results = {
            'status': 'success',
            'correlations': {
                'positive': [],
                'negative': [
                    {'factor': 'anxiety', 'correlation': -0.70},
                    {'factor': 'depression', 'correlation': -0.65}
                ]
            }
        }

        insights = _analyze_correlation_insights(corr_results)

        self.assertEqual(len(insights), 2)
        self.assertEqual(insights[0]['type'], 'correlation_negative')
        self.assertEqual(insights[0]['strength'], 'strong')
        self.assertEqual(insights[0]['factor'], 'anxiety')

    def test_weak_correlations_ignored(self):
        """Test that weak correlations are not included in insights."""
        corr_results = {
            'status': 'success',
            'correlations': {
                'positive': [
                    {'factor': 'sleep', 'correlation': 0.5}  # Too weak (< 0.6)
                ],
                'negative': [
                    {'factor': 'anxiety', 'correlation': -0.4}  # Too weak (> -0.6)
                ]
            }
        }

        insights = _analyze_correlation_insights(corr_results)

        self.assertEqual(len(insights), 0)

    def test_error_status(self):
        """Test handling error status in correlation results."""
        corr_results = {
            'status': 'error',
            'message': 'Some error'
        }

        insights = _analyze_correlation_insights(corr_results)

        self.assertEqual(len(insights), 0)

    def test_insufficient_data_status(self):
        """Test handling insufficient_data status."""
        corr_results = {
            'status': 'insufficient_data',
            'message': 'Not enough data'
        }

        insights = _analyze_correlation_insights(corr_results)

        self.assertEqual(len(insights), 0)


class TestAnalyzeTrendInsights(unittest.TestCase):
    """Тесты для функции _analyze_trend_insights."""

    def test_weekly_pattern_significant_difference(self):
        """Test generating insights from weekly patterns with significant difference."""
        trend_results = {
            'status': 'success',
            'trends': {
                'weekly': {
                    'available': True,
                    'best_day': {'day': 'Пятница', 'value': 8.0},
                    'worst_day': {'day': 'Понедельник', 'value': 5.0}
                },
                'recent': {'available': False}
            }
        }

        insights = _analyze_trend_insights(trend_results)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]['type'], 'weekly_pattern')
        self.assertIn('пятниц', insights[0]['message'].lower())
        self.assertIn('понедельник', insights[0]['message'].lower())

    def test_weekly_pattern_small_difference(self):
        """Test that small weekly differences are ignored."""
        trend_results = {
            'status': 'success',
            'trends': {
                'weekly': {
                    'available': True,
                    'best_day': {'day': 'Пятница', 'value': 7.0},
                    'worst_day': {'day': 'Понедельник', 'value': 6.5}  # Diff < 2
                },
                'recent': {'available': False}
            }
        }

        insights = _analyze_trend_insights(trend_results)

        self.assertEqual(len(insights), 0)

    def test_recent_trend_upward(self):
        """Test generating insights from upward recent trend."""
        trend_results = {
            'status': 'success',
            'trends': {
                'weekly': {'available': False},
                'recent': {
                    'available': True,
                    'mood_trend': 'upward',
                    'mood_slope': 0.5
                }
            }
        }

        insights = _analyze_trend_insights(trend_results)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]['type'], 'recent_trend')
        self.assertEqual(insights[0]['trend'], 'positive')
        self.assertIn('улучшению', insights[0]['message'])

    def test_recent_trend_downward(self):
        """Test generating insights from downward recent trend."""
        trend_results = {
            'status': 'success',
            'trends': {
                'weekly': {'available': False},
                'recent': {
                    'available': True,
                    'mood_trend': 'downward',
                    'mood_slope': -0.5
                }
            }
        }

        insights = _analyze_trend_insights(trend_results)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]['type'], 'recent_trend')
        self.assertEqual(insights[0]['trend'], 'negative')
        self.assertIn('ухудшению', insights[0]['message'])

    def test_recent_trend_stable(self):
        """Test that stable trends are ignored."""
        trend_results = {
            'status': 'success',
            'trends': {
                'weekly': {'available': False},
                'recent': {
                    'available': True,
                    'mood_trend': 'stable',
                    'mood_slope': 0.1
                }
            }
        }

        insights = _analyze_trend_insights(trend_results)

        self.assertEqual(len(insights), 0)

    def test_error_status(self):
        """Test handling error status in trend results."""
        trend_results = {
            'status': 'error',
            'message': 'Some error'
        }

        insights = _analyze_trend_insights(trend_results)

        self.assertEqual(len(insights), 0)


class TestAnalyzePatternInsights(unittest.TestCase):
    """Тесты для функции _analyze_pattern_insights."""

    def test_weekend_mood_higher(self):
        """Test insight generation when weekend mood is significantly higher."""
        pattern_results = {
            'status': 'success',
            'patterns': {
                'weekend_vs_weekday': {
                    'weekend_mood': 8.0,
                    'weekday_mood': 5.5
                },
                'cyclicality': {'detected': False}
            }
        }

        insights = _analyze_pattern_insights(pattern_results)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]['type'], 'weekend_effect')
        self.assertEqual(insights[0]['effect'], 'positive')
        self.assertIn('выходные', insights[0]['message'])

    def test_weekday_mood_higher(self):
        """Test insight generation when weekday mood is significantly higher."""
        pattern_results = {
            'status': 'success',
            'patterns': {
                'weekend_vs_weekday': {
                    'weekend_mood': 5.0,
                    'weekday_mood': 7.5
                },
                'cyclicality': {'detected': False}
            }
        }

        insights = _analyze_pattern_insights(pattern_results)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]['type'], 'weekend_effect')
        self.assertEqual(insights[0]['effect'], 'negative')
        self.assertIn('будни', insights[0]['message'])

    def test_no_weekend_effect(self):
        """Test that small mood differences are ignored."""
        pattern_results = {
            'status': 'success',
            'patterns': {
                'weekend_vs_weekday': {
                    'weekend_mood': 6.5,
                    'weekday_mood': 6.0  # Diff < 2
                },
                'cyclicality': {'detected': False}
            }
        }

        insights = _analyze_pattern_insights(pattern_results)

        self.assertEqual(len(insights), 0)

    def test_cyclicality_detected(self):
        """Test insight generation when cyclicality is detected."""
        pattern_results = {
            'status': 'success',
            'patterns': {
                'weekend_vs_weekday': {
                    'weekend_mood': 6.5,
                    'weekday_mood': 6.0
                },
                'cyclicality': {
                    'detected': True,
                    'cycle_days': 7,
                    'correlation': 0.65
                }
            }
        }

        insights = _analyze_pattern_insights(pattern_results)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]['type'], 'cyclicality')
        self.assertEqual(insights[0]['cycle_days'], 7)
        self.assertIn('7 дней', insights[0]['message'])

    def test_error_status(self):
        """Test handling error status in pattern results."""
        pattern_results = {
            'status': 'error',
            'message': 'Some error'
        }

        insights = _analyze_pattern_insights(pattern_results)

        self.assertEqual(len(insights), 0)


class TestAnalyzeGeneralRecommendations(unittest.TestCase):
    """Тесты для функции _analyze_general_recommendations."""

    def test_sleep_recommendation_high_correlation_low_quality(self):
        """Test sleep recommendation when correlation is high but quality is low."""
        entries = [
            {'mood': 8, 'sleep': 7, 'anxiety': 3},
            {'mood': 7, 'sleep': 6, 'anxiety': 4},
            {'mood': 6, 'sleep': 5, 'anxiety': 5},
            {'mood': 5, 'sleep': 4, 'anxiety': 6},
            {'mood': 4, 'sleep': 3, 'anxiety': 7},
            {'mood': 3, 'sleep': 2, 'anxiety': 8},
            {'mood': 2, 'sleep': 1, 'anxiety': 9}
        ]

        insights = _analyze_general_recommendations(entries)

        # Should generate sleep recommendation (high correlation + low avg sleep)
        sleep_insights = [i for i in insights if i['type'] == 'sleep_recommendation']
        self.assertEqual(len(sleep_insights), 1)
        self.assertEqual(sleep_insights[0]['strength'], 'strong')
        self.assertIn('сон', sleep_insights[0]['message'])

    def test_no_sleep_recommendation_good_quality(self):
        """Test no sleep recommendation when sleep quality is good."""
        entries = [
            {'mood': 8, 'sleep': 8, 'anxiety': 3},
            {'mood': 7, 'sleep': 7, 'anxiety': 4},
            {'mood': 8, 'sleep': 9, 'anxiety': 3},
            {'mood': 7, 'sleep': 8, 'anxiety': 4},
            {'mood': 8, 'sleep': 8, 'anxiety': 3},
            {'mood': 7, 'sleep': 7, 'anxiety': 4},
            {'mood': 8, 'sleep': 9, 'anxiety': 3}
        ]

        insights = _analyze_general_recommendations(entries)

        # Should NOT generate sleep recommendation (good avg sleep)
        sleep_insights = [i for i in insights if i['type'] == 'sleep_recommendation']
        self.assertEqual(len(sleep_insights), 0)

    def test_anxiety_alert_high_average(self):
        """Test anxiety alert when average anxiety is high."""
        entries = [
            {'mood': 5, 'sleep': 5, 'anxiety': 8},
            {'mood': 6, 'sleep': 6, 'anxiety': 9},
            {'mood': 5, 'sleep': 5, 'anxiety': 8},
            {'mood': 6, 'sleep': 6, 'anxiety': 9},
            {'mood': 5, 'sleep': 5, 'anxiety': 7},
            {'mood': 6, 'sleep': 6, 'anxiety': 8},
            {'mood': 5, 'sleep': 5, 'anxiety': 8}
        ]

        insights = _analyze_general_recommendations(entries)

        # Should generate anxiety alert (avg > 7)
        anxiety_insights = [i for i in insights if i['type'] == 'anxiety_alert']
        self.assertEqual(len(anxiety_insights), 1)
        self.assertEqual(anxiety_insights[0]['strength'], 'medium')
        self.assertIn('тревог', anxiety_insights[0]['message'])

    def test_no_anxiety_alert_low_average(self):
        """Test no anxiety alert when average anxiety is low."""
        entries = [
            {'mood': 7, 'sleep': 7, 'anxiety': 3},
            {'mood': 8, 'sleep': 8, 'anxiety': 4},
            {'mood': 7, 'sleep': 7, 'anxiety': 3},
            {'mood': 8, 'sleep': 8, 'anxiety': 4},
            {'mood': 7, 'sleep': 7, 'anxiety': 5},
            {'mood': 8, 'sleep': 8, 'anxiety': 4},
            {'mood': 7, 'sleep': 7, 'anxiety': 3}
        ]

        insights = _analyze_general_recommendations(entries)

        # Should NOT generate anxiety alert (avg < 7)
        anxiety_insights = [i for i in insights if i['type'] == 'anxiety_alert']
        self.assertEqual(len(anxiety_insights), 0)

    def test_missing_columns_handled(self):
        """Test that missing columns don't cause errors."""
        entries = [
            {'mood': 7},  # Only mood, no sleep or anxiety
            {'mood': 8},
            {'mood': 7},
            {'mood': 8},
            {'mood': 7},
            {'mood': 8},
            {'mood': 7}
        ]

        insights = _analyze_general_recommendations(entries)

        # Should not crash, just return empty list
        self.assertIsInstance(insights, list)


if __name__ == '__main__':
    unittest.main()
