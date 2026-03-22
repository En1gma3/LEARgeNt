"""
主题拆解器

使用 LLM 将主题拆解为知识点/维度
"""

import json
from typing import List, Optional

from memory.context import SessionContext
from utils import get_logger

logger = get_logger(__name__)


IS_THEME_PROMPT = """判断以下输入是"主题"还是"具体概念"：

主题特点：
- 范围广泛，包含多个子概念
- 可以从多个维度/方面拆解
- 例如："区块链"、"人工智能"、"经济学"

具体概念特点：
- 定义明确，边界清晰
- 通常是单一知识点
- 例如："工作量证明"、"梯度下降"、"GDP"

输入: {term_name}

请只回答"是主题"或"不是主题"，不要有其他内容。
"""


THEME_DECOMPOSE_PROMPT = """将主题"{theme_name}"拆解为多个维度/方面。

要求：
- 列出3-6个主要维度
- 每个维度应该是理解该主题的一个方面
- 维度之间应该有清晰的区分

请以 JSON 数组格式输出：
["维度1", "维度2", "维度3", ...]

请只输出 JSON 数组，不要有其他内容。
"""


DIMENSION_TO_KPOINTS_PROMPT = """主题"{theme}"的"{dimension}"维度下，有哪些具体的学习点？

请列出3-5个具体知识点，每个知识点应该：
- 是一个独立的概念/术语
- 适合作为单独的学习单元

请以 JSON 数组格式输出：
["知识点1", "知识点2", "知识点3", ...]

请只输出 JSON 数组，不要有其他内容。
"""


class ThemeDecomposer:
    """使用 LLM 将主题拆解为知识点（会话级工具）"""

    def __init__(self, session_context: SessionContext):
        self._session = session_context
        self._llm = None  # 惰性初始化

    @property
    def llm(self):
        """惰性获取 LLM 客户端"""
        if self._llm is None:
            self._llm = self._session.get_llm_client()
        return self._llm

    async def is_theme(self, term_name: str) -> bool:
        """
        调用 LLM 判断是否为主题

        Args:
            term_name: 待判断的术语

        Returns:
            True 如果是主题，False 如果是具体概念
        """
        logger.info(f"Checking if '{term_name}' is a theme")

        prompt = IS_THEME_PROMPT.format(term_name=term_name)

        try:
            response = self._call_llm(prompt)
            is_theme = "是主题" in response.strip()
            logger.info(f"'{term_name}' is_theme={is_theme}")
            return is_theme
        except Exception as e:
            logger.error(f"Failed to check if '{term_name}' is theme: {e}")
            return False

    async def decompose(self, theme_name: str) -> List[str]:
        """
        将主题拆解为维度

        Args:
            theme_name: 主题名称

        Returns:
            维度列表
        """
        logger.info(f"Decomposing theme: {theme_name}")

        prompt = THEME_DECOMPOSE_PROMPT.format(theme_name=theme_name)

        try:
            response = self._call_llm(prompt)
            dimensions = self._parse_json_array(response)
            logger.info(f"Decomposed '{theme_name}' into {len(dimensions)} dimensions")
            return dimensions
        except Exception as e:
            logger.error(f"Failed to decompose theme '{theme_name}': {e}")
            return self._get_default_dimensions(theme_name)

    async def decompose_to_knowledge_points(
        self,
        dimension: str,
        theme: str
    ) -> List[str]:
        """
        将维度拆解为具体知识点

        Args:
            dimension: 维度名称
            theme: 所属主题

        Returns:
            知识点列表
        """
        logger.info(f"Decomposing dimension '{dimension}' of theme '{theme}'")

        prompt = DIMENSION_TO_KPOINTS_PROMPT.format(
            theme=theme,
            dimension=dimension
        )

        try:
            response = self._call_llm(prompt)
            kpoints = self._parse_json_array(response)
            logger.info(f"Decomposed dimension '{dimension}' into {len(kpoints)} knowledge points")
            return kpoints
        except Exception as e:
            logger.error(f"Failed to decompose dimension '{dimension}': {e}")
            return []

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM（同步版本）"""
        messages = [{"role": "user", "content": prompt}]
        return self.llm.chat(messages)

    def _parse_json_array(self, response: str) -> List[str]:
        """解析 JSON 数组响应"""
        try:
            json_str = response.strip()
            # 处理可能的 markdown 代码块
            if json_str.startswith("```"):
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1])

            data = json.loads(json_str)
            if isinstance(data, list):
                return [str(item) for item in data]
            return []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON array: {e}")
            logger.debug(f"Raw response: {response}")
            return []

    def _get_default_dimensions(self, theme_name: str) -> List[str]:
        """获取默认维度（当 LLM 调用失败时）"""
        return [
            f"{theme_name}概述",
            f"{theme_name}核心原理",
            f"{theme_name}应用场景",
            f"{theme_name}优缺点"
        ]

    # 同步便捷方法

    def check_is_theme(self, term_name: str) -> bool:
        """同步版本：判断是否为主题"""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.is_theme(term_name))
        finally:
            loop.close()

    def decompose_theme(self, theme_name: str) -> List[str]:
        """同步版本：拆解主题为维度"""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.decompose(theme_name))
        finally:
            loop.close()

    def get_dimension_kpoints(self, dimension: str, theme: str) -> List[str]:
        """同步版本：获取维度的知识点"""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.decompose_to_knowledge_points(dimension, theme)
            )
        finally:
            loop.close()
