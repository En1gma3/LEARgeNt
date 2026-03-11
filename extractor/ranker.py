"""
术语重要性排序器

综合多种方法对提取的术语进行排序
"""

from typing import List

from .base import Term


class TermRanker:
    """术语重要性排序器"""

    def __init__(self, weights: dict = None):
        """
        初始化

        Args:
            weights: 各因子权重
        """
        self.weights = weights or {
            "position": 0.3,  # 位置权重
            "frequency": 0.3,  # 频率权重
            "length": 0.2,     # 长度权重
            "specificity": 0.2,  # 专业性权重
        }

    def rank(self, terms: List[Term], context: dict = None) -> List[Term]:
        """
        对术语进行综合排序

        Args:
            terms: 术语列表
            context: 上下文信息（已学习词汇、用户偏好等）

        Returns:
            List[Term]: 排序后的术语列表
        """
        if not terms:
            return []

        context = context or {}

        # 计算各维度分数
        scores = []
        for term in terms:
            score = self._calculate_score(term, context)
            scores.append((term, score))

        # 按分数排序
        scores.sort(key=lambda x: x[1], reverse=True)

        # 更新术语的重要性分数
        max_score = scores[0][1] if scores else 1.0
        for term, score in scores:
            if max_score > 0:
                term.importance = score / max_score

        return [t for t, _ in scores]

    def _calculate_score(self, term: Term, context: dict) -> float:
        """计算综合分数"""
        score = 0.0

        # 位置分数
        position_score = self._calculate_position_score(term)
        score += position_score * self.weights.get("position", 0.3)

        # 频率分数（使用importance作为频率）
        frequency_score = term.importance
        score += frequency_score * self.weights.get("frequency", 0.3)

        # 长度分数
        length_score = self._calculate_length_score(term)
        score += length_score * self.weights.get("length", 0.2)

        # 专业性分数
        specificity_score = self._calculate_specificity_score(term)
        score += specificity_score * self.weights.get("specificity", 0.2)

        return score

    def _calculate_position_score(self, term: Term) -> float:
        """计算位置分数（越靠前越高）"""
        position = term.source_position
        if position == 0:
            return 1.0
        # 简单的衰减函数
        return 1.0 / (1.0 + 0.1 * position)

    def _calculate_length_score(self, term: Term) -> float:
        """计算长度分数（术语长度适中较好）"""
        length = len(term.name)
        # 2-8个字符/单词最佳
        if 2 <= length <= 8:
            return 1.0
        elif length < 2:
            return 0.3
        else:
            return max(0.3, 1.0 - (length - 8) * 0.1)

    def _calculate_specificity_score(self, term: Term) -> float:
        """计算专业性分数"""
        # 检查reason是否包含专业关键词
        professional_keywords = [
            "专业", "技术", "算法", "模型", "系统", "机制", "原理",
            "technology", "algorithm", "model", "system", "mechanism"
        ]

        reason = term.reason.lower()
        for keyword in professional_keywords:
            if keyword in reason:
                return 0.9

        return 0.5


# 便捷函数
def rank_terms(terms: List[Term], context: dict = None) -> List[Term]:
    """
    对术语进行排序的便捷函数

    Args:
        terms: 术语列表
        context: 上下文信息

    Returns:
        List[Term]: 排序后的术语列表
    """
    ranker = TermRanker()
    return ranker.rank(terms, context)
