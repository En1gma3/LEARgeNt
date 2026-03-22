"""
记忆系统模块

提供短期记忆（会话上下文）和长期记忆（用户偏好、历史）功能。

会话持久化:
    会话自动保存到 data/sessions.json
    每次退出时会保存当前会话
"""

from .context import ShortTermMemory, SessionContext, Message
from .long_term import LongTermMemory

__all__ = [
    'ShortTermMemory',
    'SessionContext',
    'Message',
    'LongTermMemory',
]
