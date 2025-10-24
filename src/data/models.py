"""
Модуль с определениями структур данных.
Содержит классы и типы для работы с данными в приложении.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, TypedDict, Union
from datetime import datetime


class UserDict(TypedDict):
    """Структура данных для пользователя."""
    chat_id: int
    username: Optional[str]
    first_name: Optional[str]
    notification_time: Optional[str]


class EntryDict(TypedDict):
    """Структура данных для записи в дневнике."""
    date: str  # формат 'YYYY-MM-DD'
    mood: str  # оценка от 1 до 10
    sleep: str  # оценка от 1 до 10
    comment: Optional[str]  # комментарий или None
    balance: str  # оценка от 1 до 10
    mania: str  # оценка от 1 до 10
    depression: str  # оценка от 1 до 10
    anxiety: str  # оценка от 1 до 10
    irritability: str  # оценка от 1 до 10
    productivity: str  # оценка от 1 до 10
    sociability: str  # оценка от 1 до 10


class StoredEntryDict(TypedDict):
    """Структура данных для хранения зашифрованной записи."""
    date: str  # формат 'YYYY-MM-DD'
    encrypted_data: str  # зашифрованные данные в base64


@dataclass
class Entry:
    """Класс для записи в дневнике с проверкой типов."""
    date: str
    mood: int
    sleep: int
    comment: Optional[str]
    balance: int
    mania: int
    depression: int
    anxiety: int
    irritability: int
    productivity: int
    sociability: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entry':
        """Создает экземпляр класса из словаря."""
        return cls(
            date=data['date'],
            mood=int(data['mood']),
            sleep=int(data['sleep']),
            comment=data.get('comment'),
            balance=int(data['balance']),
            mania=int(data['mania']),
            depression=int(data['depression']),
            anxiety=int(data['anxiety']),
            irritability=int(data['irritability']),
            productivity=int(data['productivity']),
            sociability=int(data['sociability'])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует экземпляр класса в словарь."""
        return {
            'date': self.date,
            'mood': str(self.mood),
            'sleep': str(self.sleep),
            'comment': self.comment,
            'balance': str(self.balance),
            'mania': str(self.mania),
            'depression': str(self.depression),
            'anxiety': str(self.anxiety),
            'irritability': str(self.irritability),
            'productivity': str(self.productivity),
            'sociability': str(self.sociability)
        }


@dataclass
class User:
    """Класс для пользователя с проверкой типов."""
    chat_id: int
    username: Optional[str]
    first_name: Optional[str]
    notification_time: Optional[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Создает экземпляр класса из словаря."""
        return cls(
            chat_id=int(data['chat_id']),
            username=data.get('username'),
            first_name=data.get('first_name'),
            notification_time=data.get('notification_time')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует экземпляр класса в словарь."""
        return {
            'chat_id': self.chat_id,
            'username': self.username,
            'first_name': self.first_name,
            'notification_time': self.notification_time
        }


class SharedPackage(TypedDict):
    """Структура данных для обмена зашифрованными данными."""
    encrypted_data: str
    sender_id: int
    format_version: str


# ============================================================================
# Модели для впечатлений (Impressions)
# ============================================================================

# Допустимые категории впечатлений
IMPRESSION_CATEGORIES = ("craving", "emotion", "physical", "thoughts", "other")


class ImpressionDict(TypedDict):
    """Структура данных для впечатления."""
    id: int
    chat_id: int
    impression_text: str
    impression_date: str  # формат 'YYYY-MM-DD'
    impression_time: str  # формат 'HH:MM:SS'
    category: Optional[str]  # одна из IMPRESSION_CATEGORIES
    intensity: Optional[int]  # от 1 до 10
    entry_date: Optional[str]  # связь с основной записью дня


class ImpressionTagDict(TypedDict):
    """Структура данных для тега впечатления."""
    id: int
    chat_id: int
    tag_name: str
    tag_color: Optional[str]


@dataclass
class Impression:
    """Класс для впечатления с проверкой типов и валидацией."""
    id: int
    chat_id: int
    impression_text: str
    impression_date: str
    impression_time: str
    category: Optional[str]
    intensity: Optional[int]
    entry_date: Optional[str]

    def __post_init__(self):
        """Валидация полей после инициализации."""
        # Валидация категории
        if self.category is not None and self.category not in IMPRESSION_CATEGORIES:
            raise ValueError(
                f"Invalid category: {self.category}. "
                f"Must be one of {IMPRESSION_CATEGORIES}"
            )

        # Валидация интенсивности
        if self.intensity is not None:
            if not isinstance(self.intensity, int):
                raise ValueError("Intensity must be an integer")
            if self.intensity < 1 or self.intensity > 10:
                raise ValueError("Intensity must be between 1 and 10")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Impression':
        """Создает экземпляр класса из словаря."""
        return cls(
            id=int(data['id']),
            chat_id=int(data['chat_id']),
            impression_text=str(data['impression_text']),
            impression_date=str(data['impression_date']),
            impression_time=str(data['impression_time']),
            category=data.get('category'),
            intensity=int(data['intensity']) if data.get('intensity') is not None else None,
            entry_date=data.get('entry_date')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует экземпляр класса в словарь."""
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'impression_text': self.impression_text,
            'impression_date': self.impression_date,
            'impression_time': self.impression_time,
            'category': self.category,
            'intensity': self.intensity,
            'entry_date': self.entry_date
        }


@dataclass
class ImpressionTag:
    """Класс для тега впечатления с проверкой типов."""
    id: int
    chat_id: int
    tag_name: str
    tag_color: Optional[str]

    def __post_init__(self):
        """Нормализация и валидация после инициализации."""
        # Приводим имя тега к нижнему регистру
        self.tag_name = self.tag_name.lower().strip()

    @property
    def color(self) -> Optional[str]:
        """Алиас для tag_color для удобства."""
        return self.tag_color

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImpressionTag':
        """Создает экземпляр класса из словаря."""
        return cls(
            id=int(data['id']),
            chat_id=int(data['chat_id']),
            tag_name=str(data['tag_name']),
            tag_color=data.get('tag_color')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует экземпляр класса в словарь."""
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'tag_name': self.tag_name,
            'tag_color': self.tag_color
        }
