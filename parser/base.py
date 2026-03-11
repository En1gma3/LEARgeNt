"""
解析器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class ParseResult:
    """解析结果"""

    source_type: str  # 来源类型: pdf/news/company/industry/question
    title: str  # 标题
    content: str  # 正文内容
    metadata: Dict[str, Any] = None  # 额外元数据

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseParser(ABC):
    """解析器基类"""

    source_type: str = ""

    @abstractmethod
    def parse(self, input_source: str) -> ParseResult:
        """
        解析输入内容

        Args:
            input_source: 输入来源（文件路径/URL/文本）

        Returns:
            ParseResult: 解析结果
        """
        pass

    def validate_input(self, input_source: str) -> bool:
        """
        验证输入是否有效

        Args:
            input_source: 输入来源

        Returns:
            bool: 是否有效
        """
        return bool(input_source and input_source.strip())

    def preprocess(self, content: str) -> str:
        """
        预处理内容

        Args:
            content: 原始内容

        Returns:
            str: 处理后的内容
        """
        # 去除多余空白
        lines = [line.strip() for line in content.split('\n')]
        return '\n'.join(line for line in lines if line)
