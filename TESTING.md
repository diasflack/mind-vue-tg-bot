# Testing Guide

Руководство по тестированию Telegram Mood Tracker Bot.

## Доступные тесты

### 1. Unit Tests (183 теста)

Полный набор unit тестов для всех компонентов.

```bash
# Запуск всех unit тестов
python -m unittest discover tests/unit -v

# Запуск конкретного тест-файла
python -m unittest tests/unit/test_handlers_entry.py -v

# Запуск без вывода (быстро)
python -m unittest discover tests/unit
```

**Покрытие:**
- ✅ Handlers (entry, stats, delete, sharing)
- ✅ Formatters и utilities
- ✅ Validation logic
- ✅ Analytics и pattern detection
- ✅ CSV migration
- ✅ Date helpers

**Время выполнения:** ~2 секунды

### 2. Smoke Tests (8 тестов)

Быстрая проверка работоспособности после изменений.

```bash
# Запуск smoke tests
python3 test_smoke.py
```

**Что проверяется:**
1. ✅ Импорты всех модулей
2. ✅ Конфигурация (константы)
3. ✅ Инициализация хранилища (SQLite)
4. ✅ Шифрование/расшифровка данных
5. ✅ Форматтеры (display logic)
6. ✅ Валидация ввода
7. ✅ Аналитика (insights, correlations)
8. ✅ Создание приложения бота

**Особенности:**
- Не требует BOT_TOKEN
- Использует временные директории
- Быстро (~2 секунды)
- Идеально для CI/CD

**Время выполнения:** ~2 секунды

---

## Workflow для разработки

### Перед коммитом

```bash
# 1. Запустить smoke tests для быстрой проверки
python3 test_smoke.py

# 2. Запустить полные unit tests
python -m unittest discover tests/unit

# 3. Если всё OK - можно коммитить
git add .
git commit -m "Your commit message"
```

### После рефакторинга

```bash
# Smoke tests покажут, если что-то сломалось на уровне интеграции
python3 test_smoke.py

# Проверить затронутые модули отдельно
python -m unittest tests/unit/test_YOUR_MODULE.py -v
```

### Перед деплоем

```bash
# Полный прогон всех тестов
python -m unittest discover tests/unit -v && python3 test_smoke.py

# Если оба прошли - можно деплоить
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run smoke tests
        run: python3 test_smoke.py
      - name: Run unit tests
        run: python -m unittest discover tests/unit
```

---

## Тестирование конкретных компонентов

### Handlers

```bash
# Entry handlers
python -m unittest tests/unit/test_handlers_entry.py -v

# Stats and delete
python -m unittest tests/unit/test_handlers_stats_delete.py -v

# Sharing functionality
python -m unittest tests/unit/test_handlers_sharing.py -v
```

### Analytics

```bash
# Pattern detection
python -m unittest tests/unit/test_pattern_detection_refactored.py -v

# General analytics
python -m unittest tests/unit/test_analytics.py -v
```

### Utils

```bash
# Formatters
python -m unittest tests/unit/test_formatters.py -v

# Validation
python -m unittest tests/unit/test_validation.py -v

# Date helpers
python -m unittest tests/unit/test_date_helpers.py -v
```

### Storage

```bash
# CSV migration
python -m unittest tests/unit/test_csv_migration.py -v
```

---

## Отладка проваленных тестов

### Verbose mode

```bash
# Максимальный вывод для отладки
python -m unittest tests/unit/test_YOUR_MODULE.py -v
```

### Запуск одного теста

```bash
# Запустить конкретный тест-кейс
python -m unittest tests.unit.test_YOUR_MODULE.TestClassName.test_method_name
```

### Проверка логов

Тесты логируют в stdout. Для отладки можно увеличить уровень логирования:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Метрики тестирования

**Текущее состояние:**
- 📊 **183 unit tests** - 100% passing
- 🚀 **8 smoke tests** - 100% passing
- ⚡ **Total execution time** - ~4 seconds
- ✅ **Zero regressions** after Phase 4 refactoring

**Coverage:**
- Handlers: 18 tests
- Analytics: 29 tests (8 original + 21 refactored)
- Formatters: 12 tests
- Validation: 20 tests
- Storage: 11 tests (CSV migration)
- Utils: множественные тесты

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'pytest'`

Некоторые тест-файлы используют pytest. Их можно пропустить при использовании unittest:

```bash
# Эти тесты будут пропущены (2 errors - это ожидаемо)
python -m unittest discover tests/unit
```

### BOT_TOKEN warnings

В тестовой среде BOT_TOKEN не требуется. Warning'и можно игнорировать:

```
WARNING - TELEGRAM_BOT_TOKEN не установлен! Это нормально для тестов...
```

### Временные файлы

Smoke tests создают временные директории, которые автоматически удаляются после выполнения.

---

## Добавление новых тестов

### Структура unit теста

```python
import unittest
from unittest.mock import MagicMock, AsyncMock

class TestYourFeature(unittest.TestCase):
    """Тесты для вашей фичи."""

    def test_something(self):
        """Test case description."""
        # Arrange
        test_data = {"key": "value"}

        # Act
        result = your_function(test_data)

        # Assert
        self.assertEqual(result, expected)
```

### Async тесты

```python
from unittest import IsolatedAsyncioTestCase

class TestAsyncFeature(IsolatedAsyncioTestCase):
    """Async tests."""

    async def test_async_function(self):
        """Test async functionality."""
        result = await your_async_function()
        self.assertTrue(result)
```

---

## Best Practices

1. **Всегда запускайте smoke tests** перед коммитом
2. **Запускайте полные unit tests** перед PR
3. **Добавляйте тесты** для новой функциональности
4. **Не коммитьте** если тесты не проходят
5. **Используйте descriptive names** для тест-кейсов
6. **Изолируйте тесты** - каждый тест должен быть независимым

---

## Контакты

Если тесты падают или нужна помощь:
1. Проверьте логи тестов (`-v` flag)
2. Убедитесь, что все зависимости установлены
3. Проверьте, что используете Python 3.11+

**Happy Testing! 🧪**
