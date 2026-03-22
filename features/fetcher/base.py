"""
Fetcher 基类模块

定义信息获取器的基本接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class TermInfo:
    """术语信息数据结构"""

    name: str                           # 术语名称
    definition: str                     # 定义/解释
    summary: str = ""                   # 简短摘要
    description: str = ""               # 一句话描述
    source: str = ""                   # 来源 (wikipedia, web, etc.)
    url: str = ""                      # 来源URL
    language: str = "zh"               # 语言 (zh, en)
    raw_data: Optional[Dict] = None     # 原始数据
    structured_definition: str = ""     # LLM结构化后的定义

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "definition": self.definition,
            "summary": self.summary,
            "description": self.description,
            "source": self.source,
            "url": self.url,
            "language": self.language,
            "structured_definition": self.structured_definition,
        }

    def has_structured(self) -> bool:
        """是否有结构化定义"""
        return bool(self.structured_definition)


class BaseFetcher(ABC):
    """信息获取器基类"""

    @abstractmethod
    def fetch(self, term: str, language: str = "zh") -> Optional[TermInfo]:
        """
        获取术语信息

        Args:
            term: 术语名称
            language: 语言偏好 (zh, en)

        Returns:
            TermInfo: 术语信息，如果获取失败返回 None
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查获取器是否可用

        Returns:
            bool: 是否可用
        """
        pass

    def get_source_name(self) -> str:
        """获取来源名称"""
        return self.__class__.__name__.replace("Fetcher", "").lower()
