"""
LearnMate Agent - 单循环架构

主Agent Loop + 工具调用 (使用 Function Call 机制)
"""

import asyncio
from typing import Any, Dict, List, Optional

from agent.state import AgentState
from agent.tools.registry import get_registry
from agent.llm_client import get_llm_client
from cli.selector import readline_with_chinese
from utils import get_logger

logger = get_logger(__name__)


# 工具定义 (用于 Function Call)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "build",
            "description": "为概念构建完整的三锚点知识结构",
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {"type": "string", "description": "概念名称"},
                    "definition": {"type": "string", "description": "概念定义（可选）"}
                },
                "required": ["term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "teach",
            "description": "基于锚点生成概念讲解，并给出理解建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {"type": "string", "description": "概念名称"},
                    "anchors": {
                        "type": "object",
                        "description": "三锚点知识结构",
                        "properties": {
                            "topic_anchor": {"type": "string"},
                            "dependency_anchors": {"type": "array", "items": {"type": "string"}},
                            "semantic_anchor": {"type": "string"},
                            "contrast_anchor": {"type": "string"},
                            "example_anchor": {"type": "string"}
                        }
                    }
                },
                "required": ["term", "anchors"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "answer",
            "description": "基于锚点回答用户问题，并生成追问引导深入思考",
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {"type": "string", "description": "概念名称"},
                    "question": {"type": "string", "description": "用户问题"},
                    "anchors": {"type": "object", "description": "三锚点知识结构"},
                    "history": {"type": "array", "description": "对话历史"}
                },
                "required": ["term", "question", "anchors"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "decompose",
            "description": "将主题分解为多个维度，或将维度分解为知识点",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "主题或维度名称"},
                    "type": {"type": "string", "enum": ["theme", "dimension"], "description": "分解类型"},
                    "context": {"type": "string", "description": "上下文（主题名）"}
                },
                "required": ["input", "type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize",
            "description": "基于学习过程生成结构化总结和建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {"type": "string", "description": "概念名称"},
                    "anchors": {"type": "object", "description": "三锚点知识结构"},
                    "qa_history": {"type": "array", "description": "问答历史"}
                },
                "required": ["term", "anchors"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "select",
            "description": "显示选项列表并等待用户选择，最后一个选项支持用户输入",
            "parameters": {
                "type": "object",
                "properties": {
                    "options": {"type": "array", "items": {"type": "string"}, "description": "选项列表"},
                    "prompt": {"type": "string", "description": "提示文字"}
                },
                "required": ["options", "prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch",
            "description": "从外部知识源获取术语定义",
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {"type": "string", "description": "术语名称"}
                },
                "required": ["term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "结束对话",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "结束消息"}
                },
                "required": ["message"]
            }
        }
    }
]


class LearnMateAgent:
    """
    LearnMate 主 Agent

    单一 LLM 决策循环 + Function Call 工具调用
    """

    def __init__(self):
        self.registry = get_registry()
        self.state = AgentState.IDLE
        self.current_term: Optional[str] = None
        self.anchors: Optional[Dict] = None
        self.learned_terms: List[str] = []
        self.message_history: List[Dict[str, str]] = []
        self.qa_history: List[Dict[str, str]] = []
        self.pending_question: Optional[str] = None

        # LLM 客户端
        self._llm = None

        logger.info("LearnMateAgent initialized")

    @property
    def llm(self):
        """获取 LLM 客户端"""
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    def _extract_term_fallback(self, user_input: str) -> Optional[str]:
        """从用户输入中提取概念名（备用，仅在 LLM 未提取时使用）"""
        # 移除常见前缀
        text = user_input.strip()
        for prefix in ["学习", "了解", "看看", "我想学", "教我", "介绍一下", "介绍"]:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        # 返回清理后的概念名
        return text if text else None

    async def run(self, max_iterations: int = 100) -> int:
        """主循环

        Args:
            max_iterations: 最大迭代次数，防止测试时死循环
        """
        print("=" * 50)
        print("LearnMate - 智能学习助手")
        print("=" * 50)
        print("你好！我是 LearnMate，一个基于三锚点知识系统的智能学习助手。")
        print("你可以告诉我你想学习什么概念，我会帮你深入理解。")
        print()

        # 系统提示词
        system_prompt = """你是一个智能学习助手，基于三锚点知识系统帮助用户学习概念。

你有以下工具可用：
- build: 构建三锚点知识结构
- teach: 生成讲解
- answer: 回答问题
- decompose: 分解主题
- summarize: 生成总结
- select: 等待用户选择
- fetch: 获取术语定义
- finish: 结束对话

工作流程：
1. 用户提出学习需求
2. 使用 build 构建知识
3. 使用 teach 讲解
4. 使用 select 等待用户选择
5. 根据用户选择继续问答或总结
6. 使用 finish 结束

当前概念: {current_term}
已学习概念: {learned_terms}

重要：每次只能调用一个工具。"""

        system_msg = {
            "role": "system",
            "content": system_prompt.format(
                current_term=self.current_term or "无",
                learned_terms=", ".join(self.learned_terms) or "无"
            )
        }

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            try:
                # 获取用户输入
                user_input = readline_with_chinese("> ")
                if not user_input:
                    continue

                # 检查退出
                if user_input.lower() in ["/exit", "/quit", "exit", "quit", "退出"]:
                    print("再见！")
                    break

                # 添加到历史
                self.message_history.append({"role": "user", "content": user_input})
                logger.info(f"[USER INPUT] {user_input}")

                # 如果是问答模式，让 LLM 决定工具
                if self.state == AgentState.WAITING_SELECTION:
                    decision = await self._decide_tool(
                        system_msg,
                        self.message_history,
                        user_input
                    )

                    if decision is None:
                        continue

                    tool_name = decision.get("name") or decision.get("tool")
                    params = decision.get("arguments") or decision.get("params", {})

                    # 如果是 answer 工具，补充参数
                    if tool_name == "answer":
                        params.setdefault("term", self.current_term)
                        params.setdefault("anchors", self.anchors or {})
                        params.setdefault("history", self.message_history)
                        if not params.get("question"):
                            params["question"] = user_input

                    logger.info(f"[TOOL CALL] tool={tool_name}, params={params}")

                    result = await self._execute_tool(tool_name, params)
                    logger.info(f"[TOOL RESULT] tool={tool_name}, result={result}")

                    await self._handle_result(tool_name, result, params)
                    continue

                # 解析用户意图并决定工具
                decision = await self._decide_tool(
                    system_msg,
                    self.message_history,
                    user_input
                )

                if decision is None:
                    continue

                tool_name = decision.get("name") or decision.get("tool")
                params = decision.get("arguments") or decision.get("params", {})

                # 如果参数为空但用户输入包含概念名，提取它
                if not params or params.get("term") is None:
                    term = self._extract_term_fallback(user_input)
                    if term:
                        params["term"] = term

                logger.info(f"[TOOL CALL] tool={tool_name}, params={params}")

                # 执行工具
                result = await self._execute_tool(tool_name, params)

                logger.info(f"[TOOL RESULT] tool={tool_name}, result={result}")

                # 处理结果
                await self._handle_result(tool_name, result, params)

            except KeyboardInterrupt:
                print("\n\n退出")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                print(f"发生错误: {e}")
                break
        else:
            logger.warning(f"Reached max iterations ({max_iterations}), exiting")
            print(f"\n已达到最大迭代次数 ({max_iterations})，自动退出")

        return 0

    async def _decide_tool(
        self,
        system_msg: Dict,
        messages: List[Dict],
        user_input: str
    ) -> Optional[Dict]:
        """使用 Function Call 决定工具"""

        # 构建消息
        all_messages = [system_msg] + messages[-5:]  # 最近5条

        try:
            response = self.llm.chat_with_tools(all_messages, TOOLS)
            logger.info(f"[LLM RESPONSE] {response}")

            if response.get("type") == "function":
                return {
                    "name": response.get("name"),
                    "arguments": response.get("arguments", {})
                }
            else:
                # 文本响应，打印并返回 None
                content = response.get("content", "")
                if content:
                    print(f"\n{content}\n")
                return None

        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            # 降级：根据输入简单判断
            if "学习" in user_input or "了解" in user_input:
                return {"name": "build", "arguments": {"term": user_input.replace("学习", "").replace("了解", "").strip()}}
            return None

    async def _execute_tool(self, tool_name: str, params: Dict) -> Dict:
        """执行工具"""
        logger.info(f"[_execute_tool] tool_name={tool_name}, params={params}")
        tool = self.registry.get(tool_name)
        if not tool:
            logger.error(f"[_execute_tool] Tool not found: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            logger.info(f"[_execute_tool] Executing {tool_name}...")
            result = await tool.execute(params, {})
            logger.info(f"[_execute_tool] result.success={result.success}, data={result.data}")
            if result.success:
                return result.data
            else:
                logger.error(f"[_execute_tool] Tool error: {result.error}")
                return {"error": result.error}
        except Exception as e:
            logger.error(f"[_execute_tool] Exception: {e}")
            return {"error": str(e)}

    async def _handle_result(self, tool_name: str, result: Dict, params: Dict) -> None:
        """处理工具结果"""
        logger.debug(f"[_handle_result] tool={tool_name}, params={params}")
        if "error" in result:
            print(f"错误: {result['error']}")
            return

        if tool_name == "build":
            self.anchors = result
            self.current_term = params.get("term", self.current_term)
            print("✅ 知识结构构建完成")

            # 自动进入讲解
            await self._handle_result("teach", await self._execute_tool("teach", {
                "term": self.current_term,
                "anchors": self.anchors
            }), params)

        elif tool_name == "teach":
            # 直接显示讲解内容
            print("\n" + "=" * 40)
            print("📖 讲解")
            print("=" * 40)
            print(result.get("content", ""))
            print("\n" + "=" * 40)
            print("有什么问题想问吗？（输入问题或按 Ctrl+C 退出）")
            # 设置状态，等待用户输入问题
            self.state = AgentState.WAITING_SELECTION

        elif tool_name == "answer":
            print("\n" + "=" * 40)
            print("💡 回答")
            print("=" * 40)
            print(result.get("answer", ""))

        elif tool_name == "summarize":
            print("\n" + "=" * 40)
            print("📚 学习总结")
            print("=" * 40)
            print(result.get("summary", ""))
            if result.get("suggestions"):
                print("\n📝 下一步建议:")
                for s in result.get("suggestions", []):
                    print(f"  • {s}")

            # 标记为已学习
            if self.current_term and self.current_term not in self.learned_terms:
                self.learned_terms.append(self.current_term)

            print("\n再见！")
            self.state = AgentState.IDLE

        elif tool_name == "finish":
            print(result.get("message", "再见！"))


# 便捷函数
def create_agent() -> LearnMateAgent:
    """创建 Agent 实例"""
    return LearnMateAgent()


async def run_agent(max_iterations: int = 100) -> int:
    """运行 Agent

    Args:
        max_iterations: 最大迭代次数，防止测试时死循环
    """
    agent = create_agent()
    return await agent.run(max_iterations=max_iterations)