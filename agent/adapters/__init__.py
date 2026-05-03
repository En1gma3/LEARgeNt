"""
消息适配器模块

提供统一的聊天平台接入接口，目前支持：
- Feishu (飞书)
"""

from .base import BaseAdapter
from .feishu_adapter import FeishuAdapter

__all__ = ["BaseAdapter", "FeishuAdapter"]
