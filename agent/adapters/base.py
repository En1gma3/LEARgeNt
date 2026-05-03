"""
消息适配器基类

定义统一的消息通道接口
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseAdapter(ABC):
    """消息适配器基类"""

    @abstractmethod
    def send_message(self, user_id: str, content: str, msg_type: str = "text") -> bool:
        """
        发送消息给用户

        Args:
            user_id: 用户标识
            content: 消息内容
            msg_type: 消息类型 (text/markdown/card)

        Returns:
            是否发送成功
        """
        pass

    @abstractmethod
    async def start(self):
        """启动适配器，开始接收消息"""
        pass

    @abstractmethod
    async def stop(self):
        """停止适配器"""
        pass

    def supports_markdown(self) -> bool:
        """是否支持 Markdown 消息"""
        return False

    def supports_cards(self) -> bool:
        """是否支持卡片消息"""
        return False
