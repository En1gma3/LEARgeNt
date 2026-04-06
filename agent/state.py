"""
Agent 状态定义
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List


class AgentState(Enum):
    """Agent 状态枚举"""
    IDLE = "idle"                      # 等待用户输入
    WAITING_SELECTION = "waiting_selection"   # 等待用户输入问题
    LEARNING = "learning"              # 学习中


@dataclass
class AgentSnapshot:
    """Agent 状态快照，用于持久化"""
    state: AgentState
    current_term: Optional[str]
    anchors: Optional[Dict]
    message_history: List[Dict]
    qa_history: List[Dict]
    pending_selection: Optional[List[str]]