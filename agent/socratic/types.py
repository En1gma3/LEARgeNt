"""
苏格拉底引导类型定义
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List


class QuestionType(Enum):
    """六类核心问题类型"""

    CLARIFICATION = "clarification"      # 澄清问题 - 理解学生想法
    ASSUMPTION = "assumption"           # 假设问题 - 找出隐含假设
    EVIDENCE = "evidence"               # 证据问题 - 要求支持理由
    COUNTEREXAMPLE = "counterexample"   # 反例问题 - 测试理论稳固性
    IMPLICATION = "implication"         # 推论问题 - 探索结论影响
    METACOGNITION = "metacognition"     # 元认知问题 - 训练反思思维

    @property
    def description(self) -> str:
        """问题类型的目标描述"""
        descriptions = {
            QuestionType.CLARIFICATION: "理解学生想法",
            QuestionType.ASSUMPTION: "找出隐含假设",
            QuestionType.EVIDENCE: "要求支持理由",
            QuestionType.COUNTEREXAMPLE: "测试理论稳固性",
            QuestionType.IMPLICATION: "探索结论影响",
            QuestionType.METACOGNITION: "训练反思思维",
        }
        return descriptions[self]

    @property
    def llm_guidance(self) -> str:
        """LLM行为引导语"""
        guidances = {
            QuestionType.CLARIFICATION: "当学生表述模糊时，询问具体含义",
            QuestionType.ASSUMPTION: "当学生做结论时，追问前提条件",
            QuestionType.EVIDENCE: "当学生提出观点时，要求提供依据",
            QuestionType.COUNTEREXAMPLE: "当学生确定时，尝试举反例检验",
            QuestionType.IMPLICATION: "当学生理解后，追问更深层含义",
            QuestionType.METACOGNITION: "适时询问学生对答案的确定程度",
        }
        return guidances[self]


class HintLevel(Enum):
    """提示层级"""

    LEVEL_1_CONCEPT = 1  # 提醒概念
    LEVEL_2_VARIABLE = 2  # 指出关键变量
    LEVEL_3_PARTIAL = 3   # 提供部分答案

    @property
    def prompt(self) -> str:
        prompts = {
            HintLevel.LEVEL_1_CONCEPT: "我给你一个提示：{concept}相关的核心概念是...",
            HintLevel.LEVEL_2_VARIABLE: "关键在于理解{var1}和{var2}之间的关系...",
            HintLevel.LEVEL_3_PARTIAL: "你可以这样理解：{concept}的本质是...",
        }
        return prompts[self]


class DialogueState(Enum):
    """对话状态"""

    DIAGNOSIS = "diagnosis"         # 诊断理解
    DECOMPOSE = "decompose"         # 拆解问题
    GUIDING = "guiding"             # 引导推理
    RECOGNIZING_ERROR = "recognizing_error"  # 识别错误
    HINT = "hint"                   # 关键提示
    STUDENT_SUMMARY = "student_summary"  # 学生总结
    AI_SUMMARY = "ai_summary"       # AI结构化总结
    COMPLETED = "completed"          # 完成


@dataclass
class QuestionTemplate:
    """问题模板"""

    question_type: QuestionType
    template: str
    example: str


# 问题模板库（作为示例，实际由LLM动态生成）
QUESTION_TEMPLATES = [
    # 澄清问题
    QuestionTemplate(
        QuestionType.CLARIFICATION,
        "你说的'{term}'具体指什么？",
        "你说的'效率'具体指什么？"
    ),
    QuestionTemplate(
        QuestionType.CLARIFICATION,
        "能否再解释一下你的想法？",
        "能否再解释一下你的想法？"
    ),

    # 假设问题
    QuestionTemplate(
        QuestionType.ASSUMPTION,
        "你的结论是否假设了{term}？",
        "你的结论是否假设了市场是竞争的？"
    ),
    QuestionTemplate(
        QuestionType.ASSUMPTION,
        "如果这个条件不成立会怎样？",
        "如果这个条件不成立会怎样？"
    ),

    # 证据问题
    QuestionTemplate(
        QuestionType.EVIDENCE,
        "你有什么证据支持这个观点？",
        "你有什么证据支持这个观点？"
    ),
    QuestionTemplate(
        QuestionType.EVIDENCE,
        "{term}的依据是什么？",
        "供需关系的依据是什么？"
    ),

    # 反例问题
    QuestionTemplate(
        QuestionType.COUNTEREXAMPLE,
        "有没有可能出现相反情况？",
        "有没有可能出现相反情况？"
    ),
    QuestionTemplate(
        QuestionType.COUNTEREXAMPLE,
        "在极端条件下会发生什么？",
        "在极端条件下会发生什么？"
    ),

    # 推论问题
    QuestionTemplate(
        QuestionType.IMPLICATION,
        "如果这个理论正确，会带来什么结果？",
        "如果这个理论正确，会带来什么结果？"
    ),
    QuestionTemplate(
        QuestionType.IMPLICATION,
        "{term}会产生什么影响？",
        "人工智能会产生什么影响？"
    ),

    # 元认知问题
    QuestionTemplate(
        QuestionType.METACOGNITION,
        "你对这个答案有多确定？",
        "你对这个答案有多确定？"
    ),
    QuestionTemplate(
        QuestionType.METACOGNITION,
        "还有其他解释吗？",
        "还有其他解释吗？"
    ),
]
