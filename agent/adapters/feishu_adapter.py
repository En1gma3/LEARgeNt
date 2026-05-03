"""
飞书消息适配器

使用 lark_oapi SDK 实现 WebSocket 长连接
参考 quanty_trading/qlib/trading_framework/smart_bot.py 的正确实现
"""

import asyncio
import json
import time
from typing import Dict, Optional, Set
from dataclasses import dataclass

from .base import BaseAdapter
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class FeishuMessage:
    """飞书消息结构"""
    message_id: str
    user_id: str
    content: str
    msg_type: str
    chat_id: Optional[str] = None


class FeishuAdapter(BaseAdapter):
    """飞书消息适配器"""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        AgentClass=None
    ):
        """
        初始化飞书适配器

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
            AgentClass: LearnMateAgent 类，用于创建用户会话
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.AgentClass = AgentClass

        # 用户会话缓存
        self._user_sessions: Dict[str, "LearnMateAgent"] = {}

        # 消息去重（内存版）
        self._processed_messages: Set[str] = set()
        self._message_ttl = 300  # 5分钟内不重复处理

        # Lark SDK 客户端
        self._client = None
        self._ws_client = None

        # 运行状态
        self._running = False

    def _get_user_session(self, user_id: str) -> "LearnMateAgent":
        """
        获取或创建用户独立的 LearnMateAgent

        Args:
            user_id: 用户 ID

        Returns:
            该用户的 LearnMateAgent 实例
        """
        if user_id not in self._user_sessions:
            if self.AgentClass:
                self._user_sessions[user_id] = self.AgentClass()
                logger.info(f"Created new LearnMateAgent for user: {user_id}")
            else:
                # 动态导入避免循环依赖
                from agent.learn_agent import LearnMateAgent
                self._user_sessions[user_id] = LearnMateAgent()
                logger.info(f"Created new LearnMateAgent for user: {user_id}")

        return self._user_sessions[user_id]

    def _is_duplicate(self, message_id: str) -> bool:
        """检查消息是否已处理（去重）"""
        if message_id in self._processed_messages:
            return True

        # 清理过期消息
        current_time = time.time()
        expired = {
            msg_id for msg_id, timestamp in
            [(mid, 0) for mid in self._processed_messages]
            if current_time - timestamp > self._message_ttl
        }
        for msg_id in expired:
            self._processed_messages.discard(msg_id)

        self._processed_messages.add(message_id)
        return False

    def _parse_text_content(self, content: dict) -> str:
        """解析文本消息内容"""
        try:
            if isinstance(content, dict):
                text = content.get("text", "")
                return text
            return str(content)
        except Exception as e:
            logger.warning(f"Failed to parse text content: {e}")
            return ""

    def _parse_image_content(self, content: dict) -> str:
        """解析图片消息内容"""
        try:
            if isinstance(content, dict):
                image_key = content.get("image_key", "")
                return f"[图片消息: {image_key}]"
            return "[图片消息]"
        except Exception as e:
            logger.warning(f"Failed to parse image content: {e}")
            return "[图片消息]"

    def _parse_post_content(self, content: dict) -> str:
        """解析富文本消息内容（post）"""
        try:
            if isinstance(content, dict):
                # 提取富文本的文本内容
                text_parts = []
                post = content.get("post", {})
                if isinstance(post, dict):
                    for element in post.get("elements", []):
                        if element.get("tag") == "text":
                            text_parts.append(element.get("text", ""))
                        elif element.get("tag") == "at":
                            text_parts.append(f"@{element.get('user_id', '')}")
                return " ".join(text_parts) if text_parts else str(content)
            return str(content)
        except Exception as e:
            logger.warning(f"Failed to parse post content: {e}")
            return str(content)

    def _parse_message(self, event) -> Optional[FeishuMessage]:
        """
        解析飞书消息事件

        Args:
            event: 飞书 WebSocket 事件

        Returns:
            FeishuMessage 对象，或 None 如果解析失败
        """
        try:
            message = None
            sender_id = ""
            chat_id = ""
            msg_type = "text"

            logger.debug(f"[_parse_message] event type: {type(event)}")
            logger.debug(f"[_parse_message] event attributes: {dir(event) if hasattr(event, '__dict__') else 'N/A'}")

            # SDK 事件对象结构: data.event.message
            if hasattr(event, 'event') and hasattr(event.event, 'message'):
                logger.debug(f"[_parse_message] Using event.event.message structure")
                message = event.event.message

                # 获取 sender_id
                if hasattr(event.event, 'sender') and hasattr(event.event.sender, 'sender_id'):
                    sid = event.event.sender.sender_id
                    sender_id = sid.open_id if hasattr(sid, 'open_id') else str(sid)

                chat_id = message.chat_id if hasattr(message, 'chat_id') else ""
                msg_type = message.message_type if hasattr(message, 'message_type') else "text"
            else:
                logger.warning(f"[_parse_message] Unknown event structure, no event.event.message")
                logger.warning(f"[_parse_message] event.__dict__: {event.__dict__ if hasattr(event, '__dict__') else 'N/A'}")
                return None

            if not message:
                logger.warning(f"[_parse_message] No message extracted from event")
                return None

            # 获取消息 ID
            message_id = message.message_id if hasattr(message, 'message_id') else ""
            logger.debug(f"[_parse_message] message_id={message_id}, msg_type={msg_type}")

            # 解析内容
            content_str = message.content if hasattr(message, 'content') else "{}"
            if isinstance(content_str, str):
                content = json.loads(content_str)
            else:
                content = content_str

            logger.debug(f"[_parse_message] content parsed: {content}")

            # 根据消息类型解析
            if msg_type == "text":
                text = self._parse_text_content(content)
            elif msg_type == "image":
                text = self._parse_image_content(content)
            elif msg_type == "post":
                text = self._parse_post_content(content)
            else:
                text = str(content)

            logger.info(f"[_parse_message] Parsed: user_id={sender_id}, msg_type={msg_type}, text={text[:50]}...")

            return FeishuMessage(
                message_id=message_id,
                user_id=sender_id,
                content=text,
                msg_type=msg_type,
                chat_id=chat_id
            )

        except Exception as e:
            logger.error(f"Failed to parse message: {e}", exc_info=True)
            return None

    def _handle_feishu_event(self, data):
        """
        处理飞书 WebSocket 事件

        Args:
            data: 飞书事件数据
        """
        try:
            logger.info(f"[_handle_feishu_event] Received event data type: {type(data)}")

            # 解析消息
            feishu_msg = self._parse_message(data)
            if not feishu_msg:
                logger.warning(f"[_handle_feishu_event] Failed to parse message, feishu_msg is None")
                return

            # 去重检查
            if self._is_duplicate(feishu_msg.message_id):
                logger.debug(f"Duplicate message skipped: {feishu_msg.message_id}")
                return

            logger.info(f"Received message from user {feishu_msg.user_id}: {feishu_msg.content[:50]}...")

            # 在独立线程中处理消息（避免阻塞 event loop）
            # LearnMateAgent.handle_input() 是 async 方法，需要在 event loop 中运行
            import threading
            import asyncio

            def process():
                try:
                    # 获取或创建用户的 agent
                    agent = self._get_user_session(feishu_msg.user_id)
                    logger.info(f"[_handle_feishu_event] Calling handle_input for user {feishu_msg.user_id}")

                    # 在新的 event loop 中运行 async handle_input
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        response = loop.run_until_complete(agent.handle_input(feishu_msg.content))
                    finally:
                        loop.close()

                    logger.info(f"[_handle_feishu_event] handle_input returned: {response[:100] if response else 'empty'}...")
                    self.send_message(feishu_msg.user_id, response)
                except Exception as e:
                    logger.error(f"[FeishuAdapter] Error in process thread: {e}", exc_info=True)

            thread = threading.Thread(target=process, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    def send_message(self, user_id: str, content: str, msg_type: str = "text") -> bool:
        """
        发送消息给用户

        Args:
            user_id: 用户 ID (open_id)
            content: 消息内容
            msg_type: 消息类型 (text/markdown/card)

        Returns:
            是否发送成功
        """
        try:
            if not self._client:
                logger.warning("Lark client not initialized")
                return False

            import lark_oapi as lark

            # 构建消息内容
            if msg_type == "markdown":
                msg_type = "text"  # 飞书 markdown 本质是文本

            # 使用 open_id 发送消息
            request = lark.im.v1.CreateMessageRequest.builder() \
                .receive_id_type("open_id") \
                .request_body(
                    lark.im.v1.CreateMessageRequestBody.builder()
                    .receive_id(user_id)
                    .msg_type(msg_type)
                    .content(json.dumps({"text": content}))
                    .build()
                ) \
                .build()

            response = self._client.im.v1.message.create(request)

            if response.success():
                logger.info(f"Message sent to user {user_id}")
                return True
            else:
                logger.error(f"Failed to send message: code={response.code} msg={response.msg}")
                return False

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def send_markdown_card(self, user_id: str, title: str, content: str) -> bool:
        """
        发送 Markdown 卡片消息

        Args:
            user_id: 用户 ID
            title: 卡片标题
            content: Markdown 内容

        Returns:
            是否发送成功
        """
        try:
            if not self._client:
                logger.warning("Lark client not initialized")
                return False

            import lark_oapi as lark

            # 构建卡片内容
            card = {
                "config": {"wide_screen_mode": True},
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content
                    }
                ]
            }

            # 如果有标题，添加到卡片
            if title:
                card["header"] = {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue"
                }

            request = lark.im.v1.CreateMessageRequest.builder() \
                .receive_id_type("open_id") \
                .request_body(
                    lark.im.v1.CreateMessageRequestBody.builder()
                    .receive_id(user_id)
                    .msg_type("interactive")
                    .content(json.dumps(card, ensure_ascii=False))
                    .build()
                ) \
                .build()

            response = self._client.im.v1.message.create(request)

            if response.success():
                logger.info(f"Card message sent to user {user_id}")
                return True
            else:
                logger.error(f"Failed to send card: code={response.code} msg={response.msg}")
                return False

        except Exception as e:
            logger.error(f"Failed to send card message: {e}")
            return False

    def supports_markdown(self) -> bool:
        """是否支持 Markdown"""
        return True

    def supports_cards(self) -> bool:
        """是否支持卡片消息"""
        return True

    def prepare(self):
        """
        准备阶段：初始化客户端（在 event loop 外调用）
        """
        try:
            import lark_oapi as lark

            logger.info(f"[FeishuAdapter] Preparing client with app_id: {self.app_id[:8]}...")

            # 初始化 HTTP 客户端（用于发送消息）
            self._client = lark.Client.builder() \
                .app_id(self.app_id) \
                .app_secret(self.app_secret) \
                .log_level(lark.LogLevel.DEBUG) \
                .build()

            logger.info("[FeishuAdapter] HTTP client created")

            # 创建消息处理器闭包
            def on_message(data):
                """处理接收到的消息"""
                logger.info(f"[FeishuAdapter] on_message called! data type: {type(data)}")
                logger.debug(f"[FeishuAdapter] on_message data: {data}")
                self._handle_feishu_event(data)

            logger.info("[FeishuAdapter] Creating EventDispatcherHandler...")

            # 创建事件处理器
            logger.info("[FeishuAdapter] Registering p2_im_message_receive_v1 handler...")
            event_handler = lark.EventDispatcherHandler.builder("", "") \
                .register_p2_im_message_receive_v1(on_message) \
                .build()
            logger.info("[FeishuAdapter] Event handler registered successfully")

            logger.info("[FeishuAdapter] EventDispatcherHandler created with p2_im_message_receive_v1")

            # 创建 WebSocket 客户端（正确的 API）
            self._ws_client = lark.ws.Client(
                self.app_id,
                self.app_secret,
                event_handler=event_handler,
                log_level=lark.LogLevel.DEBUG
            )

            logger.info("[FeishuAdapter] WebSocket client created")
            logger.info("[FeishuAdapter] Feishu client prepared successfully")

        except ImportError:
            logger.error("lark_oapi not installed. Install with: pip install lark-oapi")
            raise
        except Exception as e:
            logger.error(f"Failed to prepare Feishu client: {e}", exc_info=True)
            raise

    async def connect_and_run(self):
        """
        连接到飞书并保持运行（供 SDK 的 event loop 调用）
        """
        from lark_oapi.ws.client import loop as sdk_loop

        logger.info("[FeishuAdapter] Connecting to Feishu WebSocket...")

        # 建立 WebSocket 连接
        await self._ws_client._connect()

        logger.info("[FeishuAdapter] WebSocket _connect() completed")

        # 启动心跳
        logger.info("[FeishuAdapter] Creating ping task...")
        sdk_loop.create_task(self._ws_client._ping_loop())
        logger.info("[FeishuAdapter] Ping task created")

        self._running = True
        logger.info("[FeishuAdapter] Feishu WebSocket connected and running")

        # 保持运行
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("FeishuAdapter cancelled")
        finally:
            self._running = False
            logger.info("Feishu WebSocket stopped")

    async def start(self):
        """启动飞书 WebSocket 长连接（内部调用 connect_and_run）"""
        if self._running:
            logger.warning("FeishuAdapter already running")
            return

        self.prepare()
        await self.connect_and_run()

    async def stop(self):
        """停止飞书连接"""
        if not self._running:
            return

        self._running = False
        logger.info("Feishu WebSocket stopped")

    async def run(self):
        """运行适配器（阻塞）- 供外部调用"""
        await self.start()
