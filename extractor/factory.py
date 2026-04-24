"""
提取器工厂

提供统一的提取器创建接口
"""

from typing import Optional

from .llm_extractor import LLMExtractor
from .nlp_extractor import NLPExtractor
from .statistical_extractor import StatisticalExtractor


class ExtractorFactory:
    """提取器工厂类"""

    _extractors = {
        "llm": LLMExtractor,
        "nlp": NLPExtractor,
        "statistical": StatisticalExtractor,
    }

    @classmethod
    def create(cls, extractor_type: str):
        """
        创建提取器实例

        Args:
            extractor_type: 提取器类型 ("llm", "nlp", "statistical")

        Returns:
            BaseExtractor: 提取器实例

        Raises:
            ValueError: 不支持的提取器类型
        """
        if extractor_type not in cls._extractors:
            raise ValueError(f"不支持的提取器类型: {extractor_type}")
        return cls._extractors[extractor_type]()

    @classmethod
    def create_extractor(cls, extractor_type: str):
        """
        创建提取器实例（向后兼容别名）

        Args:
            extractor_type: 提取器类型

        Returns:
            BaseExtractor: 提取器实例
        """
        return cls.create(extractor_type)

    @classmethod
    def get_available_types(cls):
        """获取所有可用的提取器类型"""
        return list(cls._extractors.keys())
