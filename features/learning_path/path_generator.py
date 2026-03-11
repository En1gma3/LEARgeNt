"""
学习路径模块
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class LearningPath:
    """学习路径"""
    id: str
    name: str
    description: str = ""
    terms: List[str] = field(default_factory=list)
    estimated_time: int = 0  # 分钟
    difficulty: str = "beginner"  # beginner/intermediate/advanced
    prerequisites: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PathManager:
    """学习路径管理器"""

    def __init__(self, data_path: str = "./data/learning_paths.json"):
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self._paths: Dict[str, LearningPath] = self._load()

    def _load(self) -> Dict[str, LearningPath]:
        """加载数据"""
        if self.data_path.exists():
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {k: LearningPath(**v) for k, v in data.items()}
        return {}

    def _save(self):
        """保存数据"""
        data = {k: asdict(v) for k, v in self._paths.items()}
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_path(self, name: str, description: str = "", difficulty: str = "beginner") -> str:
        """创建学习路径"""
        import uuid
        path_id = str(uuid.uuid4())
        self._paths[path_id] = LearningPath(
            id=path_id,
            name=name,
            description=description,
            difficulty=difficulty
        )
        self._save()
        return path_id

    def add_term(self, path_id: str, term: str) -> bool:
        """添加名词到路径"""
        if path_id not in self._paths:
            return False

        if term not in self._paths[path_id].terms:
            self._paths[path_id].terms.append(term)
            self._save()
        return True

    def remove_term(self, path_id: str, term: str) -> bool:
        """从路径移除名词"""
        if path_id not in self._paths:
            return False

        if term in self._paths[path_id].terms:
            self._paths[path_id].terms.remove(term)
            self._save()
        return True

    def get_path(self, path_id: str) -> Optional[LearningPath]:
        """获取路径"""
        return self._paths.get(path_id)

    def get_path_by_name(self, name: str) -> Optional[LearningPath]:
        """根据名称获取路径"""
        for path in self._paths.values():
            if path.name == name:
                return path
        return None

    def list_paths(self) -> List[LearningPath]:
        """列出所有路径"""
        return list(self._paths.values())

    def delete_path(self, path_id: str) -> bool:
        """删除路径"""
        if path_id in self._paths:
            del self._paths[path_id]
            self._save()
            return True
        return False

    def generate_recommend(self, target_term: str, known_terms: List[str]) -> Dict[str, Any]:
        """
        生成推荐学习路径

        基于目标名词生成推荐路径
        简化实现：实际需要知识图谱支持
        """
        # 简化版：返回目标词作为学习起点
        return {
            "name": f"{target_term}学习路径",
            "description": f"学习{target_term}的推荐路径",
            "difficulty": "intermediate",
            "estimated_time": 60,
            "terms": [target_term],
            "note": "简化版本，需要知识图谱支持自动生成完整路径"
        }
