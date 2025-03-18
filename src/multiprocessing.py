"""
Модуль для выполнения тяжелых операций в отдельных процессах.
Позволяет использовать несколько ядер процессора для параллельной обработки.
"""

import logging
import concurrent.futures
from typing import Callable, Any, Dict, List, Optional, TypeVar, Generic, Tuple
import functools
import os
import time
from datetime import datetime, timedelta
import hashlib
import json
import traceback
import psutil

# Настройка логгирования
logger = logging.getLogger(__name__)

# Тип возвращаемого значения для обобщенных функций
T = TypeVar('T')

# Максимальное количество рабочих процессов
MAX_WORKERS = max(2, os.cpu_count() or 2)

# Пул процессов для выполнения тяжелых задач
_process_pool = None

# Кеш результатов выполнения функций
_results_cache = {}

# Срок жизни кеша результатов (в секундах)
RESULTS_CACHE_TTL = 1800  # 30 минут

# Счетчик выполненных задач
_task_counter = 0
_task_times = {}


def initialize_process_pool():
    """
    Инициализирует пул процессов для выполнения тяжелых задач.
    """
    global _process_pool
    if _process_pool is None:
        # Используем контекстный менеджер для более надежного управления ресурсами
        _process_pool = concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS)
        logger.info(f"Инициализирован пул процессов с {MAX_WORKERS} рабочими")


def shutdown_process_pool():
    """
    Корректно завершает работу пула процессов.
    """
    global _process_pool
    if _process_pool is not None:
        _process_pool.shutdown(wait=True)
        _process_pool = None
        logger.info("Пул процессов корректно завершен")


def process_task(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Выполняет задачу в отдельном процессе.

    Args:
        func: функция для выполнения
        *args, **kwargs: аргументы функции

    Returns:
        T: результат выполнения функции
    """
    global _process_pool, _task_counter

    # Инициализация пула, если он не создан
    if _process_pool is None:
        initialize_process_pool()

    # Увеличиваем счетчик задач
    _task_counter += 1
    task_id = _task_counter

    # Логируем начало выполнения задачи
    start_time = time.time()
    logger.debug(f"Задача #{task_id}: Запуск {func.__name__}")

    try:
        # Отправляем задачу на выполнение в отдельном процессе
        future = _process_pool.submit(func, *args, **kwargs)

        # Ждем результат
        result = future.result()

        # Логируем завершение задачи
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Задача #{task_id}: Завершено {func.__name__} за {execution_time:.2f} сек")

        # Сохраняем время выполнения для статистики
        if func.__name__ not in _task_times:
            _task_times[func.__name__] = []
        _task_times[func.__name__].append(execution_time)

        return result

    except concurrent.futures.TimeoutError:
        logger.error(f"Задача #{task_id}: Превышено время ожидания функции {func.__name__}")
        raise
    except Exception as e:
        logger.error(f"Задача #{task_id}: Ошибка при выполнении функции {func.__name__}: {e}")
        logger.error(f"Трассировка: {traceback.format_exc()}")
        raise


def _create_cache_key(func, args, kwargs, cache_key_func=None):
    """
    Создает ключ для кеширования результатов функции.

    Args:
        func: функция
        args: позиционные аргументы
        kwargs: именованные аргументы
        cache_key_func: пользовательская функция для создания ключа

    Returns:
        str: ключ для кеширования
    """
    if cache_key_func:
        return cache_key_func(*args, **kwargs)

    # Преобразуем аргументы в строковое представление для хеширования
    args_str = str(args)
    kwargs_str = str(sorted(kwargs.items()))

    key_str = f"{func.__module__}.{func.__name__}:{args_str}:{kwargs_str}"
    return hashlib.md5(key_str.encode()).hexdigest()


def run_in_process(timeout: Optional[int] = None, cache_key: Optional[Callable] = None,
                  cache_ttl: Optional[int] = None):
    """
    Декоратор для выполнения функции в отдельном процессе.

    Args:
        timeout: максимальное время выполнения в секундах
        cache_key: функция для генерации ключа кеша (принимает те же аргументы, что и декорируемая функция)
        cache_ttl: время жизни кеша в секундах (по умолчанию RESULTS_CACHE_TTL)

    Returns:
        Callable: декорированная функция
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Проверка кеша, если включено кеширование
            if cache_key is not None:
                key = _create_cache_key(func, args, kwargs, cache_key)

                if key in _results_cache:
                    cache_entry = _results_cache[key]
                    current_time = time.time()

                    # Используем кешированный результат, если он не устарел
                    if current_time - cache_entry["timestamp"] < (cache_ttl or RESULTS_CACHE_TTL):
                        logger.debug(f"Используется кешированный результат для {func.__name__}")
                        return cache_entry["result"]

            global _process_pool

            # Инициализация пула, если он не создан
            if _process_pool is None:
                initialize_process_pool()

            # Увеличиваем счетчик задач
            global _task_counter
            _task_counter += 1
            task_id = _task_counter

            # Логируем начало выполнения задачи
            start_time = time.time()
            logger.debug(f"Задача #{task_id}: Запуск {func.__name__} в отдельном процессе")

            try:
                # Отправляем задачу на выполнение в отдельном процессе
                future = _process_pool.submit(func, *args, **kwargs)

                # Ждем результат с таймаутом, если он указан
                if timeout is not None:
                    result = future.result(timeout=timeout)
                else:
                    result = future.result()

                # Логируем завершение задачи
                end_time = time.time()
                execution_time = end_time - start_time
                logger.debug(f"Задача #{task_id}: Завершено {func.__name__} за {execution_time:.2f} сек")

                # Сохраняем время выполнения для статистики
                if func.__name__ not in _task_times:
                    _task_times[func.__name__] = []
                _task_times[func.__name__].append(execution_time)

                # Кешируем результат, если включено кеширование
                if cache_key is not None:
                    key = _create_cache_key(func, args, kwargs, cache_key)
                    _results_cache[key] = {
                        "result": result,
                        "timestamp": time.time()
                    }

                return result

            except concurrent.futures.TimeoutError:
                logger.error(f"Задача #{task_id}: Превышено время ожидания функции {func.__name__}")
                raise
            except Exception as e:
                logger.error(f"Задача #{task_id}: Ошибка при выполнении функции {func.__name__}: {e}")
                logger.error(f"Трассировка: {traceback.format_exc()}")
                raise

        # Добавляем атрибут для доступа к оригинальной функции
        wrapper.original_func = func
        return wrapper

    return decorator


def cleanup_results_cache():
    """
    Очищает устаревшие результаты из кеша.
    """
    current_time = time.time()
    expired_keys = []

    for key, cache_entry in _results_cache.items():
        if current_time - cache_entry["timestamp"] > RESULTS_CACHE_TTL:
            expired_keys.append(key)

    for key in expired_keys:
        del _results_cache[key]

    if expired_keys:
        logger.debug(f"Очищено {len(expired_keys)} устаревших результатов из кеша")


def clear_results_cache():
    """
    Полностью очищает кеш результатов.
    """
    _results_cache.clear()
    logger.info("Кеш результатов полностью очищен")


def get_process_stats():
    """
    Возвращает статистику по выполнению задач в пуле процессов.

    Returns:
        Dict: статистика выполнения задач
    """
    stats = {
        "total_tasks": _task_counter,
        "function_stats": {},
        "cache_size": len(_results_cache),
        "system_resources": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024)
        }
    }

    # Рассчитываем статистику по функциям
    for func_name, times in _task_times.items():
        if times:
            stats["function_stats"][func_name] = {
                "calls": len(times),
                "avg_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times),
                "total_time": sum(times)
            }

    return stats


def log_process_stats():
    """
    Логирует статистику выполнения задач в пуле процессов.
    """
    stats = get_process_stats()

    logger.info(f"Статистика мультипроцессинга:")
    logger.info(f"  Всего задач: {stats['total_tasks']}")
    logger.info(f"  Размер кеша: {stats['cache_size']} элементов")
    logger.info(f"  CPU: {stats['system_resources']['cpu_percent']}%, Память: {stats['system_resources']['memory_percent']}%")

    for func_name, func_stats in stats["function_stats"].items():
        logger.info(f"  Функция {func_name}:")
        logger.info(f"    Вызовов: {func_stats['calls']}")
        logger.info(f"    Среднее время: {func_stats['avg_time']:.2f} сек")
        logger.info(f"    Мин/Макс: {func_stats['min_time']:.2f}/{func_stats['max_time']:.2f} сек")


# Примеры использования декоратора для тяжелых функций

@run_in_process(timeout=30)
def heavy_encryption_task(data: Dict[str, Any], encryption_key: bytes) -> str:
    """
    Пример тяжелой задачи шифрования, выполняемой в отдельном процессе.

    Args:
        data: данные для шифрования
        encryption_key: ключ шифрования

    Returns:
        str: зашифрованные данные в формате base64
    """
    import base64
    import json
    from cryptography.fernet import Fernet

    # Преобразование данных в JSON
    data_json = json.dumps(data).encode('utf-8')

    # Создание шифра
    cipher = Fernet(encryption_key)

    # Шифрование данных
    encrypted_data = cipher.encrypt(data_json)

    # Возврат данных в формате base64
    return base64.b64encode(encrypted_data).decode('utf-8')


def generate_cache_key_for_entries(entries: List[Dict[str, Any]], chat_id: int) -> str:
    """
    Генерирует ключ кеша для функций обработки записей.

    Args:
        entries: список записей
        chat_id: ID пользователя

    Returns:
        str: ключ кеша
    """
    # Используем хеш от количества записей и последней даты
    if not entries:
        return f"user_{chat_id}_empty"

    # Сортируем записи по дате (если есть)
    try:
        sorted_entries = sorted(entries, key=lambda x: x.get('date', ''), reverse=True)
        last_entry = sorted_entries[0]
        entry_count = len(entries)
        return f"user_{chat_id}_entries_{entry_count}_last_{last_entry.get('date', '')}"
    except:
        # Если сортировка не удалась, используем только количество записей
        return f"user_{chat_id}_entries_{len(entries)}"


@run_in_process(cache_key=generate_cache_key_for_entries, cache_ttl=3600)
def analyze_entries(entries: List[Dict[str, Any]], chat_id: int) -> Dict[str, Any]:
    """
    Пример тяжелой аналитической задачи с кешированием результатов.

    Args:
        entries: список записей пользователя
        chat_id: ID пользователя

    Returns:
        Dict[str, Any]: результаты анализа
    """
    import pandas as pd
    import numpy as np

    # Проверка наличия данных
    if not entries:
        return {"status": "no_data", "message": "Нет данных для анализа"}

    # Преобразование в DataFrame
    df = pd.DataFrame(entries)

    # Преобразование строковых значений в числовые
    numeric_columns = ['mood', 'sleep', 'balance', 'mania', 'depression',
                      'anxiety', 'irritability', 'productivity', 'sociability']

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Базовая статистика
    stats = {}
    for col in numeric_columns:
        if col in df.columns and not df[col].isna().all():
            stats[col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "std": float(df[col].std())
            }

    # Анализ корреляций
    correlations = {}
    if len(df) >= 5:  # Минимальное количество записей для корреляции
        corr_matrix = df[numeric_columns].corr().round(2)

        # Преобразование корреляционной матрицы в словарь
        for col1 in corr_matrix.columns:
            correlations[col1] = {}
            for col2 in corr_matrix.columns:
                correlations[col1][col2] = float(corr_matrix.loc[col1, col2])

    # Анализ трендов
    trends = {}
    if 'date' in df.columns and len(df) >= 7:  # Минимум неделя данных
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # Линейные тренды для каждого показателя
        for col in numeric_columns:
            if col in df.columns and not df[col].isna().all():
                # Простая линейная регрессия
                x = np.arange(len(df))
                y = df[col].values
                # Избегаем NaN значений
                mask = ~np.isnan(y)
                if sum(mask) >= 2:  # Нужно минимум 2 точки для линии
                    x_valid = x[mask]
                    y_valid = y[mask]
                    slope, intercept = np.polyfit(x_valid, y_valid, 1)
                    trends[col] = {
                        "slope": float(slope),
                        "intercept": float(intercept),
                        "direction": "upward" if slope > 0.1 else ("downward" if slope < -0.1 else "stable")
                    }

    # Формирование итогового анализа
    analysis_results = {
        "status": "success",
        "entry_count": len(df),
        "date_range": {
            "start": df['date'].min().strftime('%Y-%m-%d') if 'date' in df.columns else None,
            "end": df['date'].max().strftime('%Y-%m-%d') if 'date' in df.columns else None
        },
        "statistics": stats,
        "correlations": correlations,
        "trends": trends
    }

    return analysis_results


@run_in_process(timeout=15)
def create_visualization(entries: List[Dict[str, Any]], chat_id: int,
                        viz_type: str, params: Dict[str, Any]) -> bytes:
    """
    Пример тяжелой задачи визуализации, выполняемой в отдельном процессе.

    Args:
        entries: список записей пользователя
        chat_id: ID пользователя
        viz_type: тип визуализации
        params: параметры визуализации

    Returns:
        bytes: изображение в байтовом формате
    """
    import io
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np

    # Преобразование в DataFrame
    df = pd.DataFrame(entries)

    # Преобразование столбца даты в datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

    # Преобразование числовых колонок
    numeric_columns = ['mood', 'sleep', 'balance', 'mania', 'depression',
                      'anxiety', 'irritability', 'productivity', 'sociability']

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Создание графика в зависимости от типа
    fig, ax = plt.subplots(figsize=(10, 6))

    if viz_type == "line":
        # Линейный график
        columns_to_plot = params.get('columns', ['mood'])
        for col in columns_to_plot:
            if col in df.columns:
                ax.plot(df['date'], df[col], marker='o', label=col)

        ax.set_title("Динамика показателей")
        ax.set_xlabel("Дата")
        ax.set_ylabel("Значение")
        ax.legend()
        ax.grid(True)

    elif viz_type == "heatmap":
        # Тепловая карта корреляций
        corr_matrix = df[numeric_columns].corr()
        im = ax.imshow(corr_matrix, cmap='coolwarm')

        # Настройка меток
        ax.set_xticks(np.arange(len(numeric_columns)))
        ax.set_yticks(np.arange(len(numeric_columns)))
        ax.set_xticklabels(numeric_columns, rotation=45, ha="right")
        ax.set_yticklabels(numeric_columns)

        # Добавление значений в ячейки
        for i in range(len(numeric_columns)):
            for j in range(len(numeric_columns)):
                ax.text(j, i, f"{corr_matrix.iloc[i, j]:.2f}",
                        ha="center", va="center",
                        color="white" if abs(corr_matrix.iloc[i, j]) > 0.5 else "black")

        ax.set_title("Корреляция показателей")
        plt.colorbar(im)

    # Сохранение графика в байтовый буфер
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)

    # Закрытие фигуры для освобождения памяти
    plt.close(fig)

    return buffer.getvalue()