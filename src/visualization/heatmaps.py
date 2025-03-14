"""
Модуль для создания тепловых карт и календарных отображений.
"""

import io
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import calendar
import matplotlib.colors as mcolors
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

# Настройка логгирования
logger = logging.getLogger(__name__)

# Настройка стиля matplotlib
plt.style.use('ggplot')


def create_monthly_heatmap(entries: List[Dict[str, Any]], year: int, month: int, column: str) -> io.BytesIO:
    """
    Создает тепловую карту для выбранного показателя по дням месяца.
    
    Args:
        entries: список записей пользователя
        year: год для отображения
        month: месяц для отображения
        column: название показателя для отображения
        
    Returns:
        io.BytesIO: объект с графиком в формате байтов
    """
    try:
        # Преобразование в DataFrame
        df = pd.DataFrame(entries)
        
        # Преобразование столбца даты в datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Фильтрация по году и месяцу
        mask = (df['date'].dt.year == year) & (df['date'].dt.month == month)
        filtered_df = df[mask].copy()
        
        # Преобразование числовых колонок в числовой формат
        if column in filtered_df.columns:
            filtered_df[column] = pd.to_numeric(filtered_df[column], errors='coerce')
        else:
            logger.warning(f"Колонка {column} не найдена в данных")
            return None
        
        # Создание календарной сетки
        cal = calendar.monthcalendar(year, month)
        
        # Подготовка данных для тепловой карты
        data = np.zeros((len(cal), 7)) - 1  # -1 будет обозначать отсутствие данных
        
        # Заполнение данными
        for _, row in filtered_df.iterrows():
            day = row['date'].day
            weekday = row['date'].weekday()
            
            # Поиск позиции дня в календарной сетке
            for week_idx, week in enumerate(cal):
                if day in week and week[weekday] == day:
                    data[week_idx, weekday] = row[column]
                    break
        
        # Создание графика
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Создание маски для скрытия дней, не относящихся к месяцу
        mask = data < 0
        
        # Создание кастомной цветовой карты
        cmap = plt.cm.YlOrRd
        cmap.set_bad('white')
        
        # Создание тепловой карты
        im = ax.imshow(np.ma.array(data, mask=mask), cmap=cmap, vmin=1, vmax=10,
                    aspect='equal', alpha=0.8)
        
        # Настройка меток
        day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        ax.set_xticks(np.arange(len(day_names)))
        ax.set_xticklabels(day_names)
        
        # Убираем метки по оси Y
        ax.set_yticks([])
        
        # Добавление номеров дней
        for week_idx, week in enumerate(cal):
            for day_idx, day in enumerate(week):
                if day != 0:  # Если день принадлежит текущему месяцу
                    # Определяем цвет текста в зависимости от значения
                    if data[week_idx, day_idx] >= 0:
                        text_color = 'black' if data[week_idx, day_idx] < 5 else 'white'
                        value_text = f"{data[week_idx, day_idx]:.0f}"
                    else:
                        text_color = 'gray'
                        value_text = ""
                    
                    # Добавляем номер дня
                    ax.text(day_idx, week_idx, f"{day}\n{value_text}", ha='center', va='center',
                            color=text_color, fontweight='bold')
        
        # Настройка заголовка
        month_name = calendar.month_name[month]
        russian_column_name = get_russian_column_name(column)
        ax.set_title(f"{russian_column_name} - {month_name} {year}")
        
        # Добавление цветовой шкалы
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(russian_column_name)
        
        # Подгонка макета
        plt.tight_layout()
        
        # Сохранение графика в буфер
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        
        # Закрытие фигуры для освобождения памяти
        plt.close(fig)
        
        return buffer
    except Exception as e:
        logger.error(f"Ошибка при создании тепловой карты: {e}")
        raise


def create_mood_distribution(entries: List[Dict[str, Any]], column: str) -> io.BytesIO:
    """
    Создает гистограмму распределения выбранного показателя.
    
    Args:
        entries: список записей пользователя
        column: название показателя для отображения
        
    Returns:
        io.BytesIO: объект с графиком в формате байтов
    """
    try:
        # Преобразование в DataFrame
        df = pd.DataFrame(entries)
        
        # Проверка наличия колонки
        if column not in df.columns:
            logger.warning(f"Колонка {column} не найдена в данных")
            return None
        
        # Преобразование в числовой формат
        df[column] = pd.to_numeric(df[column], errors='coerce')
        
        # Создание гистограммы
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Построение гистограммы
        bins = np.arange(0.5, 11.5, 1)  # Границы между 1 и 10
        n, bins, patches = ax.hist(df[column], bins=bins, edgecolor='black', alpha=0.7)
        
        # Раскраска баров в зависимости от значения
        colors = plt.cm.YlOrRd(np.linspace(0, 1, 10))
        for i, patch in enumerate(patches):
            patch.set_facecolor(colors[i])
        
        # Добавление подписей значений над барами
        for i, count in enumerate(n):
            if count > 0:
                ax.text(i + 1, count + 0.1, str(int(count)), ha='center')
        
        # Настройка осей
        ax.set_xticks(range(1, 11))
        ax.set_xlim(0.5, 10.5)
        ax.set_xlabel('Значение')
        ax.set_ylabel('Количество записей')
        
        # Настройка заголовка
        russian_column_name = get_russian_column_name(column)
        ax.set_title(f'Распределение показателя "{russian_column_name}"')
        
        # Добавление среднего значения
        mean_value = df[column].mean()
        ax.axvline(mean_value, color='red', linestyle='dashed', linewidth=2)
        ax.text(mean_value + 0.1, max(n) * 0.9, f'Среднее: {mean_value:.2f}', 
                color='red', fontweight='bold')
        
        # Подгонка макета
        plt.tight_layout()
        
        # Сохранение графика в буфер
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        
        # Закрытие фигуры для освобождения памяти
        plt.close(fig)
        
        return buffer
    except Exception as e:
        logger.error(f"Ошибка при создании гистограммы распределения: {e}")
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
        'balance': 'Ровность настроения',
        'mania': 'Мания',
        'depression': 'Депрессия',
        'anxiety': 'Тревога',
        'irritability': 'Раздражительность',
        'productivity': 'Работоспособность',
        'sociability': 'Общительность'
    }
    
    return column_names.get(column, column)
