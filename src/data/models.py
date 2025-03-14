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
