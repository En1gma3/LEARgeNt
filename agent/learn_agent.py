"""
LearnMate Agent - 单循环架构

主Agent Loop + 工具调用 (使用 Anthropic Messages API)
LLM 是导演，工具是演员。
"""

import json
from typing import Any, Dict, List, Optional

from agent.state import AgentState
from agent.tools.registry import get_registry
from agent.llm_client import get_llm_client
from agent.anthropic_messages import (
    user_message,
    assistant_message,
    assistant_message_with_tool,
    tool_result_content_block,
    create_tool_use_id,
)
from cli.selector import readline_with_chinese
from utils import get_logger

logger = get_logger(__name__)


class LearnMateAgent:
    """LearnMate 主 Agent - 单一 LLM 决策循环 + 工具调用"""

    def __init__(self):
        self.registry = get_registry()
        self.state = AgentState.IDLE
        self.current_term: Optional[str] = None
        self.anchors: Optional[Dict] = None
        self.learned_terms: List[str] = []
        self.message_history: List[Dict[str, Any]] = []

        self._llm = None
        logger.info("LearnMateAgent initialized")

    @property
    def llm(self):
        """获取 LLM 客户端"""
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    async def run(self, max_iterations: int = 100) -> int:
        """主循环

        Args:
            max_iterations: 最大迭代次数，防止测试时死循环
        """
        print("=" * 50)
        print("灵恩婕L - 智能学习助手")
        print("=" * 50)
        print("嗨，我是灵恩婕，很高兴遇见你。学习也好、问题也好，我们可以一起慢慢拆解，不用着急，我会一直在你身边帮你找到答案。")
        print("今天想学习什么？")

        system_prompt = """你是一个智能学习助手，采用苏格拉底式对话帮助用户学习概念。

【核心目标】
通过提问引导用户主动思考，而不是直接给出答案，帮助用户真正理解概念。

【教学策略】
1. 先评估用户理解水平
2. 引导式提问，每次最多1-2个问题
3. 解释时用类比、生活例子
4. 错误处理用追问代替否定
5. 阶段结束时简要总结

【对话风格】
- 亲切友善，像耐心导师
- 优先以提问结尾（除非解释或总结）
- 单次输出不超过5句话

请直接用中文回复用户。"""

        system_msg = {"role": "system", "content": system_prompt}

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            try:
                user_input = readline_with_chinese("> ")
                if not user_input:
                    continue

                if user_input.lower() in ["/exit", "/quit", "exit", "quit", "退出"]:
                    print("再见！")
                    break

                self.message_history.append(user_message(user_input))
                logger.info(f"[USER INPUT] {user_input}")

                TOOLS = self.registry.get_tools_for_llm()
                response = self.llm.chat_with_tools(
                    [system_msg] + self.message_history,
                    TOOLS
                )
                logger.info(f"[LLM RESPONSE] {response}")

                if response.get("type") == "tool_use":
                    tool_calls = response.get("tool_calls", [])
                    if not tool_calls:
                        continue

                    tool_call = tool_calls[0]
                    tool_name = tool_call.get("name")
                    tool_input = tool_call.get("input", {})
                    tool_use_id = tool_call.get("id", create_tool_use_id())

                    # 1. 添加 assistant 的 tool_use 消息到历史
                    self.message_history.append(assistant_message_with_tool(
                        tool_use_id=tool_use_id,
                        tool_name=tool_name,
                        tool_input=tool_input
                    ))

                    # 2. 执行工具
                    result = await self._execute_tool(tool_name, tool_input)

                    # 3. 处理结果并加入 message_history
                    userFacingText = await self._handle_export_result(
                        tool_use_id=tool_use_id,
                        result=result
                    )
                    print(userFacingText)

                    # 4. 继续对话让 LLM 生成最终回复
                    continue_response = self.llm.chat(
                        [system_msg] + self.message_history,
                        max_tokens=4096
                    )
                    print(continue_response)
                    self.message_history.append(assistant_message(continue_response))
                else:
                    response_text = response.get("content", "")
                    print(f"\n{response_text}\n")
                    self.message_history.append(assistant_message(response_text))

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

    async def handle_input(self, user_input: str) -> str:
        """处理单条用户输入（供 Feishu 等非交互式接口调用）

        Args:
            user_input: 用户输入的文本

        Returns:
            Agent 的回复文本
        """
        logger.info(f"[LearnMateAgent.handle_input] user_input={user_input}")

        # 新增：/clear 指令检测
        if user_input.strip() == "/clear":
            self.message_history = []
            self.state = AgentState.IDLE
            self.current_term = None
            self.anchors = None
            logger.info(f"Session cleared")
            return "好的，已开启新的对话！之前的上下文已清除。"

        system_prompt = """你是一个智能学习助手，采用苏格拉底式对话帮助用户学习概念。

【核心目标】
通过提问引导用户主动思考，而不是直接给出答案，帮助用户真正理解概念。

【教学策略】
1. 先评估用户理解水平
2. 引导式提问，每次最多1-2个问题
3. 解释时用类比、生活例子
4. 错误处理用追问代替否定
5. 阶段结束时简要总结

【对话风格】
- 亲切友善，像耐心导师
- 优先以提问结尾（除非解释或总结）
- 单次输出不超过5句话

请直接用中文回复用户。"""

        system_msg = {"role": "system", "content": system_prompt}

        try:
            self.message_history.append(user_message(user_input))

            TOOLS = self.registry.get_tools_for_llm()
            response = self.llm.chat_with_tools(
                [system_msg] + self.message_history,
                TOOLS
            )
            logger.info(f"[LearnMateAgent.handle_input] LLM response type: {response.get('type')}")

            if response.get("type") == "tool_use":
                tool_calls = response.get("tool_calls", [])
                if not tool_calls:
                    return "我没有理解你的意思，请再说一次。"

                tool_call = tool_calls[0]
                tool_name = tool_call.get("name")
                tool_input = tool_call.get("input", {})
                tool_use_id = tool_call.get("id", create_tool_use_id())

                self.message_history.append(assistant_message_with_tool(
                    tool_use_id=tool_use_id,
                    tool_name=tool_name,
                    tool_input=tool_input
                ))

                result = await self._execute_tool(tool_name, tool_input)

                userFacingText = await self._handle_export_result(
                    tool_use_id=tool_use_id,
                    result=result
                )

                continue_response = self.llm.chat(
                    [system_msg] + self.message_history,
                    max_tokens=4096
                )
                self.message_history.append(assistant_message(continue_response))
                return continue_response
            else:
                response_text = response.get("content", "")
                self.message_history.append(assistant_message(response_text))
                return response_text

        except Exception as e:
            logger.error(f"[LearnMateAgent.handle_input] Error: {e}", exc_info=True)
            return f"发生错误: {e}"

    async def _execute_tool(self, tool_name: str, params: Dict) -> Dict:
        """执行工具"""
        logger.info(f"[_execute_tool] tool_name={tool_name}, params={params}")
        tool = self.registry.get(tool_name)
        if not tool:
            logger.error(f"[_execute_tool] Tool not found: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            logger.info(f"[_execute_tool] Executing {tool_name}...")
            context = {
                "message_history": self.message_history,
                "current_term": self.current_term,
                "anchors": self.anchors,
            }
            result = await tool.execute(params, context)
            logger.info(f"[_execute_tool] result.success={result.success}, data={result.data}")
            if result.success:
                return result.data
            else:
                logger.error(f"[_execute_tool] Tool error: {result.error}")
                return {"error": result.error}
        except Exception as e:
            logger.error(f"[_execute_tool] Exception: {e}")
            return {"error": str(e)}

    async def _handle_export_result(self, tool_use_id: str, result: Dict) -> str:
        """处理导出工具结果，按 Anthropic 格式加入 message_history"""
        success = result.get("success", False)

        if success:
            tool_result_content = json.dumps({
                "success": True,
                "message": result.get("message", "已经完成知识库总结")
            }, ensure_ascii=False)
            is_error = False
        else:
            tool_result_content = json.dumps({
                "success": False,
                "error": result.get("error", "未知错误")
            }, ensure_ascii=False)
            is_error = True

        tool_result_msg = user_message([
            tool_result_content_block(
                tool_use_id=tool_use_id,
                content=tool_result_content,
                is_error=is_error
            )
        ])
        self.message_history.append(tool_result_msg)

        if success:
            return f"✅ 已完成知识库总结"
        else:
            return f"❌ 导出失败：{result.get('error', '未知错误')}"


def create_agent() -> LearnMateAgent:
    """创建 Agent 实例"""
    return LearnMateAgent()


async def run_agent(max_iterations: int = 100) -> int:
    """运行 Agent"""
    agent = create_agent()
    return await agent.run(max_iterations=max_iterations)
