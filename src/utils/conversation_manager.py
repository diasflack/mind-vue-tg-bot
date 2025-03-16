"""
Модуль для управления активными диалогами (ConversationHandler) пользователей.
Обеспечивает корректное завершение активных диалогов при начале новых.
"""

import logging
from typing import Dict, Set, Any

# Настройка логгирования
logger = logging.getLogger(__name__)

# Глобальный словарь для хранения активных разговоров пользователей
# Структура: {chat_id: {handler_name: conversation_state}}
active_conversations: Dict[int, Dict[str, Any]] = {}


def register_conversation(chat_id: int, handler_name: str, state: Any) -> None:
    """
    Регистрирует активный диалог для пользователя.

    Args:
        chat_id: ID пользователя
        handler_name: имя обработчика диалога
        state: текущее состояние диалога
    """
    if chat_id not in active_conversations:
        active_conversations[chat_id] = {}

    active_conversations[chat_id][handler_name] = state
    logger.info(f"Зарегистрирован диалог {handler_name} для пользователя {chat_id}, состояние: {state}")


def end_conversation(chat_id: int, handler_name: str) -> None:
    """
    Завершает активный диалог для пользователя.

    Args:
        chat_id: ID пользователя
        handler_name: имя обработчика диалога
    """
    if chat_id in active_conversations and handler_name in active_conversations[chat_id]:
        del active_conversations[chat_id][handler_name]
        logger.info(f"Завершен диалог {handler_name} для пользователя {chat_id}")

        # Удаляем пользователя из словаря, если у него не осталось активных диалогов
        if not active_conversations[chat_id]:
            del active_conversations[chat_id]
    else:
        logger.warning(f"Попытка завершить несуществующий диалог {handler_name} для пользователя {chat_id}")


def end_all_conversations(chat_id: int) -> Set[str]:
    """
    Завершает все активные диалоги для пользователя.

    Args:
        chat_id: ID пользователя

    Returns:
        Set[str]: набор имен завершенных диалогов
    """
    ended_handlers = set()

    if chat_id in active_conversations:
        ended_handlers = set(active_conversations[chat_id].keys())
        logger.info(f"Завершаем все диалоги для пользователя {chat_id}: {ended_handlers}")
        del active_conversations[chat_id]
    else:
        logger.info(f"У пользователя {chat_id} нет активных диалогов для завершения")

    return ended_handlers


def get_active_conversations(chat_id: int) -> Dict[str, Any]:
    """
    Возвращает все активные диалоги пользователя.

    Args:
        chat_id: ID пользователя

    Returns:
        Dict[str, Any]: словарь активных диалогов {handler_name: state}
    """
    conversations = active_conversations.get(chat_id, {})
    logger.debug(f"Активные диалоги пользователя {chat_id}: {conversations}")
    return conversations


def is_conversation_active(chat_id: int, handler_name: str) -> bool:
    """
    Проверяет, активен ли указанный диалог для пользователя.

    Args:
        chat_id: ID пользователя
        handler_name: имя обработчика диалога

    Returns:
        bool: True, если диалог активен
    """
    is_active = chat_id in active_conversations and handler_name in active_conversations[chat_id]
    logger.debug(f"Диалог {handler_name} для пользователя {chat_id} активен: {is_active}")
    return is_active


def has_active_conversations(chat_id: int) -> bool:
    """
    Проверяет, есть ли у пользователя активные диалоги.

    Args:
        chat_id: ID пользователя

    Returns:
        bool: True, если у пользователя есть активные диалоги
    """
    has_conversations = chat_id in active_conversations and bool(active_conversations[chat_id])
    logger.debug(f"У пользователя {chat_id} есть активные диалоги: {has_conversations}")
    return has_conversations


def dump_all_conversations() -> None:
    """
    Выводит в лог все активные диалоги для отладки.
    """
    logger.info(f"Все активные диалоги: {active_conversations}")