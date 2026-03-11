"""
知识库数据库操作
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .models import Term, Tag, TermTag, TermRelation, TermVersion


class KnowledgeDB:
    """知识库数据库"""

    def __init__(self, db_path: str = "./data/knowledge.db"):
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 名词表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS terms (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    definition TEXT,
                    source TEXT DEFAULT 'manual',
                    source_url TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_verified INTEGER DEFAULT 0,
                    is_expired INTEGER DEFAULT 0,
                    mindmap TEXT,
                    summary TEXT
                )
            """)

            # 标签表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT DEFAULT '#666666',
                    description TEXT
                )
            """)

            # 名词-标签关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS term_tags (
                    id TEXT PRIMARY KEY,
                    term_id TEXT NOT NULL,
                    tag_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                    UNIQUE(term_id, tag_id)
                )
            """)

            # 名词-名词关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS term_relations (
                    id TEXT PRIMARY KEY,
                    source_term_id TEXT NOT NULL,
                    target_term_id TEXT NOT NULL,
                    relation_type TEXT DEFAULT 'related',
                    created_by TEXT DEFAULT 'auto',
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (source_term_id) REFERENCES terms(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_term_id) REFERENCES terms(id) ON DELETE CASCADE
                )
            """)

            # 版本历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS term_versions (
                    id TEXT PRIMARY KEY,
                    term_id TEXT NOT NULL,
                    definition TEXT,
                    change_summary TEXT,
                    version INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    created_by TEXT DEFAULT 'user',
                    FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE
                )
            """)

            # 全文检索表
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS terms_fts USING fts5(
                    name, definition, content=terms, content_rowid=rowid
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_terms_name ON terms(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_term_tags_term ON term_tags(term_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_term_tags_tag ON term_tags(tag_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_term_relations_source ON term_relations(source_term_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_term_relations_target ON term_relations(target_term_id)")

    # ========== Term 操作 ==========

    def add_term(self, term: Term) -> str:
        """添加名词"""
        term.id = term.id or str(uuid.uuid4())
        term.created_at = datetime.now()
        term.updated_at = datetime.now()

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO terms (id, name, definition, source, source_url,
                                 created_at, updated_at, is_verified, is_expired, mindmap, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (term.id, term.name, term.definition, term.source, term.source_url,
                  term.created_at.isoformat(), term.updated_at.isoformat(),
                  int(term.is_verified), int(term.is_expired), term.mindmap, term.summary))

            # 更新全文检索
            cursor.execute("INSERT INTO terms_fts (rowid, name, definition) VALUES (?, ?, ?)",
                          (cursor.lastrowid, term.name, term.definition))

            # 创建初始版本
            self._add_version(term.id, term.definition, "初始创建", conn)

        return term.id

    def get_term(self, term_id: str) -> Optional[Term]:
        """获取名词"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM terms WHERE id = ?", (term_id,))
            row = cursor.fetchone()
            return self._row_to_term(row) if row else None

    def get_term_by_name(self, name: str) -> Optional[Term]:
        """根据名称获取名词"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM terms WHERE name = ?", (name,))
            row = cursor.fetchone()
            return self._row_to_term(row) if row else None

    def update_term(self, term_id: str, **kwargs) -> bool:
        """更新名词"""
        if not kwargs:
            return False

        kwargs['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [term_id]

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE terms SET {set_clause} WHERE id = ?", values)

            # 如果更新定义，添加版本记录
            if 'definition' in kwargs:
                old_term = self.get_term(term_id)
                if old_term:
                    self._add_version(term_id, kwargs['definition'], "更新定义", conn)

            # 更新全文检索
            if 'name' in kwargs or 'definition' in kwargs:
                term = self.get_term(term_id)
                if term:
                    cursor.execute("DELETE FROM terms_fts WHERE name = ?", (term.name,))
                    cursor.execute("INSERT INTO terms_fts (name, definition) VALUES (?, ?)",
                                  (term.name, term.definition))

        return True

    def delete_term(self, term_id: str) -> bool:
        """删除名词"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM terms WHERE id = ?", (term_id,))
        return True

    def list_terms(self, limit: int = 100, offset: int = 0) -> List[Term]:
        """列出所有名词"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM terms ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                          (limit, offset))
            return [self._row_to_term(row) for row in cursor.fetchall()]

    def search_terms(self, query: str, limit: int = 20) -> List[Term]:
        """搜索名词"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.* FROM terms t
                JOIN terms_fts fts ON t.name = fts.name
                WHERE terms_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            return [self._row_to_term(row) for row in cursor.fetchall()]

    def _row_to_term(self, row: sqlite3.Row) -> Term:
        """行转Term对象"""
        return Term(
            id=row['id'],
            name=row['name'],
            definition=row['definition'] or '',
            source=row['source'] or 'manual',
            source_url=row['source_url'] or '',
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            is_verified=bool(row['is_verified']),
            is_expired=bool(row['is_expired']),
            mindmap=row['mindmap'] or '',
            summary=row['summary'] or ''
        )

    # ========== Tag 操作 ==========

    def add_tag(self, tag: Tag) -> str:
        """添加标签"""
        tag.id = tag.id or str(uuid.uuid4())

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tags (id, name, color, description)
                VALUES (?, ?, ?, ?)
            """, (tag.id, tag.name, tag.color, tag.description))

        return tag.id

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        """获取标签"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
            row = cursor.fetchone()
            return self._row_to_tag(row) if row else None

    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """根据名称获取标签"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tags WHERE name = ?", (name,))
            row = cursor.fetchone()
            return self._row_to_tag(row) if row else None

    def delete_tag(self, tag_id: str) -> bool:
        """删除标签"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        return True

    def list_tags(self) -> List[Tag]:
        """列出所有标签"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tags ORDER BY name")
            return [self._row_to_tag(row) for row in cursor.fetchall()]

    def _row_to_tag(self, row: sqlite3.Row) -> Tag:
        """行转Tag对象"""
        return Tag(
            id=row['id'],
            name=row['name'],
            color=row['color'] or '#666666',
            description=row['description'] or ''
        )

    # ========== Term-Tag 操作 ==========

    def add_term_tag(self, term_id: str, tag_id: str) -> str:
        """添加名词-标签关联"""
        id_ = str(uuid.uuid4())
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO term_tags (id, term_id, tag_id, created_at)
                VALUES (?, ?, ?, ?)
            """, (id_, term_id, tag_id, datetime.now().isoformat()))
        return id_

    def remove_term_tag(self, term_id: str, tag_id: str) -> bool:
        """移除名词-标签关联"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM term_tags WHERE term_id = ? AND tag_id = ?",
                          (term_id, tag_id))
        return True

    def get_term_tags(self, term_id: str) -> List[Tag]:
        """获取名词的所有标签"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.* FROM tags t
                JOIN term_tags tt ON t.id = tt.tag_id
                WHERE tt.term_id = ?
            """, (term_id,))
            return [self._row_to_tag(row) for row in cursor.fetchall()]

    def get_tag_terms(self, tag_id: str) -> List[Term]:
        """获取标签下的所有名词"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.* FROM terms t
                JOIN term_tags tt ON t.id = tt.term_id
                WHERE tt.tag_id = ?
            """, (tag_id,))
            return [self._row_to_term(row) for row in cursor.fetchall()]

    # ========== Term-Relation 操作 ==========

    def add_relation(self, relation: TermRelation) -> str:
        """添加名词关联"""
        relation.id = relation.id or str(uuid.uuid4())
        relation.created_at = datetime.now()

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO term_relations (id, source_term_id, target_term_id,
                                          relation_type, created_by, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (relation.id, relation.source_term_id, relation.target_term_id,
                  relation.relation_type, relation.created_by, relation.confidence,
                  relation.created_at.isoformat()))

        return relation.id

    def get_term_relations(self, term_id: str) -> List[Term]:
        """获取名词的所有关联名词"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.* FROM terms t
                JOIN term_relations tr ON t.id = tr.target_term_id
                WHERE tr.source_term_id = ?
            """, (term_id,))
            return [self._row_to_term(row) for row in cursor.fetchall()]

    def _add_version(self, term_id: str, definition: str, summary: str, conn: sqlite3.Connection):
        """添加版本记录"""
        cursor = conn.cursor()
        # 获取当前最大版本号
        cursor.execute("SELECT MAX(version) FROM term_versions WHERE term_id = ?", (term_id,))
        max_version = cursor.fetchone()[0] or 0

        version_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO term_versions (id, term_id, definition, change_summary, version, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (version_id, term_id, definition, summary, max_version + 1,
              datetime.now().isoformat(), "user"))

    def get_term_versions(self, term_id: str) -> List[TermVersion]:
        """获取名词版本历史"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM term_versions
                WHERE term_id = ?
                ORDER BY version DESC
            """, (term_id,))
            return [TermVersion(
                id=row['id'],
                term_id=row['term_id'],
                definition=row['definition'],
                change_summary=row['change_summary'] or '',
                version=row['version'],
                created_at=datetime.fromisoformat(row['created_at']),
                created_by=row['created_by']
            ) for row in cursor.fetchall()]
