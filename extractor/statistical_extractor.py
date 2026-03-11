"""
统计方法提取器

使用TF-IDF和TextRank算法提取关键词
"""

import re
import math
from typing import List, Dict, Set
from collections import Counter, defaultdict

from .base import BaseExtractor, Term


class StatisticalExtractor(BaseExtractor):
    """统计方法提取器"""

    def __init__(self):
        self._stop_words = self._load_stop_words()

    def _load_stop_words(self) -> Set[str]:
        return {
            "的", "是", "在", "有", "和", "与", "或", "但", "而", "等",
            "了", "着", "过", "把", "被", "让", "给", "向", "从", "到",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
        }

    def extract(self, content: str, max_terms: int = 20) -> List[Term]:
        """
        使用统计方法提取术语

        Args:
            content: 文本内容
            max_terms: 最大提取数量

        Returns:
            List[Term]: 提取的术语列表
        """
        # 尝试使用TextRank
        terms = self._textrank_extract(content, max_terms)

        if terms:
            return terms

        # 降级到TF-IDF
        return self._tfidf_extract(content, max_terms)

    def _textrank_extract(self, content: str, max_terms: int) -> List[Term]:
        """TextRank算法提取"""
        try:
            # 尝试使用jieba
            import jieba
            import jieba.analyse

            keywords = jieba.analyse.textrank(content, topK=max_terms, withWeight=True)

            terms = []
            for idx, (word, weight) in enumerate(keywords):
                if word not in self._stop_words and len(word) > 1:
                    terms.append(Term(
                        name=word,
                        importance=weight,
                        source_position=idx,
                        reason="TextRank"
                    ))

            return terms

        except ImportError:
            return []

    def _tfidf_extract(self, content: str, max_terms: int) -> List[Term]:
        """简单的TF-IDF提取"""
        # 分词
        words = self._tokenize(content)

        # 计算词频
        word_freq = Counter(words)

        # 计算TF
        total = sum(word_freq.values())
        tf = {w: freq / total for w, freq in word_freq.items()}

        # 简单的IDF（假设单文档）
        # 这里简化为只使用TF
        terms = []
        for idx, (word, freq) in enumerate(word_freq.most_common(max_terms * 2)):
            if word not in self._stop_words and len(word) > 1:
                terms.append(Term(
                    name=word,
                    importance=tf[word],
                    source_position=idx,
                    reason="TF"
                ))

        # 去重
        terms = self._deduplicate_terms(terms)

        return terms[:max_terms]

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 尝试jieba
        try:
            import jieba
            return list(jieba.cut(text))
        except ImportError:
            pass

        # 降级：简单分词
        # 中文
        cn_pattern = re.compile(r'[\u4e00-\u9fa5]+')
        cn_words = cn_pattern.findall(text)

        # 英文
        en_pattern = re.compile(r'[a-zA-Z]+')
        en_words = en_pattern.findall(text)

        return cn_words + en_words
