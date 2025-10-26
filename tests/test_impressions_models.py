"""
Тесты для моделей данных впечатлений (Impression, ImpressionTag).

TDD Phase 1.2: Эти тесты должны провалиться до реализации моделей.
"""

import pytest
from datetime import datetime


def test_impression_creation():
    """
    Тест: создание экземпляра Impression с обязательными полями.
    """
    from src.data.models import Impression

    impression = Impression(
        id=1,
        chat_id=123456,
        impression_text="Хочется выпить",
        impression_date="2025-10-24",
        impression_time="18:45:00",
        category=None,
        intensity=None,
        entry_date=None
    )

    assert impression.id == 1
    assert impression.chat_id == 123456
    assert impression.impression_text == "Хочется выпить"
    assert impression.impression_date == "2025-10-24"
    assert impression.impression_time == "18:45:00"
    assert impression.category is None
    assert impression.intensity is None
    assert impression.entry_date is None


def test_impression_with_all_fields():
    """
    Тест: создание Impression со всеми полями.
    """
    from src.data.models import Impression

    impression = Impression(
        id=1,
        chat_id=123456,
        impression_text="Хочется выпить",
        impression_date="2025-10-24",
        impression_time="18:45:00",
        category="craving",
        intensity=7,
        entry_date="2025-10-24"
    )

    assert impression.category == "craving"
    assert impression.intensity == 7
    assert impression.entry_date == "2025-10-24"


def test_impression_category_validation():
    """
    Тест: валидация категории впечатления.

    Допустимые категории: craving, emotion, physical, thoughts, other
    """
    from src.data.models import Impression

    # Валидные категории
    valid_categories = ["craving", "emotion", "physical", "thoughts", "other", None]

    for category in valid_categories:
        impression = Impression(
            id=1,
            chat_id=123,
            impression_text="Тест",
            impression_date="2025-10-24",
            impression_time="12:00:00",
            category=category,
            intensity=None,
            entry_date=None
        )
        assert impression.category == category

    # Невалидная категория должна вызвать ошибку
    with pytest.raises(ValueError, match="Invalid category"):
        Impression(
            id=1,
            chat_id=123,
            impression_text="Тест",
            impression_date="2025-10-24",
            impression_time="12:00:00",
            category="invalid_category",
            intensity=None,
            entry_date=None
        )


def test_impression_intensity_validation():
    """
    Тест: валидация интенсивности (должна быть от 1 до 10 или None).
    """
    from src.data.models import Impression

    # Валидные значения
    for intensity in [None, 1, 5, 10]:
        impression = Impression(
            id=1,
            chat_id=123,
            impression_text="Тест",
            impression_date="2025-10-24",
            impression_time="12:00:00",
            category=None,
            intensity=intensity,
            entry_date=None
        )
        assert impression.intensity == intensity

    # Невалидные значения
    for invalid_intensity in [0, 11, -1, 100]:
        with pytest.raises(ValueError, match="Intensity must be between 1 and 10"):
            Impression(
                id=1,
                chat_id=123,
                impression_text="Тест",
                impression_date="2025-10-24",
                impression_time="12:00:00",
                category=None,
                intensity=invalid_intensity,
                entry_date=None
            )


def test_impression_to_dict():
    """
    Тест: преобразование Impression в словарь (для шифрования).
    """
    from src.data.models import Impression

    impression = Impression(
        id=1,
        chat_id=123456,
        impression_text="Хочется выпить",
        impression_date="2025-10-24",
        impression_time="18:45:00",
        category="craving",
        intensity=7,
        entry_date="2025-10-24"
    )

    result = impression.to_dict()

    assert isinstance(result, dict)
    assert result['id'] == 1
    assert result['chat_id'] == 123456
    assert result['impression_text'] == "Хочется выпить"
    assert result['impression_date'] == "2025-10-24"
    assert result['impression_time'] == "18:45:00"
    assert result['category'] == "craving"
    assert result['intensity'] == 7
    assert result['entry_date'] == "2025-10-24"


def test_impression_from_dict():
    """
    Тест: создание Impression из словаря (после расшифровки).
    """
    from src.data.models import Impression

    data = {
        'id': 1,
        'chat_id': 123456,
        'impression_text': "Хочется выпить",
        'impression_date': "2025-10-24",
        'impression_time': "18:45:00",
        'category': "craving",
        'intensity': 7,
        'entry_date': "2025-10-24"
    }

    impression = Impression.from_dict(data)

    assert impression.id == 1
    assert impression.chat_id == 123456
    assert impression.impression_text == "Хочется выпить"
    assert impression.impression_date == "2025-10-24"
    assert impression.impression_time == "18:45:00"
    assert impression.category == "craving"
    assert impression.intensity == 7
    assert impression.entry_date == "2025-10-24"


def test_impression_from_dict_with_optional_fields():
    """
    Тест: создание Impression из словаря с опциональными полями.
    """
    from src.data.models import Impression

    # Минимальные данные
    data = {
        'id': 1,
        'chat_id': 123456,
        'impression_text': "Тест",
        'impression_date': "2025-10-24",
        'impression_time': "12:00:00"
    }

    impression = Impression.from_dict(data)

    assert impression.category is None
    assert impression.intensity is None
    assert impression.entry_date is None


def test_impression_tag_creation():
    """
    Тест: создание экземпляра ImpressionTag.
    """
    from src.data.models import ImpressionTag

    tag = ImpressionTag(
        id=1,
        chat_id=123456,
        tag_name="алкоголь",
        tag_color=None
    )

    assert tag.id == 1
    assert tag.chat_id == 123456
    assert tag.tag_name == "алкоголь"
    assert tag.color is None


def test_impression_tag_with_color():
    """
    Тест: создание ImpressionTag с цветом.
    """
    from src.data.models import ImpressionTag

    tag = ImpressionTag(
        id=1,
        chat_id=123456,
        tag_name="стресс",
        tag_color="#FF0000"
    )

    assert tag.color == "#FF0000"


def test_impression_tag_to_dict():
    """
    Тест: преобразование ImpressionTag в словарь.
    """
    from src.data.models import ImpressionTag

    tag = ImpressionTag(
        id=1,
        chat_id=123456,
        tag_name="алкоголь",
        tag_color="#FF5733"
    )

    result = tag.to_dict()

    assert isinstance(result, dict)
    assert result['id'] == 1
    assert result['chat_id'] == 123456
    assert result['tag_name'] == "алкоголь"
    assert result['tag_color'] == "#FF5733"


def test_impression_tag_from_dict():
    """
    Тест: создание ImpressionTag из словаря.
    """
    from src.data.models import ImpressionTag

    data = {
        'id': 1,
        'chat_id': 123456,
        'tag_name': "стресс",
        'tag_color': "#0000FF"
    }

    tag = ImpressionTag.from_dict(data)

    assert tag.id == 1
    assert tag.chat_id == 123456
    assert tag.tag_name == "стресс"
    assert tag.color == "#0000FF"


def test_impression_dict_typed_dict():
    """
    Тест: TypedDict для ImpressionDict (для шифрования).
    """
    from src.data.models import ImpressionDict

    # Проверяем что можем создать словарь нужной структуры
    data: ImpressionDict = {
        'id': 1,
        'chat_id': 123456,
        'impression_text': "Тест",
        'impression_date': "2025-10-24",
        'impression_time': "12:00:00",
        'category': "emotion",
        'intensity': 5,
        'entry_date': None
    }

    assert data['id'] == 1
    assert data['chat_id'] == 123456
    assert data['category'] == "emotion"


def test_impression_tag_dict_typed_dict():
    """
    Тест: TypedDict для ImpressionTagDict.
    """
    from src.data.models import ImpressionTagDict

    data: ImpressionTagDict = {
        'id': 1,
        'chat_id': 123456,
        'tag_name': "тест",
        'tag_color': None
    }

    assert data['id'] == 1
    assert data['tag_name'] == "тест"


def test_impression_categories_constant():
    """
    Тест: константа IMPRESSION_CATEGORIES существует и содержит правильные значения.
    """
    from src.data.models import IMPRESSION_CATEGORIES

    assert isinstance(IMPRESSION_CATEGORIES, (list, tuple, set))

    expected = {"craving", "emotion", "physical", "thoughts", "other"}
    assert set(IMPRESSION_CATEGORIES) == expected


def test_impression_roundtrip_serialization():
    """
    Тест: полный цикл сериализации и десериализации Impression.

    Impression -> to_dict() -> from_dict() -> должен получиться идентичный объект
    """
    from src.data.models import Impression

    original = Impression(
        id=42,
        chat_id=999,
        impression_text="Тестовое впечатление",
        impression_date="2025-10-24",
        impression_time="15:30:00",
        category="emotion",
        intensity=8,
        entry_date="2025-10-24"
    )

    # Сериализация
    data = original.to_dict()

    # Десериализация
    restored = Impression.from_dict(data)

    # Проверка идентичности
    assert restored.id == original.id
    assert restored.chat_id == original.chat_id
    assert restored.impression_text == original.impression_text
    assert restored.impression_date == original.impression_date
    assert restored.impression_time == original.impression_time
    assert restored.category == original.category
    assert restored.intensity == original.intensity
    assert restored.entry_date == original.entry_date


def test_impression_tag_name_normalization():
    """
    Тест: нормализация имени тега (приведение к нижнему регистру).
    """
    from src.data.models import ImpressionTag

    tag = ImpressionTag(
        id=1,
        chat_id=123,
        tag_name="АЛКОГОЛЬ",
        tag_color=None
    )

    # Имя тега должно быть приведено к нижнему регистру
    assert tag.tag_name == "алкоголь"
