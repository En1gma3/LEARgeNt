"""
提醒系统模块
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, time


@dataclass
class Reminder:
    """提醒"""
    id: str
    type: str  # review/study/goal
    message: str
    time: str = "09:00"  # HH:MM
    days: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 0])  # 0=周日
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ReminderManager:
    """提醒管理器"""

    def __init__(self, data_path: str = "./data/reminders.json"):
        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self._reminders: Dict[str, Reminder] = self._load()

    def _load(self) -> Dict[str, Reminder]:
        """加载数据"""
        if self.data_path.exists():
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {k: Reminder(**v) for k, v in data.items()}
        return {}

    def _save(self):
        """保存数据"""
        data = {k: asdict(v) for k, v in self._reminders.items()}
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_reminder(self, reminder_type: str, message: str, time: str = "09:00",
                     days: List[int] = None) -> str:
        """添加提醒"""
        import uuid
        reminder_id = str(uuid.uuid4())

        self._reminders[reminder_id] = Reminder(
            id=reminder_id,
            type=reminder_type,
            message=message,
            time=time,
            days=days or [1, 2, 3, 4, 5, 6, 0]
        )
        self._save()
        return reminder_id

    def add_review_reminder(self, time: str = "09:00") -> str:
        """添加复习提醒"""
        return self.add_reminder("review", "该复习了！", time)

    def add_study_reminder(self, time: str = "09:00", days: List[int] = None) -> str:
        """添加学习提醒"""
        return self.add_reminder("study", "该学习了！", time, days)

    def remove_reminder(self, reminder_id: str) -> bool:
        """删除提醒"""
        if reminder_id in self._reminders:
            del self._reminders[reminder_id]
            self._save()
            return True
        return False

    def toggle_reminder(self, reminder_id: str, enabled: bool) -> bool:
        """开关提醒"""
        if reminder_id in self._reminders:
            self._reminders[reminder_id].enabled = enabled
            self._save()
            return True
        return False

    def get_reminders(self, enabled_only: bool = False) -> List[Reminder]:
        """获取提醒列表"""
        reminders = list(self._reminders.values())
        if enabled_only:
            reminders = [r for r in reminders if r.enabled]
        return reminders

    def get_due_reminders(self) -> List[Reminder]:
        """获取到期的提醒"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_day = now.weekday()

        due = []
        for reminder in self._reminders.values():
            if not reminder.enabled:
                continue
            if current_day in reminder.days and reminder.time == current_time:
                due.append(reminder)

        return due

    def clear_all(self):
        """清除所有提醒"""
        self._reminders.clear()
        self._save()
