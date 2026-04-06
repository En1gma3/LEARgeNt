"""
工具注册表

7个工具: build, answer, teach, decompose, summarize, select, fetch
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from agent.state import AgentState


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None


class BaseTool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str, needs_agent: bool = False):
        self.name = name
        self.description = description
        self.needs_agent = needs_agent  # 是否需要子Agent

    @abstractmethod
    async def execute(self, params: Dict, context: Dict) -> ToolResult:
        """执行工具"""
        pass

    def get_schema(self) -> Dict:
        """获取工具定义（用于LLM决策）"""
        return {
            "name": self.name,
            "description": self.description,
            "needs_agent": self.needs_agent
        }

    def _extract_json_from_response(self, response: str) -> Dict:
        """从 LLM 响应中提取 JSON（通用逻辑）"""
        import json
        json_str = response.strip()
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            json_str = "\n".join(lines[1:-1])
        return json.loads(json_str)


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        """列出所有工具"""
        return [tool.get_schema() for tool in self._tools.values()]

    def get_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())


# 全局注册表实例
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _register_tools(_registry)
    return _registry


def _register_tools(registry: ToolRegistry) -> None:
    """注册所有工具"""
    from agent.tools.impl import (
        BuildTool, AnswerTool, TeachTool,
        DecomposeTool, SummarizeTool,
        SelectTool, FetchTool
    )

    # P0: 核心工具
    registry.register(BuildTool())
    registry.register(AnswerTool())
    registry.register(TeachTool())

    # P1: 重要工具
    registry.register(DecomposeTool())
    registry.register(SummarizeTool())

    # P2: 交互工具
    registry.register(SelectTool())

    # P3: 辅助工具
    registry.register(FetchTool())


def reset_registry() -> None:
    """重置注册表（用于测试）"""
    global _registry
    _registry = None