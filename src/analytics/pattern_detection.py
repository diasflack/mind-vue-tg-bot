"""
Модуль для выявления паттернов и закономерностей в записях пользователя.
Анализирует данные и генерирует персонализированные инсайты.
"""

import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import calendar

# Настройка логгирования
logger = logging.getLogger(__name__)


def analyze_trends(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Анализирует тренды в записях пользователя.
    
    Args:
        entries: список записей пользователя
        
    Returns:
        Dict[str, Any]: словарь с результатами анализа трендов
    """
    if not entries or len(entries) < 7:  # Требуется минимум неделя данных
        return {
            'status': 'insufficient_data',
            'message': 'Для анализа трендов нужно не менее 7 записей'
        }
    
    try:
        # Преобразование в DataFrame
        df = pd.DataFrame(entries)
        
        # Преобразование столбца даты в datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Сортировка по дате
        df = df.sort_values('date')
        
        # Преобразование числовых колонок в числовой формат
        numeric_columns = ['mood', 'sleep', 'balance', 'mania', 'depression',
                          'anxiety', 'irritability', 'productivity', 'sociability']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Определение периода данных
        date_range = (df['date'].max() - df['date'].min()).days
        
        # Анализ трендов в различных временных масштабах
        trends = {}
        
        # Если есть данные за месяц или больше
        if date_range >= 28:
            # Ежемесячные тренды
            df['month'] = df['date'].dt.month
            monthly_stats = df.groupby('month')[numeric_columns].mean()
            
            trends['monthly'] = {
                'available': True,
                'best_month': {
                    'month': calendar.month_name[int(monthly_stats['mood'].idxmax())],
                    'value': float(monthly_stats['mood'].max())
                },
                'worst_month': {
                    'month': calendar.month_name[int(monthly_stats['mood'].idxmin())],
                    'value': float(monthly_stats['mood'].min())
                }
            }
        else:
            trends['monthly'] = {'available': False}
        
        # Если есть данные за неделю или больше
        if date_range >= 7:
            # Еженедельные тренды
            df['day_of_week'] = df['date'].dt.dayofweek
            weekly_stats = df.groupby('day_of_week')[numeric_columns].mean()
            
            day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
            
            trends['weekly'] = {
                'available': True,
                'best_day': {
                    'day': day_names[int(weekly_stats['mood'].idxmax())],
                    'value': float(weekly_stats['mood'].max())
                },
                'worst_day': {
                    'day': day_names[int(weekly_stats['mood'].idxmin())],
                    'value': float(weekly_stats['mood'].min())
                }
            }
        else:
            trends['weekly'] = {'available': False}
        
        # Тренды за последние 7 дней
        if len(df) >= 7:
            last_week = df.sort_values('date', ascending=False).head(7)
            
            # Средние значения за последнюю неделю
            last_week_avg = last_week[numeric_columns].mean()
            
            # Тренд настроения (растет, падает или стабильный)
            mood_trend = last_week.sort_values('date')['mood'].tolist()
            if len(mood_trend) >= 3:
                # Используем линейную регрессию для определения тренда
                x = np.arange(len(mood_trend))
                y = np.array(mood_trend)
                z = np.polyfit(x, y, 1)
                slope = z[0]
                
                if slope > 0.3:
                    mood_trend_type = 'upward'
                elif slope < -0.3:
                    mood_trend_type = 'downward'
                else:
                    mood_trend_type = 'stable'
                
                trends['recent'] = {
                    'available': True,
                    'mood_trend': mood_trend_type,
                    'mood_slope': float(slope)
                }
            else:
                trends['recent'] = {'available': False}
        else:
            trends['recent'] = {'available': False}
        
        return {
            'status': 'success',
            'trends': trends
        }
    
    except Exception as e:
        logger.error(f"Ошибка при анализе трендов: {e}")
        return {
            'status': 'error',
            'message': f"Произошла ошибка при анализе трендов: {str(e)}"
        }


def analyze_correlations(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Анализирует корреляции между различными показателями.
    
    Args:
        entries: список записей пользователя
        
    Returns:
        Dict[str, Any]: словарь с результатами анализа корреляций
    """
    if not entries or len(entries) < 5:  # Требуется минимум 5 записей для анализа корреляций
        return {
            'status': 'insufficient_data',
            'message': 'Для анализа корреляций нужно не менее 5 записей'
        }
    
    try:
        # Преобразование в DataFrame
        df = pd.DataFrame(entries)
        
        # Преобразование числовых колонок в числовой формат
        numeric_columns = ['mood', 'sleep', 'balance', 'mania', 'depression',
                         'anxiety', 'irritability', 'productivity', 'sociability']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Расчет корреляции
        corr_matrix = df[numeric_columns].corr()
        
        # Нахождение наиболее сильных положительных и отрицательных корреляций с настроением
        mood_corr = corr_matrix['mood'].drop('mood')  # Удаляем автокорреляцию
        
        top_positive = mood_corr.nlargest(3)
        top_negative = mood_corr.nsmallest(3)
        
        # Формирование результатов
        correlations = {
            'positive': [{'factor': factor, 'correlation': float(corr)} 
                        for factor, corr in top_positive.items() if corr > 0.3],
            'negative': [{'factor': factor, 'correlation': float(corr)} 
                        for factor, corr in top_negative.items() if corr < -0.3]
        }
        
        return {
            'status': 'success',
            'correlations': correlations
        }
    
    except Exception as e:
        logger.error(f"Ошибка при анализе корреляций: {e}")
        return {
            'status': 'error',
            'message': f"Произошла ошибка при анализе корреляций: {str(e)}"
        }


def analyze_patterns(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Выявляет повторяющиеся паттерны в показателях пользователя.
    
    Args:
        entries: список записей пользователя
        
    Returns:
        Dict[str, Any]: словарь с результатами анализа паттернов
    """
    if not entries or len(entries) < 14:  # Требуется минимум две недели данных
        return {
            'status': 'insufficient_data',
            'message': 'Для выявления паттернов нужно не менее 14 записей'
        }
    
    try:
        # Преобразование в DataFrame
        df = pd.DataFrame(entries)
        
        # Преобразование столбца даты в datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Сортировка по дате
        df = df.sort_values('date')
        
        # Преобразование числовых колонок в числовой формат
        numeric_columns = ['mood', 'sleep', 'balance', 'mania', 'depression',
                          'anxiety', 'irritability', 'productivity', 'sociability']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Добавление столбцов с информацией о времени
        df['day_of_week'] = df['date'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6])  # 5=Saturday, 6=Sunday
        df['week_number'] = df['date'].dt.isocalendar().week
        
        # Выявление еженедельных паттернов
        weekday_mood = df.groupby('day_of_week')['mood'].mean()
        weekend_vs_weekday = {
            'weekend_mood': float(df[df['is_weekend']]['mood'].mean()),
            'weekday_mood': float(df[~df['is_weekend']]['mood'].mean())
        }
        
        # Проверка на цикличность настроения
        # Используем автокорреляцию для выявления повторяющихся паттернов
        if len(df) >= 28:  # Требуется минимум 4 недели для анализа цикличности
            mood_data = df['mood'].tolist()
            autocorr = []
            for lag in range(1, 15):  # Проверяем лаги до 2 недель
                if len(mood_data) > lag:
                    # Смещенный список
                    lagged = mood_data[lag:]
                    # Соответствующий оригинальный список
                    original = mood_data[:-lag]
                    # Расчет корреляции
                    corr = np.corrcoef(original, lagged)[0, 1]
                    autocorr.append((lag, corr))
            
            # Находим лаги с высокой корреляцией (выше 0.5)
            high_corr_lags = [(lag, corr) for lag, corr in autocorr if corr > 0.5]
            
            if high_corr_lags:
                # Сортировка по уровню корреляции (от высокой к низкой)
                high_corr_lags.sort(key=lambda x: x[1], reverse=True)
                
                # Преобразование лага в дни для лучшего понимания
                cyclicality = {
                    'detected': True,
                    'cycle_days': high_corr_lags[0][0],
                    'correlation': float(high_corr_lags[0][1])
                }
            else:
                cyclicality = {'detected': False}
        else:
            cyclicality = {'detected': False, 'message': 'Недостаточно данных для анализа цикличности'}
        
        return {
            'status': 'success',
            'patterns': {
                'weekday_mood': {name: float(value) for name, value in weekday_mood.items()},
                'weekend_vs_weekday': weekend_vs_weekday,
                'cyclicality': cyclicality
            }
        }
    
    except Exception as e:
        logger.error(f"Ошибка при выявлении паттернов: {e}")
        return {
            'status': 'error',
            'message': f"Произошла ошибка при выявлении паттернов: {str(e)}"
        }


def _analyze_correlation_insights(corr_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Анализирует результаты корреляций и генерирует соответствующие инсайты.

    Args:
        corr_results: результаты анализа корреляций

    Returns:
        List[Dict[str, Any]]: список инсайтов о корреляциях
    """
    insights = []

    if corr_results['status'] != 'success':
        return insights

    # Добавление инсайтов о положительных корреляциях
    for pos_corr in corr_results['correlations']['positive']:
        factor = pos_corr['factor']
        corr = pos_corr['correlation']

        if corr > 0.6:
            factor_ru = get_russian_factor_name(factor)
            insights.append({
                'type': 'correlation_positive',
                'strength': 'strong',
                'factor': factor,
                'message': f"Обнаружена сильная положительная связь между {factor_ru} и вашим настроением "
                          f"(коэффициент корреляции: {corr:.2f}). Обратите на это внимание!"
            })

    # Добавление инсайтов о отрицательных корреляциях
    for neg_corr in corr_results['correlations']['negative']:
        factor = neg_corr['factor']
        corr = neg_corr['correlation']

        if corr < -0.6:
            factor_ru = get_russian_factor_name(factor)
            insights.append({
                'type': 'correlation_negative',
                'strength': 'strong',
                'factor': factor,
                'message': f"Обнаружена сильная отрицательная связь между {factor_ru} и вашим настроением "
                          f"(коэффициент корреляции: {corr:.2f}). Это может быть важным фактором!"
            })

    return insights


def _analyze_trend_insights(trend_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Анализирует результаты трендов и генерирует соответствующие инсайты.

    Args:
        trend_results: результаты анализа трендов

    Returns:
        List[Dict[str, Any]]: список инсайтов о трендах
    """
    insights = []

    if trend_results['status'] != 'success':
        return insights

    trends = trend_results['trends']

    # Инсайты о недельных трендах
    if trends['weekly']['available']:
        best_day = trends['weekly']['best_day']['day']
        worst_day = trends['weekly']['worst_day']['day']

        if trends['weekly']['best_day']['value'] - trends['weekly']['worst_day']['value'] > 2:
            insights.append({
                'type': 'weekly_pattern',
                'strength': 'medium',
                'message': f"В среднем, ваше настроение лучше всего по {best_day.lower()}ам "
                          f"и хуже всего по {worst_day.lower()}ам. Возможно, стоит планировать важные "
                          f"дела с учетом этой закономерности."
            })

    # Инсайты о недавних трендах
    if trends['recent']['available']:
        mood_trend = trends['recent']['mood_trend']

        if mood_trend == 'upward':
            insights.append({
                'type': 'recent_trend',
                'trend': 'positive',
                'message': "За последнюю неделю ваше настроение имеет тенденцию к улучшению. "
                          "Продолжайте в том же духе!"
            })
        elif mood_trend == 'downward':
            insights.append({
                'type': 'recent_trend',
                'trend': 'negative',
                'message': "За последнюю неделю ваше настроение имеет тенденцию к ухудшению. "
                          "Может быть, стоит обратить внимание на факторы, которые могут влиять на это."
            })

    return insights


def _analyze_pattern_insights(pattern_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Анализирует результаты паттернов и генерирует соответствующие инсайты.

    Args:
        pattern_results: результаты анализа паттернов

    Returns:
        List[Dict[str, Any]]: список инсайтов о паттернах
    """
    insights = []

    if pattern_results['status'] != 'success':
        return insights

    patterns = pattern_results['patterns']

    # Инсайты о выходных vs будни
    weekend_mood = patterns['weekend_vs_weekday']['weekend_mood']
    weekday_mood = patterns['weekend_vs_weekday']['weekday_mood']

    if weekend_mood - weekday_mood > 2:
        insights.append({
            'type': 'weekend_effect',
            'effect': 'positive',
            'message': "Ваше настроение значительно лучше в выходные, чем в будни. "
                      "Возможно, рабочие или учебные факторы влияют на ваше самочувствие."
        })
    elif weekday_mood - weekend_mood > 2:
        insights.append({
            'type': 'weekend_effect',
            'effect': 'negative',
            'message': "Интересно, что ваше настроение лучше в будни, чем в выходные. "
                      "Возможно, вам помогает структурированный распорядок дня."
        })

    # Инсайты о цикличности
    if patterns['cyclicality']['detected']:
        cycle_days = patterns['cyclicality']['cycle_days']

        insights.append({
            'type': 'cyclicality',
            'cycle_days': cycle_days,
            'message': f"В ваших данных обнаружена периодичность примерно в {cycle_days} дней. "
                      f"Это может быть связано с биологическими циклами или регулярными событиями в вашей жизни."
        })

    return insights


def _analyze_general_recommendations(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Анализирует общие показатели и генерирует рекомендации.

    Args:
        entries: список записей пользователя

    Returns:
        List[Dict[str, Any]]: список общих рекомендаций
    """
    insights = []

    # Преобразование в DataFrame
    df = pd.DataFrame(entries)

    # Преобразование числовых колонок в числовой формат
    numeric_columns = ['mood', 'sleep', 'balance', 'mania', 'depression',
                      'anxiety', 'irritability', 'productivity', 'sociability']

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Инсайт о сне
    if 'sleep' in df.columns and 'mood' in df.columns:
        sleep_mood_corr = df[['sleep', 'mood']].corr().iloc[0, 1]
        if sleep_mood_corr > 0.4:
            avg_sleep = df['sleep'].mean()
            if avg_sleep < 5:
                insights.append({
                    'type': 'sleep_recommendation',
                    'strength': 'strong',
                    'message': "Данные показывают, что ваш сон тесно связан с настроением, но в среднем вы оцениваете "
                              "качество сна довольно низко. Улучшение сна может значительно повысить ваше общее самочувствие."
                })

    # Инсайт о тревоге
    if 'anxiety' in df.columns and df['anxiety'].mean() > 7:
        insights.append({
            'type': 'anxiety_alert',
            'strength': 'medium',
            'message': "Ваш средний уровень тревоги довольно высок. Стоит рассмотреть методы управления тревогой, "
                      "такие как медитация, дыхательные упражнения или консультация со специалистом."
        })

    return insights


def generate_insights(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Генерирует персонализированные инсайты на основе анализа данных.

    Args:
        entries: список записей пользователя

    Returns:
        Dict[str, Any]: словарь с персонализированными инсайтами
    """
    if not entries or len(entries) < 7:
        return {
            'status': 'insufficient_data',
            'message': 'Для генерации инсайтов нужно не менее 7 записей'
        }

    insights = []

    try:
        # Анализ корреляций
        corr_results = analyze_correlations(entries)
        insights.extend(_analyze_correlation_insights(corr_results))

        # Анализ трендов
        trend_results = analyze_trends(entries)
        insights.extend(_analyze_trend_insights(trend_results))

        # Анализ паттернов
        pattern_results = analyze_patterns(entries)
        insights.extend(_analyze_pattern_insights(pattern_results))

        # Общие рекомендации
        insights.extend(_analyze_general_recommendations(entries))
        
        return {
            'status': 'success',
            'insights': insights
        }
    
    except Exception as e:
        logger.error(f"Ошибка при генерации инсайтов: {e}")
        return {
            'status': 'error',
            'message': f"Произошла ошибка при генерации инсайтов: {str(e)}"
        }


def get_russian_factor_name(factor: str) -> str:
    """
    Возвращает русское название фактора.
    
    Args:
        factor: название фактора на английском
        
    Returns:
        str: русское название фактора
    """
    factor_names = {
        'mood': 'настроением',
        'sleep': 'качеством сна',
        'balance': 'ровностью настроения',
        'mania': 'уровнем мании',
        'depression': 'уровнем депрессии',
        'anxiety': 'уровнем тревоги',
        'irritability': 'раздражительностью',
        'productivity': 'работоспособностью',
        'sociability': 'общительностью'
    }
    
    return factor_names.get(factor, factor)


def format_analytics_summary(entries: List[Dict[str, Any]]) -> str:
    """
    Форматирует сводку аналитики для отображения пользователю.
    
    Args:
        entries: список записей пользователя
        
    Returns:
        str: форматированная сводка аналитики
    """
    if not entries or len(entries) < 7:
        return "Недостаточно данных для аналитики. Продолжайте добавлять записи (нужно не менее 7)."
    
    summary = "📊 *Аналитика паттернов и инсайты*\n\n"
    
    # Генерация инсайтов
    insights_result = generate_insights(entries)
    
    if insights_result['status'] == 'success' and insights_result['insights']:
        summary += "*Обнаруженные закономерности:*\n"
        
        for i, insight in enumerate(insights_result['insights'], 1):
            summary += f"{i}. {insight['message']}\n\n"
    else:
        summary += "Пока не удалось обнаружить значимых закономерностей. Продолжайте добавлять записи для более точного анализа.\n\n"
    
    # Анализ корреляций
    corr_results = analyze_correlations(entries)
    
    if corr_results['status'] == 'success':
        correlations = corr_results['correlations']
        
        if correlations['positive'] or correlations['negative']:
            summary += "*Основные факторы, влияющие на настроение:*\n"
            
            # Положительные корреляции
            for corr in correlations['positive']:
                factor = get_russian_factor_name(corr['factor'])
                summary += f"✅ {factor.capitalize()} (+{corr['correlation']:.2f})\n"
            
            # Отрицательные корреляции
            for corr in correlations['negative']:
                factor = get_russian_factor_name(corr['factor'])
                summary += f"❌ {factor.capitalize()} ({corr['correlation']:.2f})\n"
            
            summary += "\n"
    
    # Анализ трендов
    trend_results = analyze_trends(entries)
    
    if trend_results['status'] == 'success':
        trends = trend_results['trends']
        
        if trends['weekly']['available']:
            summary += "*Еженедельные паттерны:*\n"
            summary += f"Лучший день: {trends['weekly']['best_day']['day']} ({trends['weekly']['best_day']['value']:.1f}/10)\n"
            summary += f"Худший день: {trends['weekly']['worst_day']['day']} ({trends['weekly']['worst_day']['value']:.1f}/10)\n\n"
    
    summary += "\nПродолжайте отслеживать свое настроение для получения более точных и персонализированных инсайтов!"
    
    return summary
