"""
扩展功能模块

包含：
- learning_path: 学习路径
- reminder: 提醒系统
- statistics: 统计分析
- summary: 学习总结与思维导图
- fetcher: 信息获取 (Wikipedia)
"""

from .learning_path import PathManager, LearningPath
from .reminder import ReminderManager, Reminder
from .statistics import StatisticsCollector, DailyStats
from .summary import Summarizer, MindmapGenerator
from .fetcher import FetcherManager, TermInfo

__all__ = [
    'PathManager',
    'LearningPath',
    'ReminderManager',
    'Reminder',
    'StatisticsCollector',
    'DailyStats',
    'Summarizer',
    'MindmapGenerator',
    'FetcherManager',
    'TermInfo',
]
