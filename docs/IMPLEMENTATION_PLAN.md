# План реализации: Ежедневные впечатления и настраиваемые опросы

## Методология: Test-Driven Development (TDD)

Для каждого этапа:
1. ✍️ **Написать тесты** (которые провалятся)
2. ▶️ **Запустить тесты** (убедиться что провалились)
3. 💻 **Написать код** (реализация)
4. ✅ **Запустить тесты** (убедиться что прошли)
5. ♻️ **Рефакторинг** (при необходимости)

---

## Phase 1: Впечатления - Базовая функциональность

**Цель:** Добавить возможность быстрой фиксации текущего состояния

### 1.1 Миграция базы данных

**Тесты:**
- `tests/test_impressions_migration.py`
  - `test_impressions_table_created()`
  - `test_impression_tags_table_created()`
  - `test_impression_tag_relations_table_created()`
  - `test_indexes_created()`

**Реализация:**
- `src/data/migrations/001_add_impressions_tables.py`
  - Создание таблиц impressions, impression_tags, impression_tag_relations
  - Создание индексов
  - Функция миграции с проверкой существующих таблиц

**Критерии приемки:**
- ✅ Таблицы созданы в SQLite
- ✅ Индексы работают
- ✅ Foreign keys настроены корректно
- ✅ Миграция идемпотентна (можно запустить несколько раз)

---

### 1.2 Модели данных для впечатлений

**Тесты:**
- `tests/test_impressions_models.py`
  - `test_impression_creation()`
  - `test_impression_validation()`
  - `test_impression_to_dict()`
  - `test_impression_from_dict()`
  - `test_impression_tag_creation()`

**Реализация:**
- `src/data/models.py` (расширение)
  - `class Impression` - модель впечатления
  - `class ImpressionTag` - модель тега
  - Валидация полей

**Критерии приемки:**
- ✅ Модели корректно сериализуются/десериализуются
- ✅ Валидация работает (категории, интенсивность 1-10)
- ✅ TypedDict для совместимости с шифрованием

---

### 1.3 Хранилище впечатлений

**Тесты:**
- `tests/test_impressions_storage.py`
  - `test_save_impression()`
  - `test_get_impressions_by_date()`
  - `test_get_impressions_by_date_range()`
  - `test_get_impressions_with_tags()`
  - `test_update_impression()`
  - `test_delete_impression()`
  - `test_create_tag()`
  - `test_get_user_tags()`
  - `test_attach_tag_to_impression()`
  - `test_get_impressions_by_category()`

**Реализация:**
- `src/data/impressions_storage.py`
  - `save_impression()` - сохранение впечатления (без шифрования пока)
  - `get_user_impressions()` - получение с фильтрами
  - `delete_impression()` - удаление
  - `create_tag()` - создание тега
  - `get_user_tags()` - получение тегов пользователя
  - `attach_tags_to_impression()` - привязка тегов
  - `get_impressions_by_category()` - фильтрация по категории

**Критерии приемки:**
- ✅ CRUD операции работают
- ✅ Фильтрация по дате/категории/тегам
- ✅ Теги корректно привязываются
- ✅ Кеширование (опционально)

---

### 1.4 Обработчик добавления впечатления

**Тесты:**
- `tests/test_impression_handlers.py`
  - `test_start_impression_command()`
  - `test_impression_text_input()`
  - `test_impression_intensity_input()`
  - `test_impression_intensity_skip()`
  - `test_impression_category_selection()`
  - `test_impression_category_skip()`
  - `test_impression_tags_input()`
  - `test_impression_tags_skip()`
  - `test_impression_saved_successfully()`
  - `test_impression_cancel()`
  - `test_impression_link_to_entry()`

**Реализация:**
- `src/handlers/impression_handlers.py`
  - `start_impression()` - начало диалога /impression
  - `handle_impression_text()` - получение текста
  - `handle_impression_intensity()` - получение интенсивности
  - `handle_impression_category()` - выбор категории
  - `handle_impression_tags()` - добавление тегов
  - `finish_impression()` - сохранение и подтверждение
  - `link_to_entry()` - привязка к основной записи дня
  - ConversationHandler для управления диалогом

**Критерии приемки:**
- ✅ Диалог проходит все этапы
- ✅ Пропуск необязательных полей работает (/skip)
- ✅ Отмена работает (/cancel)
- ✅ Впечатление сохраняется в БД
- ✅ Клавиатуры отображаются корректно

---

### 1.5 Просмотр впечатлений

**Тесты:**
- `tests/test_impression_viewing.py`
  - `test_view_today_impressions()`
  - `test_view_today_impressions_empty()`
  - `test_view_impressions_history()`
  - `test_view_impressions_by_category()`
  - `test_view_impressions_by_tag()`
  - `test_view_impressions_pagination()`

**Реализация:**
- `src/handlers/impression_handlers.py` (расширение)
  - `show_today_impressions()` - /impressions
  - `show_impressions_history()` - /impressions_history с фильтрами
  - Форматирование вывода впечатлений
  - Пагинация для больших списков

**Критерии приемки:**
- ✅ Отображаются все поля впечатления
- ✅ Форматирование читаемое
- ✅ Фильтры работают
- ✅ Пагинация для >10 записей

---

## Phase 2: Система опросов - Базовая функциональность

**Цель:** Реализовать систему шаблонов опросов и ответов

### 2.1 Миграция базы данных для опросов

**Тесты:**
- `tests/test_surveys_migration.py`
  - `test_survey_templates_table_created()`
  - `test_survey_questions_table_created()`
  - `test_survey_responses_table_created()`
  - `test_user_survey_preferences_table_created()`
  - `test_cascade_delete_works()`

**Реализация:**
- `src/data/migrations/002_add_surveys_tables.py`
  - Создание таблиц survey_templates, survey_questions, survey_responses, user_survey_preferences
  - Индексы и foreign keys
  - Функция миграции

**Критерии приемки:**
- ✅ Таблицы созданы
- ✅ CASCADE DELETE работает
- ✅ Миграция идемпотентна

---

### 2.2 Модели данных для опросов

**Тесты:**
- `tests/test_surveys_models.py`
  - `test_survey_template_creation()`
  - `test_survey_question_creation()`
  - `test_question_validation_by_type()`
  - `test_survey_response_creation()`
  - `test_config_json_parsing()`

**Реализация:**
- `src/data/models.py` (расширение)
  - `class SurveyTemplate`
  - `class SurveyQuestion`
  - `class SurveyResponse`
  - Валидация типов вопросов

**Критерии приемки:**
- ✅ Модели корректно работают
- ✅ JSON config парсится
- ✅ Валидация типов вопросов

---

### 2.3 Системные шаблоны опросов

**Тесты:**
- `tests/test_system_surveys.py`
  - `test_cbt_journal_template()`
  - `test_addiction_journal_template()`
  - `test_gratitude_journal_template()`
  - `test_sleep_journal_template()`
  - `test_system_surveys_loaded()`

**Реализация:**
- `src/data/system_surveys.py`
  - Определение 4 системных шаблонов
  - Функция `load_system_surveys()` - загрузка в БД
  - Проверка существования перед загрузкой

**Критерии приемки:**
- ✅ Все 4 системных опроса определены
- ✅ Загружаются в БД при первом запуске
- ✅ Не дублируются при повторной загрузке

---

### 2.4 Хранилище опросов

**Тесты:**
- `tests/test_surveys_storage.py`
  - `test_get_all_templates()`
  - `test_get_template_by_id()`
  - `test_get_template_by_name()`
  - `test_get_template_questions()`
  - `test_save_response()`
  - `test_get_user_responses()`
  - `test_get_responses_by_template()`
  - `test_delete_response()`
  - `test_encryption_decryption()`

**Реализация:**
- `src/data/surveys_storage.py`
  - `get_available_templates()` - список шаблонов
  - `get_template_questions()` - вопросы шаблона
  - `save_survey_response()` - сохранение ответа (зашифрованно)
  - `get_user_survey_responses()` - получение ответов
  - `delete_survey_response()` - удаление
  - Шифрование/дешифрование ответов

**Критерии приемки:**
- ✅ CRUD операции работают
- ✅ Ответы шифруются
- ✅ Фильтрация по шаблону/дате

---

### 2.5 Обработчик заполнения опроса

**Тесты:**
- `tests/test_survey_fill_handlers.py`
  - `test_list_surveys_command()`
  - `test_start_fill_survey()`
  - `test_handle_text_question()`
  - `test_handle_numeric_question()`
  - `test_handle_numeric_validation()`
  - `test_handle_choice_question()`
  - `test_handle_yes_no_question()`
  - `test_handle_time_question()`
  - `test_handle_required_skip_rejected()`
  - `test_handle_optional_skip_accepted()`
  - `test_survey_completion()`
  - `test_survey_cancel()`

**Реализация:**
- `src/handlers/survey_handlers.py`
  - `list_surveys()` - /surveys - список доступных опросов
  - `start_fill_survey()` - /fill <название> - начало заполнения
  - `handle_question_answer()` - обработка ответа по типу
  - `validate_answer()` - валидация ответа
  - `show_next_question()` - переход к следующему вопросу
  - `complete_survey()` - завершение и сохранение
  - ConversationHandler для управления

**Критерии приемки:**
- ✅ Диалог проходит все вопросы
- ✅ Валидация работает по типам
- ✅ Обязательные вопросы нельзя пропустить
- ✅ Ответ сохраняется зашифрованно
- ✅ Отображается резюме заполненного опроса

---

### 2.6 Просмотр ответов на опросы

**Тесты:**
- `tests/test_survey_viewing.py`
  - `test_view_my_responses()`
  - `test_view_my_responses_empty()`
  - `test_view_responses_by_survey()`
  - `test_view_single_response()`
  - `test_view_responses_pagination()`

**Реализация:**
- `src/handlers/survey_handlers.py` (расширение)
  - `show_my_responses()` - /my_responses - все ответы
  - `show_response_detail()` - детали одного ответа
  - Форматирование ответов

**Критерии приемки:**
- ✅ Отображаются все ответы
- ✅ Форматирование читаемое
- ✅ Фильтрация по опросу
- ✅ Пагинация

---

## Phase 3: Конструктор пользовательских опросов

**Цель:** Позволить пользователям создавать свои опросы

### 3.1 Создание шаблона опроса

**Тесты:**
- `tests/test_survey_builder.py`
  - `test_create_survey_start()`
  - `test_survey_name_input()`
  - `test_survey_description_input()`
  - `test_survey_icon_input()`
  - `test_add_question_numeric()`
  - `test_add_question_text()`
  - `test_add_question_choice()`
  - `test_add_question_yes_no()`
  - `test_mark_question_optional()`
  - `test_reorder_questions()`
  - `test_save_custom_survey()`
  - `test_cancel_survey_creation()`

**Реализация:**
- `src/handlers/survey_builder.py`
  - `start_create_survey()` - /create_survey
  - `handle_survey_name()` - ввод названия
  - `handle_survey_description()` - ввод описания
  - `handle_add_question()` - добавление вопроса
  - `handle_question_type()` - выбор типа вопроса
  - `handle_question_config()` - конфигурация вопроса
  - `finish_survey_creation()` - сохранение
  - ConversationHandler

**Критерии приемки:**
- ✅ Можно создать опрос с несколькими вопросами
- ✅ Поддерживаются все типы вопросов
- ✅ Конфигурация для choice работает
- ✅ Опрос сохраняется в БД
- ✅ Опрос доступен только создателю

---

### 3.2 Управление пользовательскими опросами

**Тесты:**
- `tests/test_survey_management.py`
  - `test_list_my_surveys()`
  - `test_edit_survey()`
  - `test_delete_survey()`
  - `test_delete_survey_with_responses()`
  - `test_activate_deactivate_survey()`

**Реализация:**
- `src/handlers/survey_builder.py` (расширение)
  - `list_my_surveys()` - список своих опросов
  - `edit_survey()` - /edit_survey <id>
  - `delete_survey()` - /delete_survey <id>
  - Подтверждение удаления

**Критерии приемки:**
- ✅ Можно редактировать свои опросы
- ✅ Можно удалить опрос
- ✅ При удалении предупреждение об ответах
- ✅ Нельзя редактировать чужие опросы

---

## Phase 4: Базовая аналитика

**Цель:** Предоставить статистику по впечатлениям и опросам

### 4.1 Аналитика впечатлений

**Тесты:**
- `tests/test_impression_analytics.py`
  - `test_impressions_by_category_stats()`
  - `test_impressions_by_tag_stats()`
  - `test_impressions_intensity_average()`
  - `test_impressions_by_time_of_day()`
  - `test_impressions_by_day_of_week()`
  - `test_impressions_trend()`

**Реализация:**
- `src/handlers/impression_analytics.py`
  - `show_impression_analytics()` - /impression_analytics
  - Подсчет статистики по категориям/тегам
  - Средняя интенсивность
  - Распределение по времени суток
  - Тренды

**Критерии приемки:**
- ✅ Статистика корректно подсчитывается
- ✅ Форматирование читаемое
- ✅ Работает для разных периодов

---

### 4.2 Аналитика опросов

**Тесты:**
- `tests/test_survey_analytics.py`
  - `test_survey_completion_rate()`
  - `test_numeric_questions_trend()`
  - `test_choice_questions_frequency()`
  - `test_cbt_before_after_comparison()`
  - `test_addiction_craving_trend()`

**Реализация:**
- `src/handlers/survey_analytics.py`
  - `show_survey_stats()` - /survey_stats <название>
  - Статистика числовых вопросов (среднее, min, max, тренд)
  - Частота выбора для choice
  - Специальная аналитика для КПТ (до/после)
  - Специальная аналитика для дневника зависимости

**Критерии приемки:**
- ✅ Статистика по числовым вопросам
- ✅ Частота выборов
- ✅ Специфичная аналитика для КПТ
- ✅ Форматирование и графики (текстовые)

---

## Phase 5: Расширенная функциональность

**Цель:** Интеграция, уведомления, экспорт

### 5.1 Привязка впечатлений к записям дня

**Тесты:**
- `tests/test_impression_entry_link.py`
  - `test_link_impression_to_existing_entry()`
  - `test_link_impression_to_new_entry()`
  - `test_show_entry_with_impressions()`
  - `test_unlink_impression()`

**Реализация:**
- `src/handlers/impression_handlers.py` (расширение)
  - Привязка к существующей записи дня
  - Автоматическая привязка при создании записи
  - Отображение впечатлений в записи дня

**Критерии приемки:**
- ✅ Впечатление привязывается к записи
- ✅ В /recent отображаются впечатления
- ✅ Можно отвязать впечатление

---

### 5.2 Уведомления по опросам

**Тесты:**
- `tests/test_survey_notifications.py`
  - `test_enable_survey_notification()`
  - `test_disable_survey_notification()`
  - `test_notification_sent_at_time()`
  - `test_notification_not_sent_if_filled_today()`

**Реализация:**
- `src/handlers/survey_notifications.py`
  - `manage_survey_notifications()` - /survey_notifications
  - Настройка времени уведомлений для опросов
  - Интеграция с существующей системой уведомлений
  - Проверка заполнения перед отправкой

**Критерии приемки:**
- ✅ Можно настроить время для каждого опроса
- ✅ Уведомление приходит вовремя
- ✅ Не приходит если уже заполнено
- ✅ Можно отключить

---

### 5.3 Избранные опросы

**Тесты:**
- `tests/test_favorite_surveys.py`
  - `test_add_to_favorites()`
  - `test_remove_from_favorites()`
  - `test_list_favorites()`
  - `test_quick_fill_favorite()`

**Реализация:**
- `src/handlers/survey_handlers.py` (расширение)
  - `manage_favorites()` - /favorite_surveys
  - Добавление/удаление из избранного
  - Быстрый доступ к избранным

**Критерии приемки:**
- ✅ Можно добавить в избранное
- ✅ Избранные отображаются первыми
- ✅ Быстрое заполнение

---

### 5.4 Экспорт данных

**Тесты:**
- `tests/test_export.py`
  - `test_export_impressions_csv()`
  - `test_export_survey_responses_csv()`
  - `test_export_combined_csv()`
  - `test_export_json()`

**Реализация:**
- `src/handlers/export_handlers.py`
  - Экспорт впечатлений в CSV
  - Экспорт ответов на опросы в CSV
  - Комбинированный экспорт
  - JSON формат

**Критерии приемки:**
- ✅ CSV корректно форматируется
- ✅ Можно импортировать обратно
- ✅ JSON валидный

---

### 5.5 Комбинированная аналитика

**Тесты:**
- `tests/test_combined_analytics.py`
  - `test_impressions_mood_correlation()`
  - `test_survey_responses_mood_correlation()`
  - `test_craving_sleep_correlation()`
  - `test_combined_report()`

**Реализация:**
- `src/handlers/combined_analytics.py`
  - `/combined_analytics` - общая аналитика
  - Корреляция впечатлений с настроением
  - Корреляция опросов с метриками
  - Комплексные инсайты

**Критерии приемки:**
- ✅ Корреляции подсчитываются
- ✅ Инсайты информативные
- ✅ Форматирование читаемое

---

## Phase 6: Шаринг и визуализация

**Цель:** Делиться шаблонами, графики

### 6.1 Шаринг шаблонов опросов

**Тесты:**
- `tests/test_survey_sharing.py`
  - `test_share_survey_template()`
  - `test_import_shared_template()`
  - `test_template_link_generation()`
  - `test_cannot_share_system_survey()`

**Реализация:**
- `src/handlers/survey_sharing.py`
  - `/share_survey <id>` - получение ссылки
  - Импорт по ссылке/коду
  - Копирование шаблона

**Критерии приемки:**
- ✅ Можно поделиться своим опросом
- ✅ Другой пользователь может импортировать
- ✅ Данные не передаются, только шаблон

---

### 6.2 Визуализация

**Тесты:**
- `tests/test_visualization.py`
  - `test_impressions_chart()`
  - `test_survey_trends_chart()`
  - `test_combined_chart()`

**Реализация:**
- `src/visualization/impressions_charts.py`
  - Графики для впечатлений
  - Графики для опросов
  - Использование matplotlib

**Критерии приемки:**
- ✅ Графики генерируются
- ✅ Читаемые и информативные

---

## Общая структура тестирования

### Типы тестов

1. **Unit тесты** - тестирование отдельных функций
   - `tests/unit/`

2. **Integration тесты** - тестирование взаимодействия компонентов
   - `tests/integration/`

3. **E2E тесты** - тестирование полных сценариев
   - `tests/e2e/`

### Запуск тестов

```bash
# Все тесты
pytest

# Конкретная фаза
pytest tests/test_impressions*.py

# С покрытием
pytest --cov=src --cov-report=html

# Конкретный тест
pytest tests/test_impressions_storage.py::test_save_impression -v
```

### Coverage цели

- Phase 1: 90%+ coverage для impressions
- Phase 2: 90%+ coverage для surveys
- Phase 3-6: 85%+ coverage

---

## Интеграция с существующим кодом

### Изменения в main.py

```python
# Инициализация новых обработчиков
from src.handlers import impression_handlers, survey_handlers

# Добавление в Application
app.add_handler(impression_handlers.impression_conv_handler)
app.add_handler(survey_handlers.survey_fill_conv_handler)
# ... и т.д.
```

### Изменения в src/data/storage.py

```python
# Добавление миграций
from src.data.migrations import run_all_migrations

def initialize_storage():
    conn = _get_db_connection()
    _migrate_csv_to_sqlite()
    run_all_migrations(conn)  # Новые таблицы
    logger.info("Хранилище данных инициализировано")
```

---

## Checklist по фазам

### ✅ Phase 1: Впечатления
- [ ] 1.1 Миграция БД
- [ ] 1.2 Модели данных
- [ ] 1.3 Хранилище
- [ ] 1.4 Обработчик добавления
- [ ] 1.5 Просмотр

### ⬜ Phase 2: Опросы
- [ ] 2.1 Миграция БД
- [ ] 2.2 Модели данных
- [ ] 2.3 Системные шаблоны
- [ ] 2.4 Хранилище
- [ ] 2.5 Заполнение опроса
- [ ] 2.6 Просмотр ответов

### ⬜ Phase 3: Конструктор
- [ ] 3.1 Создание шаблона
- [ ] 3.2 Управление

### ⬜ Phase 4: Аналитика
- [ ] 4.1 Аналитика впечатлений
- [ ] 4.2 Аналитика опросов

### ⬜ Phase 5: Расширенная функциональность
- [ ] 5.1 Привязка к записям
- [ ] 5.2 Уведомления
- [ ] 5.3 Избранные
- [ ] 5.4 Экспорт
- [ ] 5.5 Комбинированная аналитика

### ⬜ Phase 6: Шаринг и визуализация
- [ ] 6.1 Шаринг шаблонов
- [ ] 6.2 Визуализация

---

## Оценка времени

- Phase 1: 2-3 дня
- Phase 2: 3-4 дня
- Phase 3: 2 дня
- Phase 4: 2 дня
- Phase 5: 3 дня
- Phase 6: 2 дня

**Итого:** ~14-18 дней разработки

---

## Следующие шаги

1. Создать структуру папок для тестов
2. Начать с Phase 1.1 - написать тесты миграции
3. Запустить тесты (они провалятся)
4. Реализовать миграцию
5. Запустить тесты (они пройдут)
6. Перейти к Phase 1.2

**Приступаем к Phase 1.1!**
