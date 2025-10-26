# Phase 3: Custom Survey Builder - План реализации

## Обзор

Phase 3 добавляет возможность пользователям создавать собственные шаблоны опросов через интерактивный интерфейс бота. Пользователи смогут создавать, редактировать и удалять свои шаблоны, а также управлять вопросами в них.

## Требования

### Функциональные требования:
1. Создание пользовательских шаблонов опросов
2. Добавление вопросов разных типов к шаблону
3. Редактирование существующих шаблонов и вопросов
4. Удаление шаблонов и вопросов
5. Активация/деактивация шаблонов
6. Валидация данных при создании
7. Ограничения: максимум 20 пользовательских шаблонов на пользователя

### Нефункциональные требования:
1. TDD подход - все функции покрыты тестами
2. Интуитивный пошаговый интерфейс
3. Защита от удаления системных шаблонов
4. Автоматическая валидация корректности шаблонов

## Архитектура

### Новые состояния ConversationHandler:
```python
# В src/config.py добавить:
CREATE_SURVEY_NAME = 28
CREATE_SURVEY_DESC = 29
ADD_QUESTION_TYPE = 30
ADD_QUESTION_TEXT = 31
ADD_QUESTION_CONFIG = 32
EDIT_SURVEY_SELECT = 33
EDIT_QUESTION_SELECT = 34
DELETE_SURVEY_CONFIRM = 35
```

### Новые команды:
- `/create_survey` - начать создание нового опроса
- `/edit_survey <название>` - редактировать существующий опрос
- `/delete_survey <название>` - удалить пользовательский опрос
- `/my_surveys` - список моих опросов
- `/activate_survey <название>` - активировать опрос
- `/deactivate_survey <название>` - деактивировать опрос

## Phase 3.1: Create Template Handlers

### Файл: `src/handlers/survey_create.py`

**Функции:**
```python
async def create_survey_start(update, context):
    """Начало создания опроса - /create_survey"""
    # Проверка лимита (max 20 шаблонов)
    # Запрос названия

async def receive_survey_name(update, context):
    """Получение названия опроса"""
    # Валидация уникальности названия
    # Запрос описания

async def receive_survey_description(update, context):
    """Получение описания опроса"""
    # Сохранение шаблона в БД (is_active=False)
    # Предложение добавить первый вопрос

async def show_my_surveys(update, context):
    """Показ списка пользовательских опросов - /my_surveys"""
    # Группировка по active/inactive
    # Показ количества вопросов в каждом
```

**Валидация:**
- Название: 3-50 символов, уникальное для пользователя
- Описание: до 500 символов
- Лимит: максимум 20 пользовательских шаблонов

### Тесты: `tests/test_survey_create.py`
- test_create_survey_start_success
- test_create_survey_exceeds_limit
- test_receive_name_valid
- test_receive_name_duplicate
- test_receive_name_too_short
- test_receive_name_too_long
- test_receive_description_valid
- test_show_my_surveys_empty
- test_show_my_surveys_multiple

**Оценка:** ~12 тестов

## Phase 3.2: Add Questions Handlers

### Файл: `src/handlers/survey_questions.py`

**Функции:**
```python
async def add_question_start(update, context):
    """Начало добавления вопроса к шаблону"""
    # Показ типов вопросов (inline keyboard)
    # text, numeric, yes_no, time, choice, scale

async def select_question_type(update, context):
    """Выбор типа вопроса"""
    # Сохранение типа в context
    # Запрос текста вопроса

async def receive_question_text(update, context):
    """Получение текста вопроса"""
    # Валидация длины (10-500 символов)
    # Запрос конфигурации (если нужна для типа)

async def configure_numeric_question(update, context):
    """Конфигурация numeric вопроса"""
    # Запрос min/max значений

async def configure_choice_question(update, context):
    """Конфигурация choice вопроса"""
    # Запрос вариантов ответа
    # Запрос single/multiple

async def configure_scale_question(update, context):
    """Конфигурация scale вопроса"""
    # Запрос min/max/step

async def save_question(update, context):
    """Сохранение вопроса в БД"""
    # Валидация order_num (автоинкремент)
    # Сохранение в survey_questions
    # Предложение добавить еще или завершить
```

**Валидация:**
- Текст вопроса: 10-500 символов
- Numeric: min < max, разумные пределы
- Choice: 2-10 вариантов, каждый 1-100 символов
- Scale: min < max, step > 0
- Максимум 30 вопросов в шаблоне

### Тесты: `tests/test_survey_questions.py`
- test_add_question_to_template
- test_select_each_question_type (6 тестов)
- test_receive_question_text_valid
- test_receive_question_text_too_short
- test_receive_question_text_too_long
- test_configure_numeric_valid
- test_configure_numeric_invalid_range
- test_configure_choice_valid
- test_configure_choice_too_few_options
- test_configure_choice_too_many_options
- test_configure_scale_valid
- test_configure_scale_invalid_step
- test_save_question_success
- test_question_limit_reached

**Оценка:** ~20 тестов

## Phase 3.3: Edit Template Handlers

### Файл: `src/handlers/survey_edit.py`

**Функции:**
```python
async def edit_survey_start(update, context):
    """Начало редактирования опроса - /edit_survey <name>"""
    # Проверка владельца шаблона
    # Показ меню редактирования:
    #   - Изменить название
    #   - Изменить описание
    #   - Редактировать вопросы
    #   - Изменить порядок вопросов

async def edit_survey_name(update, context):
    """Изменение названия опроса"""
    # Валидация уникальности нового названия
    # Обновление в БД

async def edit_survey_description(update, context):
    """Изменение описания опроса"""

async def show_questions_for_edit(update, context):
    """Показ списка вопросов для редактирования"""
    # Inline keyboard с вопросами

async def edit_question(update, context):
    """Редактирование конкретного вопроса"""
    # Показ текущих данных
    # Запрос новых данных

async def reorder_questions(update, context):
    """Изменение порядка вопросов"""
    # Показ текущего порядка
    # Кнопки "вверх/вниз" для каждого вопроса

async def delete_question(update, context):
    """Удаление вопроса из шаблона"""
    # Подтверждение
    # Пересчет order_num
```

**Валидация:**
- Только владелец может редактировать
- Нельзя редактировать системные шаблоны (is_system=True)
- Валидация данных как при создании

### Тесты: `tests/test_survey_edit.py`
- test_edit_survey_as_owner
- test_edit_survey_not_owner
- test_edit_system_survey_forbidden
- test_edit_survey_name_valid
- test_edit_survey_name_duplicate
- test_edit_survey_description
- test_show_questions_for_edit
- test_edit_question_text
- test_edit_question_config
- test_reorder_questions_up
- test_reorder_questions_down
- test_delete_question_success
- test_delete_question_confirm_required

**Оценка:** ~15 тестов

## Phase 3.4: Delete Template Handlers

### Файл: `src/handlers/survey_delete.py`

**Функции:**
```python
async def delete_survey_start(update, context):
    """Начало удаления опроса - /delete_survey <name>"""
    # Проверка владельца
    # Запрос подтверждения

async def confirm_delete_survey(update, context):
    """Подтверждение удаления опроса"""
    # Удаление шаблона (CASCADE удалит вопросы и ответы)
    # Уведомление об успехе

async def activate_survey(update, context):
    """Активация опроса - /activate_survey <name>"""
    # Проверка что есть хотя бы 1 вопрос
    # Установка is_active=True

async def deactivate_survey(update, context):
    """Деактивация опроса - /deactivate_survey <name>"""
    # Установка is_active=False
```

**Валидация:**
- Только владелец может удалить
- Нельзя удалить системные шаблоны
- При активации проверка наличия вопросов

### Тесты: `tests/test_survey_delete.py`
- test_delete_survey_as_owner
- test_delete_survey_not_owner
- test_delete_system_survey_forbidden
- test_confirm_delete_survey
- test_cancel_delete_survey
- test_activate_survey_with_questions
- test_activate_survey_no_questions
- test_deactivate_survey

**Оценка:** ~10 тестов

## Phase 3.5: Storage Extensions

### Файл: `src/data/surveys_storage.py` (расширение)

**Новые функции:**
```python
def create_user_template(conn, chat_id, name, description) -> int:
    """Создание пользовательского шаблона"""

def update_template(conn, template_id, chat_id, **updates) -> bool:
    """Обновление шаблона (название, описание, is_active)"""

def delete_template(conn, template_id, chat_id) -> bool:
    """Удаление шаблона (только владелец)"""

def get_user_templates(conn, chat_id, only_active=False) -> List[Dict]:
    """Получение шаблонов пользователя"""

def count_user_templates(conn, chat_id) -> int:
    """Подсчет количества шаблонов пользователя"""

def add_question_to_template(conn, template_id, chat_id, question_data) -> int:
    """Добавление вопроса к шаблону"""

def update_question(conn, question_id, template_id, chat_id, **updates) -> bool:
    """Обновление вопроса (только владелец шаблона)"""

def delete_question(conn, question_id, template_id, chat_id) -> bool:
    """Удаление вопроса"""

def reorder_questions(conn, template_id, chat_id, question_ids_order) -> bool:
    """Изменение порядка вопросов"""
```

### Тесты: `tests/test_surveys_storage_extended.py`
- test_create_user_template
- test_update_template_name
- test_update_template_description
- test_update_template_is_active
- test_delete_template_as_owner
- test_delete_template_not_owner
- test_get_user_templates
- test_count_user_templates
- test_count_respects_limit
- test_add_question_to_template
- test_update_question_as_owner
- test_delete_question_as_owner
- test_reorder_questions

**Оценка:** ~15 тестов

## Интеграция

### Изменения в `src/bot.py`:
```python
from src.handlers import (
    ...,
    survey_create, survey_questions, survey_edit, survey_delete
)

survey_create.register(application)
survey_questions.register(application)
survey_edit.register(application)
survey_delete.register(application)
```

### Изменения в `src/config.py`:
- Добавить 8 новых состояний
- Увеличить range() соответственно

### Обновление БД:
Существующая схема уже поддерживает пользовательские шаблоны:
- `survey_templates.created_by` - chat_id владельца
- `survey_templates.is_system` - флаг системного шаблона

## Оценка тестового покрытия

| Phase | Файл | Тестов |
|-------|------|--------|
| 3.1 | test_survey_create.py | 12 |
| 3.2 | test_survey_questions.py | 20 |
| 3.3 | test_survey_edit.py | 15 |
| 3.4 | test_survey_delete.py | 10 |
| 3.5 | test_surveys_storage_extended.py | 15 |
| **Итого** | | **~72 теста** |

## Итоговая статистика по всем фазам

| Фаза | Тестов | Статус |
|------|--------|--------|
| Phase 1: Impressions | 59 | ✅ Завершена |
| Phase 2: Surveys | 65 | ✅ Завершена |
| Phase 3: Custom Builder | 72 | 📋 Планируется |
| **Всего** | **196** | |
| Существующие тесты | 220 | |
| **Итоговое покрытие** | **416** | |

## Порядок реализации

1. **Phase 3.1**: Create Template Handlers + тесты
2. **Phase 3.2**: Add Questions Handlers + тесты
3. **Phase 3.3**: Edit Template Handlers + тесты
4. **Phase 3.4**: Delete Template Handlers + тесты
5. **Phase 3.5**: Storage Extensions + тесты
6. **Integration**: Интеграция в бота
7. **Documentation**: Обновление README

## Риски и ограничения

### Риски:
1. Сложность UI для конфигурации вопросов в Telegram
2. Валидация конфигурации может быть сложной для пользователей

### Митигация:
1. Пошаговый интерфейс с подсказками
2. Примеры для каждого типа вопроса
3. Валидация с понятными сообщениями об ошибках

### Ограничения:
- Максимум 20 пользовательских шаблонов
- Максимум 30 вопросов в шаблоне
- Максимум 10 вариантов в choice вопросе

## Следующие шаги

После утверждения плана:
1. Начать с Phase 3.1 (Create Template Handlers)
2. Следовать TDD методологии
3. Коммитить после каждой подфазы
4. Запускать полный набор тестов перед каждым коммитом
