#!/usr/bin/env python3
"""
Smoke test для проверки работоспособности бота после изменений.
Проверяет, что все компоненты могут инициализироваться без ошибок.
"""

import sys
import logging
import tempfile
import os

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def test_imports():
    """Проверка, что все основные модули импортируются без ошибок."""
    logger.info("🔍 Тест 1: Проверка импортов...")

    try:
        # Основные модули
        from src import bot, config
        from src.data import storage, encryption
        from src.handlers import entry, basic, stats, delete, notifications
        from src.utils import formatters, date_helpers, validation
        from src.analytics import pattern_detection
        # Note: analytics - это папка, не импортируем как модуль

        logger.info("✅ Все модули импортируются корректно")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        return False


def test_config_initialization():
    """Проверка инициализации конфигурации."""
    logger.info("🔍 Тест 2: Проверка конфигурации...")

    try:
        import src.config as config
        import os

        # Проверяем, что модуль конфигурации импортируется
        # В тестовой среде BOT_TOKEN может отсутствовать - это нормально
        if not os.environ.get('TELEGRAM_BOT_TOKEN'):
            logger.warning("⚠️ BOT_TOKEN отсутствует (ожидаемо в тестовой среде)")

        # Проверяем, что основные константы доступны
        if hasattr(config, 'DATA_FOLDER') and hasattr(config, 'MOOD'):
            logger.info("✅ Конфигурация загружена корректно (константы доступны)")
            return True
        else:
            logger.error("❌ Конфигурация не содержит необходимые константы")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации конфигурации: {e}")
        return False


def test_storage_initialization():
    """Проверка инициализации хранилища данных."""
    logger.info("🔍 Тест 3: Проверка инициализации хранилища...")

    # Создаем временную директорию для тестовой БД
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            import src.data.storage as storage

            # Переключаем на тестовую директорию
            original_data_folder = storage.DATA_FOLDER
            original_db_file = storage.DB_FILE

            storage.DATA_FOLDER = temp_dir
            storage.DB_FILE = os.path.join(temp_dir, "test_mood_tracker.db")

            # Инициализация хранилища
            storage.initialize_storage()

            # Проверка, что БД создана
            if os.path.exists(storage.DB_FILE):
                logger.info("✅ Хранилище инициализировано корректно")
                result = True
            else:
                logger.error("❌ БД не создана")
                result = False

            # Восстановление оригинальных путей
            storage.DATA_FOLDER = original_data_folder
            storage.DB_FILE = original_db_file

            return result
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации хранилища: {e}")
            return False


def test_encryption():
    """Проверка работы модуля шифрования."""
    logger.info("🔍 Тест 4: Проверка шифрования...")

    try:
        from src.data.encryption import encrypt_data, decrypt_data
        import src.config as config

        # Инициализируем соли если они не установлены
        if not config.SECRET_SALT or not config.SYSTEM_SALT:
            # Создаем временные соли для тестирования
            config.SECRET_SALT = b'test_secret_salt_for_testing_purposes_only'
            config.SYSTEM_SALT = b'test_system_salt_for_testing_purposes_only'
            logger.info("Используем временные соли для тестирования")

        test_data = {
            'mood': 7,
            'sleep': 8,
            'comment': 'Test comment',
            'date': '2025-01-20'
        }

        # Шифрование
        encrypted = encrypt_data(test_data, 12345)

        # Расшифровка
        decrypted = decrypt_data(encrypted, 12345)

        # Проверка
        if decrypted['mood'] == test_data['mood'] and decrypted['comment'] == test_data['comment']:
            logger.info("✅ Шифрование работает корректно")
            return True
        else:
            logger.error("❌ Данные после расшифровки не совпадают")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка шифрования: {e}")
        return False


def test_formatters():
    """Проверка работы форматтеров."""
    logger.info("🔍 Тест 5: Проверка форматтеров...")

    try:
        from src.utils.formatters import format_entry_summary, format_date

        # Полный набор полей для записи
        test_entry = {
            'date': '2025-01-20',
            'mood': 7,
            'sleep': 8,
            'balance': 6,
            'mania': 4,
            'depression': 2,
            'anxiety': 3,
            'irritability': 3,
            'productivity': 7,
            'sociability': 6,
            'comment': 'Test'
        }

        # Форматирование
        summary = format_entry_summary(test_entry)
        date_str = format_date('2025-01-20')

        if summary and '7' in summary and date_str:
            logger.info("✅ Форматтеры работают корректно")
            return True
        else:
            logger.error("❌ Некорректный результат форматирования")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка форматтеров: {e}")
        return False


def test_validation():
    """Проверка работы валидации."""
    logger.info("🔍 Тест 6: Проверка валидации...")

    try:
        from src.utils.validation import validate_numeric_input, validate_comment

        # Тест валидации числового ввода
        is_valid, value = validate_numeric_input("7", min_val=1, max_val=10)
        if not (is_valid and value == 7):
            logger.error("❌ Валидация числового ввода не работает")
            return False

        # Тест валидации комментария
        comment = validate_comment("Test comment")
        if not comment:
            logger.error("❌ Валидация комментария не работает")
            return False

        logger.info("✅ Валидация работает корректно")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка валидации: {e}")
        return False


def test_analytics():
    """Проверка работы аналитики."""
    logger.info("🔍 Тест 7: Проверка аналитики...")

    try:
        from src.analytics.pattern_detection import generate_insights, analyze_correlations

        # Создаем тестовые данные (минимум 7 записей) с полным набором полей
        test_entries = [
            {
                'mood': 7 + (i % 3),
                'sleep': 8,
                'balance': 6,
                'mania': 4,
                'depression': 2,
                'anxiety': 3,
                'irritability': 3,
                'productivity': 7,
                'sociability': 6,
                'date': f'2025-01-{i+1:02d}'
            }
            for i in range(10)
        ]

        # Генерация инсайтов
        insights = generate_insights(test_entries)

        # Анализ корреляций
        correlations = analyze_correlations(test_entries)

        if insights['status'] == 'success' and correlations['status'] == 'success':
            logger.info("✅ Аналитика работает корректно")
            return True
        else:
            logger.error(f"❌ Аналитика вернула ошибку: {insights.get('message', 'Unknown')}")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка аналитики: {e}")
        return False


def test_bot_application_creation():
    """Проверка создания приложения бота (без запуска)."""
    logger.info("🔍 Тест 8: Проверка создания приложения бота...")

    try:
        from src.bot import create_application

        # Попытка создать приложение (требует BOT_TOKEN)
        # Это может упасть, если токен не установлен, но это ожидаемо в тестовом окружении
        app = create_application()

        if app:
            logger.info("✅ Приложение бота создано успешно")
            return True
        else:
            logger.warning("⚠️ Приложение не создано (возможно, нет BOT_TOKEN)")
            return True  # Это ожидаемо в тестовом окружении
    except Exception as e:
        # Если ошибка связана с отсутствием токена, это нормально
        if "BOT_TOKEN" in str(e) or "token" in str(e).lower():
            logger.warning("⚠️ BOT_TOKEN не установлен (ожидаемо в тестовом окружении)")
            return True
        else:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            return False


def run_smoke_tests():
    """Запускает все smoke tests."""
    logger.info("=" * 60)
    logger.info("🚀 Запуск smoke tests для проверки работоспособности бота")
    logger.info("=" * 60)

    tests = [
        ("Импорты", test_imports),
        ("Конфигурация", test_config_initialization),
        ("Хранилище", test_storage_initialization),
        ("Шифрование", test_encryption),
        ("Форматтеры", test_formatters),
        ("Валидация", test_validation),
        ("Аналитика", test_analytics),
        ("Создание приложения", test_bot_application_creation),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в тесте '{name}': {e}")
            results.append((name, False))
        logger.info("")  # Пустая строка для разделения

    # Итоговый отчет
    logger.info("=" * 60)
    logger.info("📊 ИТОГОВЫЙ ОТЧЕТ")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{name:30} {status}")

    logger.info("=" * 60)
    logger.info(f"Результат: {passed}/{total} тестов прошли успешно")
    logger.info("=" * 60)

    if passed == total:
        logger.info("🎉 Все smoke tests прошли успешно! Бот готов к работе.")
        return 0
    else:
        logger.error(f"⚠️ {total - passed} тест(ов) провалились. Требуется внимание.")
        return 1


if __name__ == '__main__':
    sys.exit(run_smoke_tests())
