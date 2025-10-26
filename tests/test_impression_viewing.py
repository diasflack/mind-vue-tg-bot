"""
Тесты для просмотра впечатлений.

TDD Phase 1.5: Эти тесты должны провалиться до реализации.
"""

import unittest
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestImpressionViewing(unittest.IsolatedAsyncioTestCase):
    """Test impression viewing commands."""

    def setUp(self):
        """Set up test fixtures."""
        self.update = MagicMock()
        self.context = MagicMock()

        self.test_chat_id = 123456789
        self.test_username = "test_user"
        self.test_first_name = "Test"

        self.update.effective_chat.id = self.test_chat_id
        self.update.effective_user.username = self.test_username
        self.update.effective_user.first_name = self.test_first_name

        self.update.message = MagicMock()
        self.update.message.reply_text = AsyncMock()
        self.update.effective_message = self.update.message

    @patch('src.handlers.impression_viewing.get_user_impressions')
    @patch('src.handlers.impression_viewing._get_db_connection')
    async def test_show_today_impressions_with_data(self, mock_db, mock_get_impressions):
        """Тест: показать впечатления за сегодня (есть данные)."""
        from src.handlers.impression_viewing import show_today_impressions

        mock_conn = MagicMock()
        mock_db.return_value = mock_conn

        # Mock impressions для сегодня
        today = datetime.now().strftime('%Y-%m-%d')
        mock_impressions = [
            {
                'id': 1,
                'chat_id': self.test_chat_id,
                'impression_text': "Хочется выпить",
                'impression_date': today,
                'impression_time': "18:45:00",
                'category': "craving",
                'intensity': 7,
                'tags': [
                    {'tag_name': 'алкоголь'},
                    {'tag_name': 'стресс'}
                ]
            },
            {
                'id': 2,
                'chat_id': self.test_chat_id,
                'impression_text': "Мне хорошо",
                'impression_date': today,
                'impression_time': "12:00:00",
                'category': "emotion",
                'intensity': 9,
                'tags': []
            }
        ]
        mock_get_impressions.return_value = mock_impressions

        await show_today_impressions(self.update, self.context)

        # Проверяем что get_user_impressions вызван с правильными параметрами
        mock_get_impressions.assert_called_once()
        call_args = mock_get_impressions.call_args
        self.assertEqual(call_args[0][1], self.test_chat_id)  # chat_id
        self.assertEqual(call_args[1]['date'], today)  # date filter
        self.assertTrue(call_args[1]['include_tags'])  # include_tags

        # Проверяем что сообщение отправлено
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]

        # Проверяем содержание сообщения
        self.assertIn("Хочется выпить", message_text)
        self.assertIn("Мне хорошо", message_text)
        self.assertIn("7/10", message_text)  # intensity
        self.assertIn("#алкоголь", message_text)  # tags
        self.assertIn("#стресс", message_text)

    @patch('src.handlers.impression_viewing.get_user_impressions')
    @patch('src.handlers.impression_viewing._get_db_connection')
    async def test_show_today_impressions_empty(self, mock_db, mock_get_impressions):
        """Тест: показать впечатления за сегодня (пусто)."""
        from src.handlers.impression_viewing import show_today_impressions

        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_get_impressions.return_value = []

        await show_today_impressions(self.update, self.context)

        # Проверяем что сообщение о пустом списке отправлено
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]

        self.assertIn("нет впечатлений", message_text.lower())

    @patch('src.handlers.impression_viewing.get_user_impressions')
    @patch('src.handlers.impression_viewing._get_db_connection')
    async def test_show_impressions_history_all(self, mock_db, mock_get_impressions):
        """Тест: показать всю историю впечатлений."""
        from src.handlers.impression_viewing import show_impressions_history

        mock_conn = MagicMock()
        mock_db.return_value = mock_conn

        mock_impressions = [
            {
                'id': 1,
                'chat_id': self.test_chat_id,
                'impression_text': "Впечатление 1",
                'impression_date': "2025-10-24",
                'impression_time': "18:45:00",
                'category': "craving",
                'intensity': 7,
                'tags': []
            }
        ]
        mock_get_impressions.return_value = mock_impressions

        await show_impressions_history(self.update, self.context)

        # Проверяем что get_user_impressions вызван без date фильтра
        mock_get_impressions.assert_called_once()
        call_args = mock_get_impressions.call_args
        self.assertNotIn('date', call_args[1])

        # Проверяем что сообщение отправлено
        self.update.message.reply_text.assert_called()

    @patch('src.handlers.impression_viewing.get_user_impressions')
    @patch('src.handlers.impression_viewing._get_db_connection')
    async def test_show_impressions_with_pagination(self, mock_db, mock_get_impressions):
        """Тест: пагинация для большого количества впечатлений."""
        from src.handlers.impression_viewing import show_today_impressions

        mock_conn = MagicMock()
        mock_db.return_value = mock_conn

        # Создаем 15 впечатлений (больше чем может поместиться в одно сообщение)
        today = datetime.now().strftime('%Y-%m-%d')
        mock_impressions = []
        for i in range(15):
            mock_impressions.append({
                'id': i,
                'chat_id': self.test_chat_id,
                'impression_text': f"Впечатление {i}",
                'impression_date': today,
                'impression_time': f"{10+i}:00:00",
                'category': None,
                'intensity': None,
                'tags': []
            })

        mock_get_impressions.return_value = mock_impressions

        await show_today_impressions(self.update, self.context)

        # Проверяем что было несколько вызовов reply_text (из-за пагинации)
        # или одно сообщение с ограничением
        self.assertTrue(self.update.message.reply_text.called)

    def test_format_impression_text(self):
        """Тест: форматирование впечатления для вывода."""
        from src.handlers.impression_viewing import _format_impression

        impression = {
            'id': 1,
            'impression_text': "Хочется выпить",
            'impression_date': "2025-10-24",
            'impression_time': "18:45:00",
            'category': "craving",
            'intensity': 7,
            'tags': [
                {'tag_name': 'алкоголь'},
                {'tag_name': 'стресс'}
            ]
        }

        result = _format_impression(impression)

        # Проверяем что все элементы присутствуют
        self.assertIn("Хочется выпить", result)
        self.assertIn("18:45", result)  # время без секунд
        self.assertIn("7/10", result)  # intensity
        self.assertIn("#алкоголь", result)
        self.assertIn("#стресс", result)
        self.assertIn("Влечение", result)  # категория по-русски

    def test_format_impression_minimal(self):
        """Тест: форматирование впечатления без опциональных полей."""
        from src.handlers.impression_viewing import _format_impression

        impression = {
            'id': 1,
            'impression_text': "Просто текст",
            'impression_date': "2025-10-24",
            'impression_time': "12:00:00",
            'category': None,
            'intensity': None,
            'tags': []
        }

        result = _format_impression(impression)

        # Проверяем базовые элементы
        self.assertIn("Просто текст", result)
        self.assertIn("12:00", result)
        # Не должно быть intensity и tags
        self.assertNotIn("/10", result)
        self.assertNotIn("#", result)

    def test_commands_registered(self):
        """Тест: команды зарегистрированы в модуле."""
        from src.handlers import impression_viewing

        # Проверяем что функции существуют
        self.assertTrue(hasattr(impression_viewing, 'show_today_impressions'))
        self.assertTrue(hasattr(impression_viewing, 'show_impressions_history'))

    @patch('src.handlers.impression_viewing.get_user_impressions')
    @patch('src.handlers.impression_viewing._get_db_connection')
    async def test_impressions_sorted_by_time_desc(self, mock_db, mock_get_impressions):
        """Тест: впечатления отображаются от новых к старым."""
        from src.handlers.impression_viewing import show_today_impressions

        mock_conn = MagicMock()
        mock_db.return_value = mock_conn

        today = datetime.now().strftime('%Y-%m-%d')
        # Впечатления уже отсортированы от новых к старым (как из БД)
        mock_impressions = [
            {
                'id': 2,
                'chat_id': self.test_chat_id,
                'impression_text': "Новое",
                'impression_date': today,
                'impression_time': "20:00:00",
                'category': None,
                'intensity': None,
                'tags': []
            },
            {
                'id': 1,
                'chat_id': self.test_chat_id,
                'impression_text': "Старое",
                'impression_date': today,
                'impression_time': "10:00:00",
                'category': None,
                'intensity': None,
                'tags': []
            }
        ]
        mock_get_impressions.return_value = mock_impressions

        await show_today_impressions(self.update, self.context)

        # Проверяем что сообщение содержит оба впечатления
        call_args = self.update.message.reply_text.call_args
        message_text = call_args[0][0]

        # Проверяем что "Новое" идет перед "Старое" в тексте
        index_new = message_text.find("Новое")
        index_old = message_text.find("Старое")
        self.assertLess(index_new, index_old, "Новые впечатления должны быть выше")


if __name__ == '__main__':
    unittest.main()
