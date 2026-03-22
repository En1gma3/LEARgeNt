"""
知识库数据模型
"""

from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class Term:
    """名词"""
    id: str
    name: str
    definition: str = ""
    source: str = "manual"  # web/doc/manual
    source_url: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_verified: bool = False
    is_expired: bool = False
    mindmap: str = ""  # 思维导图内容
    summary: str = ""  # 学习总结


@dataclass
class KnowledgePoint:
    """知识点（用于 Learn 模式的三锚点结构）"""
    id: str = ""
    name: str = ""
    definition: str = ""

    # 三锚点（必须）
    topic_anchor: str = ""           # 主题锚点
    dependency_anchors: List[str] = field(default_factory=list)  # 依赖锚点
    semantic_anchor: str = ""         # 语义锚点

    # 可选锚点
    contrast_anchor: str = ""          # 对比关系
    example_anchor: str = ""          # 举例关系

    source: str = ""
    source_url: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_verified: bool = False
    is_expired: bool = False

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
class Tag:
    """标签"""
    id: str
    name: str
    color: str = "#666666"  # 默认灰色
    description: str = ""


@dataclass
class TermTag:
    """名词-标签关联"""
    id: str
    term_id: str
    tag_id: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TermRelation:
    """名词-名词关联"""
    id: str
    source_term_id: str
    target_term_id: str
    relation_type: str = "related"  # related/similar/contrasting/causal
    created_by: str = "auto"  # auto/user
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TermVersion:
    """名词版本历史"""
    id: str
    term_id: str
    definition: str
    change_summary: str = ""
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "user"


@dataclass
class LearningStats:
    """学习统计"""
    user_id: str = "default"
    date: str = ""  # YYYY-MM-DD
    new_terms_count: int = 0
    review_count: int = 0
    study_duration: int = 0  # 分钟
    tags_created: int = 0


@dataclass
class MasteryScore:
    """掌握度评分"""
    term_id: str
    mastery_level: float = 0.0  # 0.0-1.0
    review_count: int = 0
    average_rating: float = 0.0
    last_reviewed: Optional[datetime] = None


@dataclass
class ReviewSchedule:
    """复习计划"""
    term_id: str
    next_review_date: datetime = field(default_factory=datetime.now)
    current_interval_index: int = 0
    ease_factor: float = 2.5
    review_count: int = 0


@dataclass
class InterestPoint:
    """兴趣点记录"""
    id: str
    source_type: str  # paper/news/company/industry/question
    source_content: str
    extracted_terms: List[str] = field(default_factory=list)
    predicted_interest: str = ""
    user_confirmed: bool = False
    confirmed_term: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DisambiguationPreference:
    """消歧偏好"""
    id: str
    term: str
    selected_meaning: str
    context: str = ""
    frequency: int = 1
    last_selected_at: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
