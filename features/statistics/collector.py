"""
统计分析模块
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, date


@dataclass
class DailyStats:
    """每日统计"""
    date: str  # YYYY-MM-DD
    new_terms_count: int = 0
    review_count: int = 0
    study_duration: int = 0  # 分钟
    tags_created: int = 0


class StatisticsCollector:
    """统计数据收集器"""

    def __init__(self, data_path: str = "./data/statistics.json"):
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Any]:
        """加载数据"""
        if self.data_path.exists():
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"daily": {}}

    def _save(self):
        """保存数据"""
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _get_today_key(self) -> str:
        """获取今日键"""
        return datetime.now().strftime("%Y-%m-%d")

    def record_new_term(self):
        """记录新名词学习"""
        key = self._get_today_key()
        if key not in self._data["daily"]:
            self._data["daily"][key] = {
                "new_terms_count": 0,
                "review_count": 0,
                "study_duration": 0,
                "tags_created": 0
            }
        self._data["daily"][key]["new_terms_count"] += 1
        self._save()

    def record_review(self):
        """记录复习"""
        key = self._get_today_key()
        if key not in self._data["daily"]:
            self._data["daily"][key] = {
                "new_terms_count": 0,
                "review_count": 0,
                "study_duration": 0,
                "tags_created": 0
            }
        self._data["daily"][key]["review_count"] += 1
        self._save()

    def record_study_time(self, minutes: int):
        """记录学习时长"""
        key = self._get_today_key()
        if key not in self._data["daily"]:
            self._data["daily"][key] = {
                "new_terms_count": 0,
                "review_count": 0,
                "study_duration": 0,
                "tags_created": 0
            }
        self._data["daily"][key]["study_duration"] += minutes
        self._save()

    def record_tag_created(self):
        """记录创建标签"""
        key = self._get_today_key()
        if key not in self._data["daily"]:
            self._data["daily"][key] = {
                "new_terms_count": 0,
                "review_count": 0,
                "study_duration": 0,
                "tags_created": 0
            }
        self._data["daily"][key]["tags_created"] += 1
        self._save()

    def get_today_stats(self) -> Dict[str, Any]:
        """获取今日统计"""
        key = self._get_today_key()
        return self._data["daily"].get(key, {
            "new_terms_count": 0,
            "review_count": 0,
            "study_duration": 0,
            "tags_created": 0
        })

    def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """获取统计概览"""
        today = datetime.now()
        stats = {
            "total_new_terms": 0,
            "total_reviews": 0,
            "total_study_time": 0,
            "total_tags": 0,
            "daily": []
        }

        for i in range(days):
            day = today - datetime.timedelta(days=i)
            key = day.strftime("%Y-%m-%d")
            if key in self._data["daily"]:
                day_stats = self._data["daily"][key]
                stats["total_new_terms"] += day_stats.get("new_terms_count", 0)
                stats["total_reviews"] += day_stats.get("review_count", 0)
                stats["total_study_time"] += day_stats.get("study_duration", 0)
                stats["total_tags"] += day_stats.get("tags_created", 0)
                stats["daily"].append({"date": key, **day_stats})

        stats["daily"].reverse()
        return stats

    def format_report(self, stats: Dict[str, Any]) -> str:
        """格式化报告"""
        lines = [
            "=" * 40,
            "学习统计报告",
            "=" * 40,
            f"学习新名词: {stats['total_new_terms']}个",
            f"完成复习: {stats['total_reviews']}次",
            f"总学习时长: {stats['total_study_time']}分钟",
            f"创建标签: {stats['total_tags']}个",
            "=" * 40
        ]
        return "\n".join(lines)
