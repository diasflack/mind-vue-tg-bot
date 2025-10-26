"""
Тесты для аналитики опросов (Phase 4.2).
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
def sample_numeric_questions():
    """Шаблон с числовыми вопросами."""
    return [
        {'id': 1, 'question_text': 'Уровень настроения', 'question_type': 'numeric', 'order_index': 1, 'config': '{"min": 1, "max": 10}'},
        {'id': 2, 'question_text': 'Уровень энергии', 'question_type': 'numeric', 'order_index': 2, 'config': '{"min": 1, "max": 10}'},
        {'id': 3, 'question_text': 'Уровень стресса', 'question_type': 'numeric', 'order_index': 3, 'config': '{"min": 1, "max": 10}'}
    ]


@pytest.fixture
def sample_numeric_responses():
    """Ответы на числовые вопросы."""
    base_date = datetime(2025, 10, 15)
    responses = []

    for i in range(10):
        responses.append({
            'id': i + 1,
            'chat_id': 12345,
            'template_id': 1,
            'completed_at': (base_date + timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'),
            'answers': {
                '1': str(5 + i % 3),  # Настроение: 5-7
                '2': str(6 + i % 2),  # Энергия: 6-7
                '3': str(4 - i % 3)   # Стресс: 4-2 (снижается)
            }
        })

    return responses


@pytest.fixture
def sample_choice_questions():
    """Шаблон с вопросами выбора."""
    return [
        {
            'id': 1,
            'question_text': 'Что помогло справиться?',
            'question_type': 'choice',
            'order_index': 1,
            'config': '{"type": "multiple", "options": ["Медитация", "Спорт", "Общение", "Сон"]}'
        }
    ]


@pytest.fixture
def sample_choice_responses():
    """Ответы на вопросы выбора."""
    base_date = datetime(2025, 10, 15)
    responses = []

    choices = [
        ['Медитация', 'Спорт'],
        ['Спорт'],
        ['Медитация', 'Общение'],
        ['Сон'],
        ['Медитация', 'Спорт'],
        ['Общение', 'Сон'],
        ['Медитация'],
        ['Спорт', 'Общение'],
        ['Медитация', 'Спорт', 'Сон'],
        ['Медитация']
    ]

    for i, choice in enumerate(choices):
        responses.append({
            'id': i + 1,
            'chat_id': 12345,
            'template_id': 1,
            'completed_at': (base_date + timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'),
            'answers': {
                '1': ', '.join(choice)
            }
        })

    return responses


class TestSurveyStatsCommand:
    """Тесты команды /survey_stats."""

    @pytest.mark.asyncio
    async def test_stats_no_survey_name(self, mock_update, mock_context):
        """Не указано название опроса."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = []

        await show_survey_stats(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "укажите" in call_args.lower() or "название" in call_args.lower()

    @pytest.mark.asyncio
    async def test_stats_survey_not_found(self, mock_update, mock_context):
        """Опрос не найден."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['Несуществующий опрос']

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[]):
            await show_survey_stats(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "не найден" in call_args.lower()


class TestNumericQuestionAnalytics:
    """Тесты аналитики числовых вопросов."""

    @pytest.mark.asyncio
    async def test_numeric_average_calculation(self, mock_update, mock_context, sample_numeric_questions, sample_numeric_responses):
        """Расчет среднего для числовых вопросов."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['Тестовый опрос']

        mock_template = {'id': 1, 'name': 'Тестовый опрос'}

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_analytics.get_template_questions', return_value=sample_numeric_questions):
                with patch('src.handlers.survey_analytics.get_user_survey_responses', return_value=sample_numeric_responses):
                    await show_survey_stats(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Должно быть среднее значение
        assert "средн" in call_args.lower() or "average" in call_args.lower()

    @pytest.mark.asyncio
    async def test_numeric_min_max_calculation(self, mock_update, mock_context, sample_numeric_questions, sample_numeric_responses):
        """Расчет min/max для числовых вопросов."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['Тестовый опрос']

        mock_template = {'id': 1, 'name': 'Тестовый опрос'}

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_analytics.get_template_questions', return_value=sample_numeric_questions):
                with patch('src.handlers.survey_analytics.get_user_survey_responses', return_value=sample_numeric_responses):
                    await show_survey_stats(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Должен быть диапазон (содержит min и max)
        assert "диапазон" in call_args.lower() or "range" in call_args.lower()

    @pytest.mark.asyncio
    async def test_numeric_trend_detection(self, mock_update, mock_context):
        """Определение тренда для числовых вопросов."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['Тренд опрос']

        # Растущий тренд
        trending_responses = []
        base_date = datetime(2025, 10, 10)

        for i in range(10):
            trending_responses.append({
                'id': i + 1,
                'chat_id': 12345,
                'template_id': 1,
                'completed_at': (base_date + timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'),
                'answers': {
                    '1': str(5 + i)  # Растущий тренд от 5 до 14
                }
            })

        mock_template = {'id': 1, 'name': 'Тренд опрос'}
        mock_questions = [
            {'id': 1, 'question_text': 'Уровень', 'question_type': 'numeric', 'order_index': 1, 'config': '{}'}
        ]

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_analytics.get_template_questions', return_value=mock_questions):
                with patch('src.handlers.survey_analytics.get_user_survey_responses', return_value=trending_responses):
                    await show_survey_stats(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Должен быть тренд
        assert "тренд" in call_args.lower() or "динамик" in call_args.lower()


class TestChoiceQuestionAnalytics:
    """Тесты аналитики вопросов с выбором."""

    @pytest.mark.asyncio
    async def test_choice_frequency_calculation(self, mock_update, mock_context, sample_choice_questions, sample_choice_responses):
        """Расчет частоты выбора вариантов."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['Опрос выбора']

        mock_template = {'id': 1, 'name': 'Опрос выбора'}

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_analytics.get_template_questions', return_value=sample_choice_questions):
                with patch('src.handlers.survey_analytics.get_user_survey_responses', return_value=sample_choice_responses):
                    await show_survey_stats(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Должны быть варианты и их частоты
        # Медитация должна быть самой популярной (встречается 6 раз)
        assert "медитация" in call_args.lower()
        assert "спорт" in call_args.lower()

    @pytest.mark.asyncio
    async def test_choice_percentage_calculation(self, mock_update, mock_context, sample_choice_questions, sample_choice_responses):
        """Расчет процентов для вариантов выбора."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['Опрос выбора']

        mock_template = {'id': 1, 'name': 'Опрос выбора'}

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_analytics.get_template_questions', return_value=sample_choice_questions):
                with patch('src.handlers.survey_analytics.get_user_survey_responses', return_value=sample_choice_responses):
                    await show_survey_stats(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Должны быть проценты
        assert "%" in call_args


class TestCBTAnalytics:
    """Тесты специальной аналитики для КПТ дневника."""

    @pytest.mark.asyncio
    async def test_cbt_before_after_comparison(self, mock_update, mock_context):
        """Сравнение 'до' и 'после' для КПТ."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['КПТ дневник']

        # Вопросы КПТ с оценками до/после
        cbt_questions = [
            {'id': 1, 'question_text': 'Интенсивность негативных мыслей (до)', 'question_type': 'scale', 'order_index': 1, 'config': '{"min": 0, "max": 10, "step": 1}'},
            {'id': 2, 'question_text': 'Интенсивность негативных мыслей (после)', 'question_type': 'scale', 'order_index': 2, 'config': '{"min": 0, "max": 10, "step": 1}'}
        ]

        cbt_responses = []
        base_date = datetime(2025, 10, 10)

        for i in range(5):
            cbt_responses.append({
                'id': i + 1,
                'chat_id': 12345,
                'template_id': 1,
                'completed_at': (base_date + timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'),
                'answers': {
                    '1': str(8 - i),  # До: снижается 8->4
                    '2': str(4 - i // 2)  # После: снижается медленнее 4->2
                }
            })

        mock_template = {'id': 1, 'name': 'КПТ дневник'}

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_analytics.get_template_questions', return_value=cbt_questions):
                with patch('src.handlers.survey_analytics.get_user_survey_responses', return_value=cbt_responses):
                    await show_survey_stats(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Должно быть сравнение до/после
        assert "до" in call_args.lower() and "после" in call_args.lower()


class TestAddictionAnalytics:
    """Тесты специальной аналитики для дневника зависимости."""

    @pytest.mark.asyncio
    async def test_craving_trend_analysis(self, mock_update, mock_context):
        """Анализ тренда тяги."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['Дневник зависимости']

        addiction_questions = [
            {'id': 1, 'question_text': 'Уровень тяги', 'question_type': 'scale', 'order_index': 1, 'config': '{"min": 0, "max": 10, "step": 1}'},
            {'id': 2, 'question_text': 'Были ли срывы?', 'question_type': 'yes_no', 'order_index': 2, 'config': '{}'}
        ]

        addiction_responses = []
        base_date = datetime(2025, 10, 1)

        for i in range(10):
            addiction_responses.append({
                'id': i + 1,
                'chat_id': 12345,
                'template_id': 1,
                'completed_at': (base_date + timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'),
                'answers': {
                    '1': str(max(1, 8 - i)),  # Снижающаяся тяга
                    '2': 'нет' if i > 3 else 'да'  # Срывы только в первые дни
                }
            })

        mock_template = {'id': 1, 'name': 'Дневник зависимости'}

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_analytics.get_template_questions', return_value=addiction_questions):
                with patch('src.handlers.survey_analytics.get_user_survey_responses', return_value=addiction_responses):
                    await show_survey_stats(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]

        # Должен быть анализ тяги и срывов
        assert "тяг" in call_args.lower() or "срыв" in call_args.lower()


class TestAnalyticsWithNoData:
    """Тесты аналитики без данных."""

    @pytest.mark.asyncio
    async def test_no_responses_message(self, mock_update, mock_context):
        """Сообщение когда нет ответов."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['Пустой опрос']

        mock_template = {'id': 1, 'name': 'Пустой опрос'}
        mock_questions = [
            {'id': 1, 'question_text': 'Вопрос', 'question_type': 'text', 'order_index': 1, 'config': '{}'}
        ]

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_analytics.get_template_questions', return_value=mock_questions):
                with patch('src.handlers.survey_analytics.get_user_survey_responses', return_value=[]):
                    await show_survey_stats(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "нет ответов" in call_args.lower() or "нет данных" in call_args.lower()


class TestAnalyticsPeriodFiltering:
    """Тесты фильтрации по периодам."""

    @pytest.mark.asyncio
    async def test_last_7_days_filter(self, mock_update, mock_context, sample_numeric_questions, sample_numeric_responses):
        """Фильтр последние 7 дней."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['Опрос', '--period', '7']

        mock_template = {'id': 1, 'name': 'Опрос'}

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_analytics.get_template_questions', return_value=sample_numeric_questions):
                with patch('src.handlers.survey_analytics.get_user_survey_responses', return_value=sample_numeric_responses):
                    await show_survey_stats(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_last_30_days_filter(self, mock_update, mock_context, sample_numeric_questions, sample_numeric_responses):
        """Фильтр последние 30 дней."""
        from src.handlers.survey_analytics import show_survey_stats

        mock_context.args = ['Опрос', '--period', '30']

        mock_template = {'id': 1, 'name': 'Опрос'}

        with patch('src.handlers.survey_analytics.get_available_templates', return_value=[mock_template]):
            with patch('src.handlers.survey_analytics.get_template_questions', return_value=sample_numeric_questions):
                with patch('src.handlers.survey_analytics.get_user_survey_responses', return_value=sample_numeric_responses):
                    await show_survey_stats(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
