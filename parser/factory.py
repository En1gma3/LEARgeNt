"""
解析器工厂
"""

from typing import Dict, Type

from .base import BaseParser
from .pdf_parser import PDFParser
from .news_parser import NewsParser
from .company_parser import CompanyParser
from .industry_parser import IndustryParser
from .question_parser import QuestionParser


class ParserFactory:
    """解析器工厂"""

    _parsers: Dict[str, BaseParser] = {}

    @classmethod
    def get_parser(cls, source_type: str) -> BaseParser:
        """
        获取对应类型的解析器

        Args:
            source_type: 来源类型 (paper/news/company/industry/question)

        Returns:
            BaseParser: 解析器实例
        """
        # 检查缓存
        if source_type in cls._parsers:
            return cls._parsers[source_type]

        # 创建新的解析器
        parser = cls._create_parser(source_type)
        cls._parsers[source_type] = parser

        return parser

    @classmethod
    def _create_parser(cls, source_type: str) -> BaseParser:
        """创建解析器"""
        parser_map: Dict[str, Type[BaseParser]] = {
            "paper": PDFParser,
            "pdf": PDFParser,
            "news": NewsParser,
            "company": CompanyParser,
            "industry": IndustryParser,
            "question": QuestionParser,
        }

        parser_class = parser_map.get(source_type.lower())
        if parser_class is None:
            raise ValueError(f"不支持的来源类型: {source_type}")

        return parser_class()

    @classmethod
    def parse(cls, source_type: str, input_source: str):
        """
        便捷方法：直接解析

        Args:
            source_type: 来源类型
            input_source: 输入来源

        Returns:
            ParseResult: 解析结果
        """
        parser = cls.get_parser(source_type)
        return parser.parse(input_source)

    @classmethod
    def detect_source_type(cls, input_source: str) -> str:
        """
        自动检测输入来源类型

        Args:
            input_source: 输入来源

        Returns:
            str: 来源类型
        """
        import re

        input_source = input_source.strip()

        # URL检测
        if re.match(r'^https?://', input_source):
            return "news"

        # 文件路径检测
        if re.match(r'^.*\.(pdf|docx?|txt|md)$', input_source, re.IGNORECASE):
            if input_source.lower().endswith('.pdf'):
                return "paper"
            return "text"

        # 问题检测
        question_keywords = ["什么是", "为什么", "如何", "怎么", "?", "？"]
        if any(kw in input_source for kw in question_keywords):
            return "question"

        # 公司/行业检测（需要更智能的判断）
        # 这里简化处理，默认返回question
        return "question"

    @classmethod
    def clear_cache(cls):
        """清除解析器缓存"""
        cls._parsers.clear()

    @classmethod
    def create(cls, source_type: str) -> BaseParser:
        """创建解析器的便捷方法"""
        return cls.get_parser(source_type)
