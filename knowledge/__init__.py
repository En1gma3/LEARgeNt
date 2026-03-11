"""
知识库模块

提供名词、标签、关联的存储和检索功能。
"""

from .models import Term, Tag, TermTag, TermRelation, TermVersion
from .db import KnowledgeDB

__all__ = [
    'Term',
    'Tag',
    'TermTag',
    'TermRelation',
    'TermVersion',
    'KnowledgeDB',
]
