"""
信息搜集模块

提供网页抓取、搜索、结果整合功能。
"""

from .web import WebFetcher, FallbackFetcher, SearchResult

__all__ = [
    'WebFetcher',
    'FallbackFetcher',
    'SearchResult',
]
