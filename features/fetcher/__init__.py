"""
信息获取模块

从 Wikipedia 等来源获取术语定义和背景信息
"""

from .base import BaseFetcher, TermInfo
from .wikipedia_fetcher import WikipediaFetcher
from .fetcher_manager import FetcherManager

__all__ = [
    "BaseFetcher",
    "TermInfo",
    "WikipediaFetcher",
    "FetcherManager",
]
