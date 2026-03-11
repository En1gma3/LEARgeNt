"""
问题解析器
"""

import re
from typing import List, Dict, Any

from .base import BaseParser, ParseResult


class QuestionParser(BaseParser):
    """问题/疑问解析器"""

    source_type = "question"

    # 问题类型关键词
    QUESTION_PATTERNS = {
        "definition": [r"什么是", r"什么是", r"^\s*什么是", r"是\s*什么"],
        "reason": [r"为什么", r"为何", r" reason", r" cause"],
        "how": [r"怎么", r"如何", r"怎样", r"how\s", r" ways? to"],
        "comparison": [r"和.*相比", r"与.*区别", r" different", r" vs ", r" versus"],
        "application": [r"应用", r"用途", r"作用", r" use", r" application"],
        "example": [r"例子", r"实例", r" example", r"例如"],
    }

    def parse(self, question: str) -> ParseResult:
        """
        解析问题

        Args:
            question: 用户问题

        Returns:
            ParseResult: 解析结果
        """
        if not self.validate_input(question):
            raise ValueError("无效的问题")

        # 分析问题类型
        question_type = self._analyze_question_type(question)

        # 提取关键词
        keywords = self._extract_keywords(question)

        # 识别核心概念
        core_concept = self._identify_core_concept(question, keywords)

        # 构建内容
        content = self._build_content(question, question_type, keywords, core_concept)

        return ParseResult(
            source_type=self.source_type,
            title=question,
            content=content,
            metadata={
                "question_type": question_type,
                "keywords": keywords,
                "core_concept": core_concept,
            }
        )

    def _analyze_question_type(self, question: str) -> str:
        """分析问题类型"""
        question = question.lower()

        for qtype, patterns in self.QUESTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question):
                    return qtype

        return "general"

    def _extract_keywords(self, question: str) -> List[str]:
        """提取关键词"""
        # 移除停用词和常见词
        stop_words = {
            "的", "是", "什么", "怎么", "如何", "为什么", "为何",
            "请", "帮我", "告诉", "我", "你", "能", "可以",
            "a", "an", "the", "is", "are", "was", "were",
            "what", "how", "why", "when", "where", "who"
        }

        # 简单分词
        words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', question)

        # 过滤停用词
        keywords = [w for w in words if w.lower() not in stop_words and len(w) > 1]

        return keywords

    def _identify_core_concept(self, question: str, keywords: List[str]) -> str:
        """识别核心概念"""
        # 尝试提取"什么是X"或"X是什么"中的X
        patterns = [
            r'什么是(.+?)(?:\s|$|,|？|\?)',
            r'(.+?)是\s*什么',
            r'为什么(.+?)(?:\s|$|,|？|\?)',
            r'(.+?)\?$',
        ]

        for pattern in patterns:
            match = re.search(pattern, question.strip())
            if match:
                concept = match.group(1).strip()
                if len(concept) > 1:
                    return concept

        # 如果没找到，返回第一个关键词
        return keywords[0] if keywords else question.strip()

    def _build_content(
        self,
        question: str,
        question_type: str,
        keywords: List[str],
        core_concept: str
    ) -> str:
        """构建内容"""
        lines = []

        lines.append(f"# 问题解析")
        lines.append(f"\n原始问题: {question}")

        lines.append(f"\n问题类型: {self._get_type_description(question_type)}")

        lines.append(f"\n提取到关键词:")
        lines.append(" | ".join(keywords))

        lines.append(f"\n核心概念: {core_concept}")

        # 根据问题类型提供学习建议
        lines.append(f"\n学习建议:")
        advice = self._get_learning_advice(question_type, core_concept)
        lines.append(advice)

        return "\n".join(lines)

    def _get_type_description(self, question_type: str) -> str:
        """获取问题类型描述"""
        descriptions = {
            "definition": "概念定义",
            "reason": "原因分析",
            "how": "方法/步骤",
            "comparison": "对比分析",
            "application": "应用场景",
            "example": "例子/实例",
            "general": "一般问题",
        }
        return descriptions.get(question_type, "一般问题")

    def _get_learning_advice(self, question_type: str, core_concept: str) -> str:
        """获取学习建议"""
        advice_map = {
            "definition": f"建议先学习'{core_concept}'的基本定义，然后逐步了解其原理和应用。",
            "reason": f"'{core_concept}'的原因分析需要先理解其背景和机制。",
            "how": f"'{core_concept}'的方法论学习需要了解其具体步骤和要点。",
            "comparison": f"对比学习'{core_concept}'需要了解与之相关的其他概念。",
            "application": f"了解'{core_concept}'的应用场景可以帮助加深理解。",
            "example": f"通过具体例子可以更直观地理解'{core_concept}'。",
            "general": f"建议从'{core_concept}'的基本概念开始学习。",
        }
        return advice_map.get(question_type, f"建议从'{core_concept}'开始学习。")
