"""
复习计划调度器 - 艾宾浩斯遗忘曲线实现
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict


# 复习间隔（天）
INTERVALS = [1, 3, 7, 14, 30, 60, 120]


@dataclass
class ReviewItem:
    """复习项"""
    term_id: str
    term_name: str
    next_review_date: str  # ISO格式
    current_interval_index: int = 0
    ease_factor: float = 2.5
    review_count: int = 0
    last_rating: int = 0


class ReviewScheduler:
    """复习调度器"""

    def __init__(self, data_path: str = "./data/review.json"):
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self._items: Dict[str, ReviewItem] = self._load()

    def _load(self) -> Dict[str, ReviewItem]:
        """加载数据"""
        if self.data_path.exists():
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {k: ReviewItem(**v) for k, v in data.items()}
        return {}

    def _save(self):
        """保存数据"""
        data = {k: asdict(v) for k, v in self._items.items()}
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_term(self, term_id: str, term_name: str):
        """添加复习项"""
        if term_id in self._items:
            return

        self._items[term_id] = ReviewItem(
            term_id=term_id,
            term_name=term_name,
            next_review_date=datetime.now().isoformat()
        )
        self._save()

    def get_due_reviews(self) -> List[ReviewItem]:
        """获取到期的复习项"""
        now = datetime.now()
        due = []
        for item in self._items.values():
            review_date = datetime.fromisoformat(item.next_review_date)
            if review_date <= now:
                due.append(item)
        return due

    def get_upcoming_reviews(self, days: int = 7) -> List[ReviewItem]:
        """获取即将到期的复习项"""
        now = datetime.now()
        future = now + timedelta(days=days)
        upcoming = []
        for item in self._items.values():
            review_date = datetime.fromisoformat(item.next_review_date)
            if now < review_date <= future:
                upcoming.append(item)
        return upcoming

    def update_review(self, term_id: str, rating: int) -> bool:
        """
        更新复习状态

        rating: 0-5 分
        - 0-2: 记得差，减少间隔
        - 3: 保持间隔
        - 4-5: 记得牢，增加间隔
        """
        if term_id not in self._items:
            return False

        item = self._items[term_id]

        # 更新评分
        item.last_rating = rating
        item.review_count += 1

        # 根据评分调整间隔
        if rating >= 4:
            # 记得牢，增加间隔
            item.current_interval_index = min(
                item.current_interval_index + 1,
                len(INTERVALS) - 1
            )
            # 增加难度系数
            item.ease_factor = min(item.ease_factor + 0.1, 3.0)
        elif rating <= 2:
            # 记得差，减少间隔
            item.current_interval_index = max(0, item.current_interval_index - 2)
            # 降低难度系数
            item.ease_factor = max(item.ease_factor - 0.2, 1.3)

        # 计算下次复习时间
        interval = INTERVALS[item.current_interval_index]
        next_date = datetime.now() + timedelta(days=int(interval * item.ease_factor))
        item.next_review_date = next_date.isoformat()

        self._save()
        return True

    def skip_review(self, term_id: str) -> bool:
        """跳过本次复习"""
        if term_id not in self._items:
            return False

        item = self._items[term_id]
        # 推迟一天
        next_date = datetime.now() + timedelta(days=1)
        item.next_review_date = next_date.isoformat()

        self._save()
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取复习统计"""
        now = datetime.now()
        due_count = 0
        upcoming_count = 0
        total_reviews = sum(item.review_count for item in self._items.values())

        for item in self._items.values():
            review_date = datetime.fromisoformat(item.next_review_date)
            if review_date <= now:
                due_count += 1
            else:
                upcoming_count += 1

        return {
            "total_items": len(self._items),
            "due_today": due_count,
            "upcoming": upcoming_count,
            "total_reviews": total_reviews
        }

    def remove_term(self, term_id: str) -> bool:
        """移除复习项"""
        if term_id in self._items:
            del self._items[term_id]
            self._save()
            return True
        return False
