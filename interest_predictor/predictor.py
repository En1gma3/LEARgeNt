"""
兴趣预测器

根据多种策略预测用户最可能感兴趣的术语
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from extractor.base import Term


@dataclass
class PredictionContext:
    """预测上下文"""

    learned_terms: List[str] = None  # 已学习的术语
    user_preferences: Dict[str, Any] = None  # 用户偏好
    current_context: str = ""  # 当前语境
    source_title: str = ""  # 来源标题
    source_type: str = ""  # 来源类型

    def __post_init__(self):
        if self.learned_terms is None:
            self.learned_terms = []
        if self.user_preferences is None:
            self.user_preferences = {}


class InterestPredictor:
    """
    兴趣预测器

    综合多种策略预测用户最可能感兴趣的术语：
    1. 上下文分析 - 标题、摘要权重高
    2. 知识图谱 - 关联用户已学习词汇
    3. 热度排序 - 技术热点词优先
    4. 用户历史 - 学习偏好记忆
    """

    def __init__(self, weights: Dict[str, float] = None):
        """
        初始化

        Args:
            weights: 各因子权重
        """
        self.weights = weights or {
            "position": 0.3,      # 位置权重
            "graph": 0.3,         # 知识图谱权重
            "hotness": 0.2,      # 热度权重
            "history": 0.2,      # 历史偏好权重
        }

        # 技术热点词汇
        self._hot_terms = self._load_hot_terms()

    def predict(
        self,
        terms: List[Term],
        context: PredictionContext
    ) -> Optional[Term]:
        """
        预测最可能感兴趣的术语

        Args:
            terms: 候选术语列表
            context: 预测上下文

        Returns:
            Term: 预测的术语
        """
        if not terms:
            return None

        # 计算每个术语的得分
        scored_terms = []
        for term in terms:
            score = self._calculate_score(term, context)
            scored_terms.append((term, score))

        # 按得分排序
        scored_terms.sort(key=lambda x: x[1], reverse=True)

        # 返回得分最高的
        return scored_terms[0][0] if scored_terms else None

    def _calculate_score(self, term: Term, context: PredictionContext) -> float:
        """计算综合得分"""
        score = 0.0

        # 1. 位置得分
        position_score = self._calculate_position_score(term, context)
        score += position_score * self.weights.get("position", 0.3)

        # 2. 知识图谱关联得分
        graph_score = self._calculate_graph_score(term, context)
        score += graph_score * self.weights.get("graph", 0.3)

        # 3. 热度得分
        hotness_score = self._calculate_hotness_score(term)
        score += hotness_score * self.weights.get("hotness", 0.2)

        # 4. 历史偏好得分
        history_score = self._calculate_history_score(term, context)
        score += history_score * self.weights.get("history", 0.2)

        return score

    def _calculate_position_score(self, term: Term, context: PredictionContext) -> float:
        """计算位置得分"""
        position = term.source_position
        if position == 0:
            return 1.0
        # 前10个位置的词得分较高
        if position < 10:
            return 1.0 - position * 0.05
        return 0.5

    def _calculate_graph_score(self, term: Term, context: PredictionContext) -> float:
        """计算知识图谱关联得分"""
        learned = [t.lower() for t in context.learned_terms]

        if not learned:
            return 0.5  # 无历史记录，返回中等分数

        term_name = term.name.lower()

        # 检查是否与已学习词汇相似
        # 简化：直接匹配
        for learned_term in learned:
            if learned_term in term_name or term_name in learned_term:
                return 0.9

        return 0.3

    def _calculate_hotness_score(self, term: Term) -> float:
        """计算热度得分"""
        term_name = term.name.lower()

        # 检查是否在热点词表中
        if term_name in self._hot_terms:
            return 1.0

        # 检查是否包含热点词
        for hot_term in self._hot_terms:
            if hot_term in term_name:
                return 0.8

        return 0.3

    def _calculate_history_score(
        self,
        term: Term,
        context: PredictionContext
    ) -> float:
        """计算历史偏好得分"""
        preferences = context.user_preferences

        if not preferences:
            return 0.5

        # 检查用户偏好词
        preferred_terms = preferences.get("preferred_terms", [])
        term_name = term.name.lower()

        for pref_term in preferred_terms:
            if pref_term.lower() in term_name or term_name in pref_term.lower():
                return 1.0

        return 0.5

    def _load_hot_terms(self) -> set:
        """加载热点词汇"""
        return {
            # AI/ML
            "人工智能", "机器学习", "深度学习", "神经网络",
            "transformer", "大语言模型", "llm", "gpt",
            "自动驾驶", "计算机视觉", "自然语言处理",
            # 区块链
            "区块链", "比特币", "以太坊", "智能合约", "web3",
            # 云计算
            "云计算", "边缘计算", "serverless", "docker", "kubernetes",
            # 数据
            "大数据", "数据分析", "数据挖掘", "数据科学",
            # 其他技术
            "量子计算", "5g", "物联网", "ar", "vr", "元宇宙",
        }

    def get_top_n(
        self,
        terms: List[Term],
        context: PredictionContext,
        n: int = 5
    ) -> List[Term]:
        """
        获取Top N个最可能感兴趣的术语

        Args:
            terms: 候选术语列表
            context: 预测上下文
            n: 返回数量

        Returns:
            List[Term]: 排序后的术语列表
        """
        if not terms:
            return []

        # 计算得分
        scored_terms = []
        for term in terms:
            score = self._calculate_score(term, context)
            scored_terms.append((term, score))

        # 按得分排序
        scored_terms.sort(key=lambda x: x[1], reverse=True)

        # 返回Top N
        return [t for t, _ in scored_terms[:n]]
