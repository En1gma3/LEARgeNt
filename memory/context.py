"""
短期记忆 - 当前会话上下文

支持会话持久化到磁盘
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from utils import get_logger

logger = get_logger(__name__)


class KnowledgePoint:
    """知识点（用于 Learn 模式的三锚点结构）"""

    def __init__(
        self,
        id: str = "",
        name: str = "",
        definition: str = "",
        topic_anchor: str = "",
        dependency_anchors: List[str] = None,
        semantic_anchor: str = "",
        contrast_anchor: str = "",
        example_anchor: str = "",
        source: str = "",
        source_url: str = "",
        is_verified: bool = False,
        is_expired: bool = False
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.definition = definition
        self.topic_anchor = topic_anchor
        self.dependency_anchors = dependency_anchors or []
        self.semantic_anchor = semantic_anchor
        self.contrast_anchor = contrast_anchor
        self.example_anchor = example_anchor
        self.source = source
        self.source_url = source_url
        self.is_verified = is_verified
        self.is_expired = is_expired
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "definition": self.definition,
            "topic_anchor": self.topic_anchor,
            "dependency_anchors": self.dependency_anchors,
            "semantic_anchor": self.semantic_anchor,
            "contrast_anchor": self.contrast_anchor,
            "example_anchor": self.example_anchor,
            "source": self.source,
            "source_url": self.source_url,
            "is_verified": self.is_verified,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgePoint":
        """从字典创建"""
        obj = cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            definition=data.get("definition", ""),
            topic_anchor=data.get("topic_anchor", ""),
            dependency_anchors=data.get("dependency_anchors", []),
            semantic_anchor=data.get("semantic_anchor", ""),
            contrast_anchor=data.get("contrast_anchor", ""),
            example_anchor=data.get("example_anchor", ""),
            source=data.get("source", ""),
            source_url=data.get("source_url", ""),
            is_verified=data.get("is_verified", False),
            is_expired=data.get("is_expired", False)
        )
        if "created_at" in data:
            obj.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            obj.updated_at = datetime.fromisoformat(data["updated_at"])
        return obj


@dataclass
class Message:
    """对话消息"""
    role: str  # user/assistant/system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """从字典创建"""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )


@dataclass
class SessionContext:
    """会话上下文（扩展版，包含 Learn 模式所需的三锚点和会话级工具）"""
    session_id: str
    mode: str = "learn"  # learn/qa/review
    context: str = ""  # 当前语境
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Learn 模式专用字段
    learned_knowledge_points: List[KnowledgePoint] = field(default_factory=list)  # 已学习的知识点
    discovered_topic_anchors: Set[str] = field(default_factory=set)  # 已发现的主题锚点
    discovered_dependency_anchors: Set[str] = field(default_factory=set)  # 已发现的依赖锚点
    current_theme: str = None  # 当前学习主题

    # 会话级工具（惰性初始化）
    _anchor_builder: Any = field(default=None, repr=False)
    _theme_decomposer: Any = field(default=None, repr=False)
    _llm_client: Any = field(default=None, repr=False)

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加消息"""
        self.messages.append(Message(
            role=role,
            content=content,
            metadata=metadata or {}
        ))
        self.updated_at = datetime.now()
        logger.debug(f"Session {self.session_id}: Added {role} message")

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

    def get_llm_client(self):
        """获取 LLM 客户端（惰性初始化）"""
        if self._llm_client is None:
            from agent.llm_client import get_llm_client
            self._llm_client = get_llm_client()
        return self._llm_client

    def get_anchor_builder(self):
        """获取三锚点构建器（惰性初始化）"""
        if self._anchor_builder is None:
            from agent.anchor import AnchorBuilder
            self._anchor_builder = AnchorBuilder(self)
        return self._anchor_builder

    def get_theme_decomposer(self):
        """获取主题拆解器（惰性初始化）"""
        if self._theme_decomposer is None:
            from agent.decomposer import ThemeDecomposer
            self._theme_decomposer = ThemeDecomposer(self)
        return self._theme_decomposer

    def add_learned_knowledge_point(self, kp: KnowledgePoint):
        """添加已学习的知识点"""
        self.learned_knowledge_points.append(kp)
        # 同步锚点到发现集合
        if kp.topic_anchor:
            self.discovered_topic_anchors.add(kp.topic_anchor)
        for dep in kp.dependency_anchors:
            self.discovered_dependency_anchors.add(dep)

    def to_dict(self) -> dict:
        """转换为字典（用于持久化）"""
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
            "learned_knowledge_points": [kp.to_dict() for kp in self.learned_knowledge_points],
            "discovered_topic_anchors": list(self.discovered_topic_anchors),
            "discovered_dependency_anchors": list(self.discovered_dependency_anchors),
            "current_theme": self.current_theme
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionContext":
        """从字典创建"""
        messages = [Message.from_dict(m) for m in data.get("messages", [])]
        knowledge_points = [KnowledgePoint.from_dict(kp) for kp in data.get("learned_knowledge_points", [])]
        return cls(
            session_id=data["session_id"],
            mode=data.get("mode", "learn"),
            context=data.get("context", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=messages,
            metadata=data.get("metadata", {}),
            learned_knowledge_points=knowledge_points,
            discovered_topic_anchors=set(data.get("discovered_topic_anchors", [])),
            discovered_dependency_anchors=set(data.get("discovered_dependency_anchors", [])),
            current_theme=data.get("current_theme")
        )


class ShortTermMemory:
    """短期记忆管理器（支持会话持久化）"""

    def __init__(self, storage_path: str = "./data/sessions.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.current_session: Optional[SessionContext] = None
        self._history: List[SessionContext] = []

        # 加载历史会话
        self._load_sessions()

    def _load_sessions(self):
        """从磁盘加载历史会话"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                sessions = data.get("sessions", [])
                self._history = [SessionContext.from_dict(s) for s in sessions]
                logger.info(f"Loaded {len(self._history)} sessions from disk")
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")
                self._history = []
        else:
            logger.info("No sessions file found, starting fresh")
            self._history = []

    def _save_sessions(self):
        """保存所有会话到磁盘"""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "sessions": [s.to_dict() for s in self._history]
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved {len(self._history)} sessions to disk")
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def create_session(self, session_id: str = None, mode: str = "learn") -> SessionContext:
        """创建新会话"""
        session_id = session_id or str(uuid.uuid4())
        self.current_session = SessionContext(session_id=session_id, mode=mode)
        logger.info(f"Created new session: {session_id} (mode={mode})")
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
        """保存当前会话到历史并持久化"""
        if self.current_session:
            # 检查是否已存在（避免重复）
            existing_ids = [s.session_id for s in self._history]
            if self.current_session.session_id not in existing_ids:
                self._history.append(self.current_session)
                logger.info(f"Session {self.current_session.session_id} saved to history")
            else:
                # 更新现有会话
                for i, s in enumerate(self._history):
                    if s.session_id == self.current_session.session_id:
                        self._history[i] = self.current_session
                        break
                logger.debug(f"Session {self.current_session.session_id} updated")

            # 持久化到磁盘
            self._save_sessions()

    def clear_session(self):
        """清除当前会话"""
        self.save_session()
        self.current_session = None
        logger.debug("Current session cleared")

    def get_session_history(self, limit: int = 20) -> List[SessionContext]:
        """获取会话历史列表"""
        return self._history[-limit:]

    def get_session_by_id(self, session_id: str) -> Optional[SessionContext]:
        """根据 ID 获取会话"""
        for session in self._history:
            if session.session_id == session_id:
                return session
        return None

    def delete_session(self, session_id: str) -> bool:
        """删除指定会话"""
        for i, session in enumerate(self._history):
            if session.session_id == session_id:
                del self._history[i]
                self._save_sessions()
                logger.info(f"Session {session_id} deleted")
                return True
        return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话摘要"""
        return [
            {
                "session_id": s.session_id,
                "mode": s.mode,
                "created_at": s.created_at.isoformat(),
                "message_count": len(s.messages),
                "context": s.context[:50] if s.context else ""
            }
            for s in reversed(self._history)
        ]
