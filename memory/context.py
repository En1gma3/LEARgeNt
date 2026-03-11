"""
短期记忆 - 当前会话上下文
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class Message:
    """对话消息"""
    role: str  # user/assistant/system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionContext:
    """会话上下文"""
    session_id: str
    mode: str = "learn"  # learn/qa/review
    context: str = ""  # 当前语境
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加消息"""
        self.messages.append(Message(
            role=role,
            content=content,
            metadata=metadata or {}
        ))
        self.updated_at = datetime.now()

    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """获取最近的消息"""
        return self.messages[-count:]

    def get_summary(self) -> str:
        """获取会话摘要"""
        if not self.messages:
            return "无对话历史"

        # 简单摘要：提取关键名词
        terms = []
        for msg in self.messages:
            if msg.role == "user":
                # 简单提取：假设消息中包含的名词
                # 实际应该使用NER或关键词提取
                pass
        return f"会话包含 {len(self.messages)} 条消息"


class ShortTermMemory:
    """短期记忆管理器"""

    def __init__(self):
        self.current_session: Optional[SessionContext] = None
        self._history: List[SessionContext] = []

    def create_session(self, session_id: str = None, mode: str = "learn") -> SessionContext:
        """创建新会话"""
        import uuid
        session_id = session_id or str(uuid.uuid4())
        self.current_session = SessionContext(session_id=session_id, mode=mode)
        return self.current_session

    def get_current_session(self) -> Optional[SessionContext]:
        """获取当前会话"""
        return self.current_session

    def set_context(self, context: str):
        """设置当前语境"""
        if self.current_session:
            self.current_session.context = context

    def get_context(self) -> str:
        """获取当前语境"""
        if self.current_session:
            return self.current_session.context
        return ""

    def set_mode(self, mode: str):
        """设置会话模式"""
        if self.current_session:
            self.current_session.mode = mode

    def get_mode(self) -> str:
        """获取会话模式"""
        if self.current_session:
            return self.current_session.mode
        return "learn"

    def add_user_message(self, content: str):
        """添加用户消息"""
        if self.current_session:
            self.current_session.add_message("user", content)

    def add_assistant_message(self, content: str, metadata: Dict[str, Any] = None):
        """添加助手消息"""
        if self.current_session:
            self.current_session.add_message("assistant", content, metadata)

    def get_conversation_history(self, limit: int = 20) -> List[Dict[str, str]]:
        """获取对话历史"""
        if not self.current_session:
            return []

        messages = self.current_session.get_recent_messages(limit)
        return [{"role": m.role, "content": m.content} for m in messages]

    def save_session(self):
        """保存当前会话到历史"""
        if self.current_session:
            self._history.append(self.current_session)

    def clear_session(self):
        """清除当前会话"""
        self.save_session()
        self.current_session = None
