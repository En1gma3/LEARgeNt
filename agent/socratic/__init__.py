"""
苏格拉底式学习引导模块

本模块实现系统的"灵魂"——通过苏格拉底式提问引导学生主动思考，
而非被动接收答案。

核心原则：
- 答案保留：提问 → 提示 → 解释
- 学生中心：从学生当前理解出发
- 小步推进：逐步拆解大问题
- 认知冲突：引导发现逻辑矛盾
- 鼓励解释：要求说明推理过程
- 结构总结：最终必须总结
"""

from .core import SocraticGuide
from .types import QuestionType, HintLevel, DialogueState
from .prompt import SOCRATIC_SYSTEM_PROMPT

__all__ = [
    'SocraticGuide',
    'QuestionType',
    'HintLevel',
    'DialogueState',
    'SOCRATIC_SYSTEM_PROMPT',
]
