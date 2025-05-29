"""
Пакет вспомогательных утилит для работы бота.
"""

# Импортируем только модули без внешних зависимостей по умолчанию
# Другие модули можно импортировать напрямую при необходимости

try:
    from src.utils import date_helpers
except ImportError:
    pass

try:
    from src.utils import formatters
except ImportError:
    pass

try:
    from src.utils import conversation_manager
except ImportError:
    pass

# Модули с внешними зависимостями импортируются только при необходимости
# from src.utils import keyboards  # Требует telegram
