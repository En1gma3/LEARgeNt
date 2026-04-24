"""
Agent 状态定义
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List


class AgentState(Enum):
    """统一 Agent 状态枚举"""
    # 基础状态
    IDLE = "idle"                      # 等待用户输入
    BUILDING = "building"              # 正在构建知识
    TEACHING = "teaching"              # 正在讲解
    Q_A = "q_a"                        # 问答中
    SUMMARIZING = "summarizing"        # 总结中

    # 对话状态（从 dialogue.py 合并）
    LEARNING = "learning"               # 学习中
    ASKING = "asking"                  # 问答中
    REVIEWING = "reviewing"             # 复习中
    GUIDING = "guiding"                # 引导中（苏格拉底模式）
    CONFIRMING = "confirming"          # 确认中
    DECOMPOSING = "decomposing"        # 主题拆解中（维度选择）
    SELECTING_KPOINT = "selecting_kpoint"  # 知识点选择
    EXPLAINING = "explaining"           # 概念讲解中
    Q_A_LOOP = "q_a_loop"             # 用户主导问答循环

    # 苏格拉底状态（从 socratic/types.py 合并）
    DIAGNOSIS = "diagnosis"            # 诊断理解
    DECOMPOSE = "decompose"             # 拆解问题
    RECOGNIZING_ERROR = "recognizing_error"  # 识别错误
    HINT = "hint"                      # 关键提示
    STUDENT_SUMMARY = "student_summary"  # 学生总结
    AI_SUMMARY = "ai_summary"           # AI结构化总结

    # 特殊状态
    COMPLETED = "completed"             # 完成


@dataclass
class AgentSnapshot:
    """Agent 状态快照，用于持久化"""
    state: AgentState
    current_term: Optional[str]
    anchors: Optional[Dict]
    message_history: List[Dict]
    qa_history: List[Dict]
    pending_selection: Optional[List[str]]