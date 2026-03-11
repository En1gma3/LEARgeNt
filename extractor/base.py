"""
提取器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class Term:
    """提取的术语"""

    name: str  # 术语名称
    importance: float = 0.0  # 重要性分数 0-1
    source_position: int = 0  # 在原文中的位置
    reason: str = ""  # 提取理由

    def __post_init__(self):
        self.importance = max(0.0, min(1.0, self.importance))


class BaseExtractor(ABC):
    """提取器基类"""

    @abstractmethod
    def extract(self, content: str, max_terms: int = 20) -> List[Term]:
        """
        提取术语

        Args:
            content: 文本内容
            max_terms: 最大提取数量

        Returns:
            List[Term]: 提取的术语列表
        """
        pass

    def _filter_terms(self, terms: List[Term], min_importance: float) -> List[Term]:
        """过滤术语"""
        return [t for t in terms if t.importance >= min_importance]

    def _deduplicate_terms(self, terms: List[Term]) -> List[Term]:
        """去重"""
        seen = set()
        result = []
        for term in terms:
            if term.name.lower() not in seen:
                seen.add(term.name.lower())
                result.append(term)
        return result
