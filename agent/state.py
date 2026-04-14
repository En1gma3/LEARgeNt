"""
Agent 状态定义
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List


class AgentState(Enum):
    """Agent 状态枚举"""
    IDLE = "idle"                      # 等待用户输入
    BUILDING = "building"               # 正在构建知识
    TEACHING = "teaching"              # 正在讲解
    Q_A = "q_a"                        # 问答中
    SUMMARIZING = "summarizing"        # 总结中


@dataclass
class AgentSnapshot:
    """Agent 状态快照，用于持久化"""
    state: AgentState
    current_term: Optional[str]
    anchors: Optional[Dict]
    message_history: List[Dict]
    qa_history: List[Dict]
    pending_selection: Optional[List[str]]