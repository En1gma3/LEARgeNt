"""
NLP规则提取器

基于NLP的名词短语提取
"""

import re
from typing import List, Set

from .base import BaseExtractor, Term


class NLPExtractor(BaseExtractor):
    """NLP规则提取器"""

    def __init__(self):
        self._nlp = None
        self._stop_words = self._load_stop_words()

    def _load_stop_words(self) -> Set[str]:
        """加载停用词"""
        return {
            # 中文停用词
            "的", "是", "在", "有", "和", "与", "或", "但", "而", "等",
            "了", "着", "过", "把", "被", "让", "给", "向", "从", "到",
            "为", "以", "及", "于", "上", "下", "中", "内", "外", "前", "后",
            "这", "那", "这个", "那个", "我", "你", "他", "她", "它", "我们",
            "你们", "他们", "什么", "怎么", "如何", "为什么", "哪", "哪个",
            # 英文停用词
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "need", "dare",
            "this", "that", "these", "those", "i", "you", "he", "she", "it", "we",
            "they", "what", "which", "who", "whom", "whose", "where", "when",
            "why", "how", "and", "or", "not", "no", "yes", "all", "any", "some",
        }

    def extract(self, content: str, max_terms: int = 20) -> List[Term]:
        """
        使用NLP提取术语

        Args:
            content: 文本内容
            max_terms: 最大提取数量

        Returns:
            List[Term]: 提取的术语列表
        """
        # 尝试使用spaCy
        if self._nlp is None:
            self._init_spacy()

        if self._nlp:
            return self._extract_with_spacy(content, max_terms)

        # 降级到简单规则
        return self._extract_with_rules(content, max_terms)

    def _init_spacy(self):
        """初始化spaCy"""
        try:
            import spacy
            # 尝试加载中文模型
            try:
                self._nlp = spacy.load("zh_core_web_sm")
            except:
                try:
                    self._nlp = spacy.load("en_core_web_sm")
                except:
                    pass
        except ImportError:
            pass

    def _extract_with_spacy(self, content: str, max_terms: int) -> List[Term]:
        """使用spaCy提取"""
        doc = self._nlp(content)

        terms = []
        for idx, token in enumerate(doc):
            # 提取名词和专有名词
            if token.pos_ in ("NOUN", "PROPN") and token.text not in self._stop_words:
                if len(token.text) > 1:
                    terms.append(Term(
                        name=token.text,
                        importance=0.7,
                        source_position=idx,
                        reason=f"名词 (pos={token.pos_})"
                    ))

        # 提取名词短语
        for chunk in doc.noun_chunks:
            if len(chunk.text) > 2:
                terms.append(Term(
                    name=chunk.text,
                    importance=0.8,
                    source_position=chunk.start,
                    reason="名词短语"
                ))

        # 去重和排序
        terms = self._deduplicate_terms(terms)
        terms.sort(key=lambda t: t.importance, reverse=True)

        return terms[:max_terms]

    def _extract_with_rules(self, content: str, max_terms: int) -> List[Term]:
        """使用简单规则提取"""
        # 提取中文术语
        cn_terms = self._extract_chinese_terms(content)

        # 提取英文术语
        en_terms = self._extract_english_terms(content)

        # 合并
        terms = cn_terms + en_terms

        # 去重和排序
        terms = self._deduplicate_terms(terms)
        terms.sort(key=lambda t: t.importance, reverse=True)

        return terms[:max_terms]

    def _extract_chinese_terms(self, content: str) -> List[Term]:
        """提取中文术语"""
        terms = []

        # 尝试使用jieba
        try:
            import jieba
            import jieba.analyse

            # 提取关键词
            keywords = jieba.analyse.extract_tags(content, topK=30, withWeight=True)

            for idx, (word, weight) in enumerate(keywords):
                if word not in self._stop_words and len(word) > 1:
                    terms.append(Term(
                        name=word,
                        importance=weight,
                        source_position=idx,
                        reason="jieba关键词提取"
                    ))

            return terms

        except ImportError:
            pass

        # 降级：简单正则提取
        # 匹配2-8个字符的中文词
        pattern = re.compile(r'[\u4e00-\u9fa5]{2,8}')
        words = pattern.findall(content)

        # 过滤停用词
        words = [w for w in words if w not in self._stop_words]

        # 简单计数
        from collections import Counter
        word_counts = Counter(words)

        for idx, (word, count) in enumerate(word_counts.most_common(30)):
            terms.append(Term(
                name=word,
                importance=min(1.0, count / 10),
                source_position=idx,
                reason="词频统计"
            ))

        return terms

    def _extract_english_terms(self, content: str) -> List[Term]:
        """提取英文术语"""
        terms = []

        # 匹配英文单词组合
        pattern = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b')
        words = pattern.findall(content)

        # 过滤停用词
        words = [w for w in words if w.lower() not in self._stop_words]

        # 简单计数
        from collections import Counter
        word_counts = Counter(words)

        for idx, (word, count) in enumerate(word_counts.most_common(20)):
            terms.append(Term(
                name=word,
                importance=min(1.0, count / 5),
                source_position=idx,
                reason="英文术语提取"
            ))

        return terms
