"""
三锚点构建器

使用 LLM 构建知识点的三锚点（主题锚点、依赖锚点、语义锚点）
"""

import json
import uuid
from typing import Dict, List, Optional

from memory.context import SessionContext, KnowledgePoint as SessionKnowledgePoint
from knowledge.models import KnowledgePoint
from utils import get_logger

logger = get_logger(__name__)


ANCHOR_BUILD_PROMPT = """你是一个知识结构化专家。你的任务是为给定的术语/概念构建"三锚点"结构。

## 三锚点定义

1. **主题锚点 (topic_anchor)**: 这个概念属于哪个更大的主题/领域？
   - 例如："区块链"的主题锚点可以是"分布式系统"或"密码学"

2. **依赖锚点 (dependency_anchors)**: 理解这个概念需要先掌握哪些前置概念？
   - 列出2-4个必要的前置知识

3. **语义锚点 (semantic_anchor)**: 用一句话精确定义这个概念的本质
   - 30字以内的核心定义

## 可选锚点

4. **对比锚点 (contrast_anchor)**: 这个概念容易与哪个概念混淆？区别是什么？

5. **举例锚点 (example_anchor)**: 一个典型的使用场景或例子

## 输入

术语名称: {term_name}
定义/描述: {definition}

## 输出格式

请以 JSON 格式输出：
{{
    "topic_anchor": "主题锚点",
    "dependency_anchors": ["依赖1", "依赖2", "依赖3"],
    "semantic_anchor": "一句话定义",
    "contrast_anchor": "对比概念和区别（如有）",
    "example_anchor": "典型例子（如有）"
}}

请直接输出 JSON，不要有其他内容。
"""


class AnchorBuilder:
    """使用 LLM 构建知识点三锚点（会话级工具）"""

    def __init__(self, session_context: SessionContext):
        self._session = session_context
        self._llm = None  # 惰性初始化

    @property
    def llm(self):
        """惰性获取 LLM 客户端"""
        if self._llm is None:
            self._llm = self._session.get_llm_client()
        return self._llm

    async def build(
        self,
        term_name: str,
        definition: str
    ) -> Dict:
        """
        调用 LLM 推断三锚点

        Args:
            term_name: 术语名称
            definition: 术语定义/描述

        Returns:
            包含三锚点的字典
        """
        logger.info(f"Building anchors for term: {term_name}")

        prompt = ANCHOR_BUILD_PROMPT.format(
            term_name=term_name,
            definition=definition or "无"
        )

        try:
            response = self._call_llm(prompt)
            anchors = self._parse_response(response)

            # 同步到短期记忆
            if anchors.get("topic_anchor"):
                self._session.discovered_topic_anchors.add(anchors["topic_anchor"])
            for dep in anchors.get("dependency_anchors", []):
                self._session.discovered_dependency_anchors.add(dep)

            logger.info(f"Anchors built successfully for {term_name}: {anchors}")
            return anchors

        except Exception as e:
            logger.error(f"Failed to build anchors for {term_name}: {e}")
            return self._get_default_anchors(term_name)

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM（同步版本）"""
        messages = [{"role": "user", "content": prompt}]
        return self.llm.chat(messages)

    def _parse_response(self, response: str) -> Dict:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON
            json_str = response.strip()
            # 处理可能的 markdown 代码块
            if json_str.startswith("```"):
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1])

            data = json.loads(json_str)
            return {
                "topic_anchor": data.get("topic_anchor", ""),
                "dependency_anchors": data.get("dependency_anchors", []),
                "semantic_anchor": data.get("semantic_anchor", ""),
                "contrast_anchor": data.get("contrast_anchor", ""),
                "example_anchor": data.get("example_anchor", "")
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            return self._get_default_anchors("unknown")

    def _get_default_anchors(self, term_name: str) -> Dict:
        """获取默认锚点（当 LLM 调用失败时）"""
        return {
            "topic_anchor": "未分类",
            "dependency_anchors": [],
            "semantic_anchor": f"{term_name}是一个待定义的概念",
            "contrast_anchor": "",
            "example_anchor": ""
        }

    def build_knowledge_point(
        self,
        term_name: str,
        definition: str,
        source: str = "",
        source_url: str = ""
    ) -> KnowledgePoint:
        """
        同步构建完整知识点（三锚点）

        注意：这是同步版本，内部会调用 LLM
        """
        import asyncio

        # 创建事件循环
        loop = asyncio.new_event_loop()
        try:
            anchors = loop.run_until_complete(self.build(term_name, definition))
        finally:
            loop.close()

        kp = KnowledgePoint(
            id=str(uuid.uuid4()),
            name=term_name,
            definition=definition,
            topic_anchor=anchors.get("topic_anchor", ""),
            dependency_anchors=anchors.get("dependency_anchors", []),
            semantic_anchor=anchors.get("semantic_anchor", ""),
            contrast_anchor=anchors.get("contrast_anchor", ""),
            example_anchor=anchors.get("example_anchor", ""),
            source=source,
            source_url=source_url
        )

        return kp
