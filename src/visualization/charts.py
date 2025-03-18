"""
Модуль для создания графиков на основе данных пользователя.
Исправленная версия с поддержкой кеширования и удалением параметра quality.
"""

import io
import logging
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

# Настройка логгирования
logger = logging.getLogger(__name__)

# Настройка стиля matplotlib
plt.style.use('ggplot')

# Директория для кеширования визуализаций
CACHE_DIR = "visualization_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Срок жизни кеша (в часах)
CACHE_TTL = 24


def _get_cache_path(cache_key: str) -> str:
    """
    Возвращает путь к файлу кеша для указанного ключа.

    Args:
        cache_key: ключ кеша

    Returns:
        str: путь к файлу кеша
    """
    return os.path.join(CACHE_DIR, f"{cache_key}.png")


def _check_cache(cache_key: str) -> Optional[io.BytesIO]:
    """
    Проверяет наличие визуализации в кеше.

    Args:
        cache_key: ключ кеша

    Returns:
        Optional[io.BytesIO]: данные визуализации или None, если кеш отсутствует или устарел
    """
    cache_path = _get_cache_path(cache_key)

    if os.path.exists(cache_path):
        # Проверяем возраст файла
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        cache_age = datetime.now() - file_time

        if cache_age.total_seconds() < CACHE_TTL * 3600:
            try:
                with open(cache_path, 'rb') as f:
                    data = f.read()

                buffer = io.BytesIO(data)
                buffer.seek(0)
                logger.debug(f"Найден кеш визуализации: {cache_key}")
                return buffer
            except Exception as e:
                logger.error(f"Ошибка при чтении кеша: {e}")

    return None


def _save_to_cache(cache_key: str, buffer: io.BytesIO) -> None:
    """
    Сохраняет визуализацию в кеш.

    Args:
        cache_key: ключ кеша
        buffer: буфер с данными визуализации
    """
    try:
        # Сохраняем позицию в буфере
        pos = buffer.tell()
        buffer.seek(0)

        # Сохраняем в файл
        with open(_get_cache_path(cache_key), 'wb') as f:
            f.write(buffer.read())

        # Восстанавливаем позицию в буфере
        buffer.seek(pos)

        logger.debug(f"Визуализация сохранена в кеш: {cache_key}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении в кеш: {e}")


def create_time_series_chart(entries: List[Dict[str, Any]], columns: List[str], chat_id: int) -> io.BytesIO:
    """
    Создает график временного ряда для выбранных показателей.

    Args:
        entries: список записей пользователя
        columns: список колонок для отображения
        chat_id: ID пользователя для кеширования

    Returns:
        io.BytesIO: объект с графиком в формате байтов
    """
    # Создаем ключ кеша
    columns_key = "_".join(sorted(columns))
    entry_count = len(entries)
    cache_key = f"timeseries_{chat_id}_{columns_key}_{entry_count}"

    # Проверяем наличие в кеше
    cached_viz = _check_cache(cache_key)
    if cached_viz:
        return cached_viz

    try:
        # Преобразование в DataFrame
        df = pd.DataFrame(entries)

        # Преобразование столбца даты в datetime
        df['date'] = pd.to_datetime(df['date'])

        # Сортировка по дате
        df = df.sort_values('date')

        # Преобразование числовых колонок в числовой формат
        for col in columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Создание графика
        fig, ax = plt.subplots(figsize=(10, 6), dpi=80)

        for col in columns:
            if col in df.columns:
                ax.plot(df['date'], df[col], marker='o', linestyle='-', label=get_russian_column_name(col))

        # Настройка графика
        ax.set_title('Динамика показателей во времени')
        ax.set_xlabel('Дата')
        ax.set_ylabel('Значение')
        ax.set_ylim(0, 10.5)  # Все показатели от 1 до 10
        ax.legend()

        # Форматирование оси X (дата)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        plt.xticks(rotation=45)

        # Настройка сетки
        ax.grid(True)

        # Подгонка макета
        plt.tight_layout()

        # Сохранение графика в буфер (без параметров quality и optimize)
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)

        # Закрытие фигуры для освобождения памяти
        plt.close(fig)

        # Сохраняем в кеш
        _save_to_cache(cache_key, buffer)

        return buffer
    except Exception as e:
        logger.error(f"Ошибка при создании графика временного ряда: {e}")
        raise


def create_correlation_matrix(entries: List[Dict[str, Any]], columns: List[str], chat_id: int) -> io.BytesIO:
    """
    Создает матрицу корреляции для выбранных показателей.

    Args:
        entries: список записей пользователя
        columns: список колонок для отображения
        chat_id: ID пользователя для кеширования

    Returns:
        io.BytesIO: объект с графиком в формате байтов
    """
    # Создаем ключ кеша
    entry_count = len(entries)
    cache_key = f"correlation_{chat_id}_{entry_count}"

    # Проверяем наличие в кеше
    cached_viz = _check_cache(cache_key)
    if cached_viz:
        return cached_viz

    try:
        # Преобразование в DataFrame
        df = pd.DataFrame(entries)

        # Выбор только указанных колонок
        numeric_df = df[columns].copy()

        # Преобразование строковых значений в числовые
        for col in numeric_df.columns:
            numeric_df[col] = pd.to_numeric(numeric_df[col], errors='coerce')

        # Расчет корреляции
        corr = numeric_df.corr()

        # Создание тепловой карты
        fig, ax = plt.subplots(figsize=(10, 8), dpi=80)

        # Использование русских названий для меток
        russian_labels = [get_russian_column_name(col) for col in corr.columns]

        # Создание тепловой карты
        cax = ax.matshow(corr, cmap='coolwarm', vmin=-1, vmax=1)

        # Добавление цветовой шкалы
        fig.colorbar(cax)

        # Настройка меток
        ax.set_xticks(range(len(russian_labels)))
        ax.set_yticks(range(len(russian_labels)))
        ax.set_xticklabels(russian_labels, rotation=45, ha='left')
        ax.set_yticklabels(russian_labels)

        # Добавление значений корреляции в ячейки
        for i in range(len(corr.columns)):
            for j in range(len(corr.columns)):
                ax.text(i, j, f"{corr.iloc[j, i]:.2f}", ha='center', va='center',
                        color='black' if abs(corr.iloc[j, i]) < 0.5 else 'white')

        # Настройка заголовка
        ax.set_title('Матрица корреляции показателей')

        # Подгонка макета
        plt.tight_layout()

        # Сохранение графика в буфер (без параметров quality и optimize)
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)

        # Закрытие фигуры для освобождения памяти
        plt.close(fig)

        # Сохраняем в кеш
        _save_to_cache(cache_key, buffer)

        return buffer
    except Exception as e:
        logger.error(f"Ошибка при создании матрицы корреляции: {e}")
        raise


def get_russian_column_name(column: str) -> str:
    """
    Возвращает русское название колонки для отображения на графиках.

    Args:
        column: название колонки в базе данных

    Returns:
        str: русское название колонки
    """
    column_names = {
        'mood': 'Настроение',
        'sleep': 'Сон',
        'balance': 'Ровность',
        'mania': 'Мания',
        'depression': 'Депрессия',
        'anxiety': 'Тревога',
        'irritability': 'Раздражительность',
        'productivity': 'Работоспособность',
        'sociability': 'Общительность'
    }

    return column_names.get(column, column)