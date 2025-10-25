"""
Тесты для аналитики впечатлений (Phase 4.1).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update


@pytest.fixture
def mock_update():
    """Создает mock объект Update."""
    update = MagicMock(spec=Update)
    update.effective_chat.id = 12345
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Создает mock объект CallbackContext."""
    context = MagicMock()
    context.user_data = {}
    context.args = []
    return context


@pytest.fixture
def sample_impressions():
    """Создает набор тестовых впечатлений для аналитики."""
    base_time = datetime(2025, 10, 20, 10, 0, 0)

    impressions = [
        {
            'id': 1,
            'chat_id': 12345,
            'text': 'Хорошее утро',
            'category': 'positive',
            'intensity': 8,
            'created_at': base_time.strftime('%Y-%m-%d %H:%M:%S'),
            'tags': ['работа', 'энергия']
        },
        {
            'id': 2,
            'chat_id': 12345,
            'text': 'Стресс на работе',
            'category': 'negative',
            'intensity': 6,
            'created_at': (base_time + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
            'tags': ['работа', 'стресс']
        },
        {
            'id': 3,
            'chat_id': 12345,
            'text': 'Приятный вечер',
            'category': 'positive',
            'intensity': 9,
            'created_at': (base_time + timedelta(hours=10)).strftime('%Y-%m-%d %H:%M:%S'),
            'tags': ['отдых', 'семья']
        },
        {
            'id': 4,
            'chat_id': 12345,
            'text': 'Нейтральное событие',
            'category': 'neutral',
            'intensity': 5,
            'created_at': (base_time + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'tags': ['работа']
        },
        {
            'id': 5,
            'chat_id': 12345,
            'text': 'Радость',
            'category': 'positive',
            'intensity': 10,
            'created_at': (base_time + timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
            'tags': ['семья', 'радость']
        },
    ]

    return impressions


class TestImpressionsByCategoryStats:
    """Тесты статистики по категориям."""

    @pytest.mark.asyncio
    async def test_category_stats_with_data(self, mock_update, mock_context, sample_impressions):
        """Статистика по категориям с данными."""
        from src.handlers.impression_analytics import show_impression_analytics

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]

        # Проверяем наличие категорий
        assert "positive" in call_args.lower() or "позитивн" in call_args.lower()
        assert "negative" in call_args.lower() or "негативн" in call_args.lower()
        assert "neutral" in call_args.lower() or "нейтральн" in call_args.lower()

        # Проверяем наличие подсчетов (3 positive, 1 negative, 1 neutral)
        assert "3" in call_args  # 3 positive impressions

    @pytest.mark.asyncio
    async def test_category_stats_empty(self, mock_update, mock_context):
        """Статистика по категориям без данных."""
        from src.handlers.impression_analytics import show_impression_analytics

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=[]):
            await show_impression_analytics(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "нет данных" in call_args.lower() or "нет впечатлений" in call_args.lower()


class TestImpressionsByTagStats:
    """Тесты статистики по тегам."""

    @pytest.mark.asyncio
    async def test_tag_frequency(self, mock_update, mock_context, sample_impressions):
        """Частота использования тегов."""
        from src.handlers.impression_analytics import show_impression_analytics

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Проверяем наличие тегов
        assert "работа" in call_args.lower() or "tags" in call_args.lower()

        # Тег "работа" встречается 3 раза
        # Тег "семья" встречается 2 раза


class TestImpressionsIntensityAverage:
    """Тесты средней интенсивности."""

    @pytest.mark.asyncio
    async def test_average_intensity_calculation(self, mock_update, mock_context, sample_impressions):
        """Расчет средней интенсивности."""
        from src.handlers.impression_analytics import show_impression_analytics

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Средняя интенсивность: (8+6+9+5+10)/5 = 7.6
        assert "средн" in call_args.lower() or "average" in call_args.lower()
        assert "7" in call_args or "8" in call_args  # Примерно 7.6

    @pytest.mark.asyncio
    async def test_intensity_by_category(self, mock_update, mock_context, sample_impressions):
        """Средняя интенсивность по категориям."""
        from src.handlers.impression_analytics import show_impression_analytics

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Positive: (8+9+10)/3 = 9.0
        # Negative: 6
        # Neutral: 5
        assert "интенсивн" in call_args.lower() or "intensity" in call_args.lower()


class TestImpressionsByTimeOfDay:
    """Тесты распределения по времени суток."""

    @pytest.mark.asyncio
    async def test_time_of_day_distribution(self, mock_update, mock_context, sample_impressions):
        """Распределение по времени суток."""
        from src.handlers.impression_analytics import show_impression_analytics

        mock_context.args = ['--detailed']  # Запрос детальной статистики

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Проверяем наличие временных интервалов
        # Утро (6-12): 10:00 - 1 впечатление
        # День (12-18): 15:00 - 1 впечатление
        # Вечер (18-24): 20:00 - 1 впечатление
        assert "утр" in call_args.lower() or "день" in call_args.lower() or "вечер" in call_args.lower()


class TestImpressionsByDayOfWeek:
    """Тесты распределения по дням недели."""

    @pytest.mark.asyncio
    async def test_day_of_week_distribution(self, mock_update, mock_context):
        """Распределение по дням недели."""
        from src.handlers.impression_analytics import show_impression_analytics

        # Создаем впечатления для разных дней недели
        impressions_by_weekday = []
        base_date = datetime(2025, 10, 20)  # Понедельник

        for i in range(7):
            impressions_by_weekday.append({
                'id': i + 1,
                'chat_id': 12345,
                'text': f'Impression {i}',
                'category': 'positive',
                'intensity': 7,
                'created_at': (base_date + timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'),
                'tags': []
            })

        mock_context.args = ['--detailed']

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=impressions_by_weekday):
            await show_impression_analytics(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Проверяем наличие дней недели
        # Должно быть упоминание дней (пн, вт, ср, чт, пт, сб, вс)
        assert "пн" in call_args.lower() or "monday" in call_args.lower() or "день" in call_args.lower()


class TestImpressionsTrend:
    """Тесты трендов."""

    @pytest.mark.asyncio
    async def test_trend_calculation(self, mock_update, mock_context):
        """Расчет тренда интенсивности."""
        from src.handlers.impression_analytics import show_impression_analytics

        # Создаем тренд с растущей интенсивностью
        base_date = datetime(2025, 10, 15)
        trending_impressions = []

        for i in range(10):
            trending_impressions.append({
                'id': i + 1,
                'chat_id': 12345,
                'text': f'Impression {i}',
                'category': 'positive',
                'intensity': 5 + i,  # Растущий тренд от 5 до 14
                'created_at': (base_date + timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'),
                'tags': []
            })

        mock_context.args = ['--period', '10']  # За последние 10 дней

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=trending_impressions):
            await show_impression_analytics(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Проверяем наличие информации о тренде
        assert "тренд" in call_args.lower() or "динамик" in call_args.lower() or "trend" in call_args.lower()

    @pytest.mark.asyncio
    async def test_trend_by_category(self, mock_update, mock_context, sample_impressions):
        """Тренд по категориям."""
        from src.handlers.impression_analytics import show_impression_analytics

        mock_context.args = ['--category', 'positive']

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]

        # Фильтрация по категории positive
        assert "positive" in call_args.lower() or "позитивн" in call_args.lower()


class TestAnalyticsPeriodFiltering:
    """Тесты фильтрации по периодам."""

    @pytest.mark.asyncio
    async def test_last_7_days(self, mock_update, mock_context, sample_impressions):
        """Аналитика за последние 7 дней."""
        from src.handlers.impression_analytics import show_impression_analytics

        mock_context.args = ['--period', '7']

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_last_30_days(self, mock_update, mock_context, sample_impressions):
        """Аналитика за последние 30 дней."""
        from src.handlers.impression_analytics import show_impression_analytics

        mock_context.args = ['--period', '30']

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_date_range(self, mock_update, mock_context, sample_impressions):
        """Аналитика за произвольный период."""
        from src.handlers.impression_analytics import show_impression_analytics

        mock_context.args = ['--from', '2025-10-01', '--to', '2025-10-31']

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()


class TestAnalyticsFormatting:
    """Тесты форматирования вывода."""

    @pytest.mark.asyncio
    async def test_output_is_readable(self, mock_update, mock_context, sample_impressions):
        """Вывод читаемый и структурированный."""
        from src.handlers.impression_analytics import show_impression_analytics

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Проверяем наличие структурных элементов
        assert len(call_args) > 50  # Не пустой

        # Проверяем parse_mode=Markdown
        assert mock_update.message.reply_text.call_args[1].get('parse_mode') == 'Markdown'

    @pytest.mark.asyncio
    async def test_includes_summary_statistics(self, mock_update, mock_context, sample_impressions):
        """Включает итоговую статистику."""
        from src.handlers.impression_analytics import show_impression_analytics

        with patch('src.handlers.impression_analytics.get_user_impressions', return_value=sample_impressions):
            await show_impression_analytics(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Должны быть: общее количество, средняя интенсивность, категории
        assert "всего" in call_args.lower() or "total" in call_args.lower()
        assert "средн" in call_args.lower() or "average" in call_args.lower()
