"""
长期记忆 - 用户偏好和历史数据
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class LongTermMemory:
    """长期记忆管理器"""

    def __init__(self, data_path: str = "./data/memory.json"):
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        """加载数据"""
        if self.data_path.exists():
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "learned_terms": [],
            "user_preferences": {},
            "disambiguations": {},
            "learning_history": [],
            "last_updated": datetime.now().isoformat()
        }

    def _save(self):
        """保存数据"""
        self._data["last_updated"] = datetime.now().isoformat()
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ========== 学习记录 ==========

    def add_learned_term(self, term_name: str):
        """添加已学习名词"""
        if term_name not in self._data["learned_terms"]:
            self._data["learned_terms"].append(term_name)
            self._save()

    def get_learned_terms(self) -> List[str]:
        """获取已学习名词列表"""
        return self._data["learned_terms"].copy()

    def is_learned(self, term_name: str) -> bool:
        """检查是否已学习"""
        return term_name in self._data["learned_terms"]

    # ========== 用户偏好 ==========

    def set_preference(self, key: str, value: Any):
        """设置用户偏好"""
        self._data["user_preferences"][key] = value
        self._save()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取用户偏好"""
        return self._data["user_preferences"].get(key, default)

    def get_all_preferences(self) -> Dict[str, Any]:
        """获取所有偏好"""
        return self._data["user_preferences"].copy()

    # ========== 消歧偏好 ==========

    def set_disambiguation(self, term: str, meaning: str):
        """设置消歧选择"""
        if term not in self._data["disambiguations"]:
            self._data["disambiguations"][term] = []

        # 更新或添加
        found = False
        for item in self._data["disambiguations"][term]:
            if item["meaning"] == meaning:
                item["count"] = item.get("count", 0) + 1
                item["last_selected"] = datetime.now().isoformat()
                found = True
                break

        if not found:
            self._data["disambiguations"][term].append({
                "meaning": meaning,
                "count": 1,
                "first_selected": datetime.now().isoformat(),
                "last_selected": datetime.now().isoformat()
            })

        self._save()

    def get_disambiguation(self, term: str) -> Optional[str]:
        """获取消歧偏好"""
        if term not in self._data["disambiguations"]:
            return None

        candidates = self._data["disambiguations"][term]
        if not candidates:
            return None

        # 返回最常选择的
        return max(candidates, key=lambda x: x.get("count", 0))["meaning"]

    def clear_disambiguations(self):
        """清除所有消歧偏好"""
        self._data["disambiguations"] = {}
        self._save()

    # ========== 学习历史 ==========

    def add_history(self, term: str, action: str, details: Dict[str, Any] = None):
        """添加学习历史"""
        self._data["learning_history"].append({
            "term": term,
            "action": action,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
        # 限制历史数量
        if len(self._data["learning_history"]) > 1000:
            self._data["learning_history"] = self._data["learning_history"][-1000:]
        self._save()

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取学习历史"""
        return self._data["learning_history"][-limit:]

    def get_term_history(self, term: str) -> List[Dict[str, Any]]:
        """获取特定名词的历史"""
        return [h for h in self._data["learning_history"] if h["term"] == term]

    # ========== 统计信息 ==========

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_terms": len(self._data["learned_terms"]),
            "total_history": len(self._data["learning_history"]),
            "preferences_count": len(self._data["user_preferences"]),
            "disambiguations_count": len(self._data["disambiguations"]),
            "last_updated": self._data.get("last_updated")
        }
