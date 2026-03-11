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
