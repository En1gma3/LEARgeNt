"""
工具实现

9个工具: build, answer, teach, decompose, summarize, select, fetch, finish, export_obsidian
"""

import json
from typing import Any, Dict, List, Optional

from agent.tools.registry import BaseTool, ToolResult
from agent.llm_client import get_llm_client
from agent.config import get_vault_dir
from cli.selector import readline_with_chinese
from utils import get_logger

logger = get_logger(__name__)


# ============================================================
# P0: 核心工具 - 需要子Agent
# ============================================================

class BuildTool(BaseTool):
    """构建三锚点知识结构"""

    def __init__(self):
        super().__init__(
            name="build",
            description="为概念构建完整的三锚点知识结构",
            needs_agent=True
        )

    async def execute(self, params: Dict, context: Dict) -> ToolResult:
        term = params.get("term", "")
        definition = params.get("definition", "")

        if not term:
            return ToolResult(success=False, data=None, error="term is required")

        try:
            anchors = await self._build_anchors(term, definition)
            return ToolResult(success=True, data=anchors)
        except Exception as e:
            logger.error(f"Build tool failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def get_anthropic_schema(self) -> Dict:
        return {
            "name": "build",
            "description": """当用户想要学习某个概念时使用。当用户说"学习XX"、"了解XX"、"教我XX"、"解释XX"等意图学习的表达时调用。
此工具会为概念构建完整的三锚点知识结构：
- topic_anchor: 概念所属的主题领域
- dependency_anchors: 理解该概念需要先掌握的前置知识点
- semantic_anchor: 一句话精确定义概念本质
- contrast_anchor: 容易混淆的概念及其区别
- example_anchor: 典型使用场景或例子""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "要学习的概念名称"
                    },
                    "definition": {
                        "type": "string",
                        "description": "概念的定义或描述（可选，用户已提供时填入）"
                    }
                },
                "required": ["term"]
            }
        }

    async def _build_anchors(self, term: str, definition: str) -> Dict:
        """调用LLM构建三锚点"""
        prompt = f"""你是一个知识结构化专家。你的任务是为给定的术语/概念构建"三锚点"结构。

## 三锚点定义

1. **主题锚点 (topic_anchor)**: 这个概念属于哪个更大的主题/领域？

2. **依赖锚点 (dependency_anchors)**: 理解这个概念需要先掌握哪些前置概念？（列出3-5个）
   - 要具体不要抽象，例如：葡萄酒领域应包含具体品种（赤霞珠、美乐、黑皮诺）
   - 地理区域应包含具体产区（波尔多、勃艮第）

3. **语义锚点 (semantic_anchor)**: 用一句话精确定义这个概念的本质（30字以内）

4. **对比锚点 (contrast_anchor)** (可选): 这个概念容易与哪个概念混淆？区别是什么？

5. **举例锚点 (example_anchor)** (可选): 一个典型的使用场景或例子

## 输入

术语名称: {term}
定义/描述: {definition or '无'}

## 输出格式

请以 JSON 格式输出：
{{
    "topic_anchor": "主题锚点",
    "dependency_anchors": ["依赖1", "依赖2", "依赖3"],
    "semantic_anchor": "一句话定义",
    "contrast_anchor": "对比概念和区别（如有）",
    "example_anchor": "典型例子（如有）"
}}

请直接输出 JSON，不要有其他内容。"""

        messages = [{"role": "user", "content": prompt}]
        llm = get_llm_client()
        response = llm.chat(messages, max_tokens=196607)

        return self._parse_anchors(response)

    def _parse_anchors(self, response: str) -> Dict:
        """解析LLM响应为锚点"""
        try:
            data = self._extract_json_from_response(response)
            return {
                "topic_anchor": data.get("topic_anchor", ""),
                "dependency_anchors": data.get("dependency_anchors", []),
                "semantic_anchor": data.get("semantic_anchor", ""),
                "contrast_anchor": data.get("contrast_anchor", ""),
                "example_anchor": data.get("example_anchor", "")
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse anchors JSON: {e}")
            return {
                "topic_anchor": "未分类",
                "dependency_anchors": [],
                "semantic_anchor": "解析失败",
                "contrast_anchor": "",
                "example_anchor": ""
            }


class AnswerTool(BaseTool):
    """回答问题并追问"""

    def __init__(self):
        super().__init__(
            name="answer",
            description="基于锚点回答用户问题，并生成追问引导深入思考",
            needs_agent=True
        )

    async def execute(self, params: Dict, context: Dict) -> ToolResult:
        term = params.get("term", "")
        question = params.get("question", "")
        anchors = params.get("anchors", {})
        history = params.get("history", [])

        if not term or not question:
            return ToolResult(success=False, data=None, error="term and question are required")

        try:
            result = await self._answer_question(term, question, anchors, history)
            return ToolResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Answer tool failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def get_anthropic_schema(self) -> Dict:
        return {
            "name": "answer",
            "description": """当用户对当前学习的概念提出具体问题时使用，如"XX是什么"、"为什么XX"、"XX和XX的区别"等。
此工具基于三锚点知识结构回答问题，并在回答末尾生成追问引导用户深入思考。""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "当前学习的概念名称"
                    },
                    "question": {
                        "type": "string",
                        "description": "用户提出的具体问题"
                    },
                    "anchors": {
                        "type": "object",
                        "description": "概念的三锚点知识结构"
                    },
                    "history": {
                        "type": "array",
                        "description": "对话历史记录"
                    }
                },
                "required": ["term", "question"]
            }
        }

    async def _answer_question(self, term: str, question: str, anchors: Dict, history: List) -> Dict:
        """调用LLM回答问题"""
        # 格式化历史
        history_text = ""
        if history:
            history_text = "\n".join([
                f"- {h.get('role', '')}: {h.get('content', '')}"
                for h in history[-5:]  # 最近5条
            ])
        else:
            history_text = "（无历史对话）"

        prompt = f"""你是一位知识渊博的学习导师。请基于知识结构回答学生的问题，结合对话历史，引导学生深入思考。

## 对话历史
{history_text}

## 知识结构

- **主题领域**: {anchors.get('topic_anchor', '未知')}
- **前置概念**: {', '.join(anchors.get('dependency_anchors', [])) or '无'}
- **核心定义**: {anchors.get('semantic_anchor', '未知')}
- **对比区分**: {anchors.get('contrast_anchor', '无')}
- **典型例子**: {anchors.get('example_anchor', '无')}

## 学生问题

{question}

## 要求

1. 结合对话历史上下文，准确回答问题
2. 回答要层层递进，从具体到抽象
3. 在回答末尾自然抛出新的思考问题，引导学生继续探索
4. 如果对话历史中已经有类似的问题被问过，考虑换个角度追问

请直接输出回答内容（包含引导性问题）："""

        messages = [{"role": "user", "content": prompt}]
        llm = get_llm_client()
        response = llm.chat(messages, max_tokens=196607)

        return self._parse_answer(response)

    def _parse_answer(self, response: str) -> Dict:
        """解析LLM响应 - 现在是纯文本"""
        return {
            "answer": response
        }


class TeachTool(BaseTool):
    """生成讲解并评估理解"""

    def __init__(self):
        super().__init__(
            name="teach",
            description="基于锚点生成概念讲解，并给出理解建议",
            needs_agent=True
        )

    async def execute(self, params: Dict, context: Dict) -> ToolResult:
        term = params.get("term", "")
        anchors = params.get("anchors", {})
        history = params.get("history", [])

        if not term:
            return ToolResult(success=False, data=None, error="term is required")

        try:
            result = await self._generate_teaching(term, anchors)
            return ToolResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Teach tool failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    async def _generate_teaching(self, term: str, anchors: Dict) -> Dict:
        """调用LLM生成讲解"""
        prompt = f"""你是一位深入浅出的学习导师。请为学生讲解以下概念。

## 概念信息

- **概念名称**: {term}
- **主题领域**: {anchors.get('topic_anchor', '未知')}
- **前置概念**: {', '.join(anchors.get('dependency_anchors', [])) or '无'}
- **核心定义**: {anchors.get('semantic_anchor', '未知')}
- **对比区分**: {anchors.get('contrast_anchor', '无')}
- **典型例子**: {anchors.get('example_anchor', '无')}

## 讲解要求

1. 用通俗易懂的语言解释概念
2. 从已知知识引入新概念
3. 给出具体的例子帮助理解
4. 指出常见的理解误区

## 输出格式

请用以下格式输出：

**核心总结**: 一句话概括

---
**分节讲解**:
[标题1]: 内容...
[标题2]: 内容...

---
**常见误区**:
- 误区1: ...
- 误区2: ...

---
**思考问题**:
在讲解最后，自然地提出3个引导性问题，引发学生深入思考。不要用列表形式，而是用句子自然地融入讲解末尾。

讲解完成后，说："你可以问我上面的问题，或自由提问任何相关内容。"

请直接输出讲解内容："""

        messages = [{"role": "user", "content": prompt}]
        llm = get_llm_client()
        response = llm.chat(messages, max_tokens=196607)

        return self._parse_teaching(response)

    def _parse_teaching(self, response: str) -> Dict:
        """解析LLM响应 - 现在是纯文本"""
        return {
            "content": response  # 直接返回纯文本内容
        }


# ============================================================
# P1: 重要工具 - 需要子Agent
# ============================================================

class DecomposeTool(BaseTool):
    """分解主题/维度"""

    def __init__(self):
        super().__init__(
            name="decompose",
            description="将主题分解为多个维度，或将维度分解为知识点",
            needs_agent=True
        )

    async def execute(self, params: Dict, context: Dict) -> ToolResult:
        input_str = params.get("input", "")
        decomp_type = params.get("type", "theme")  # "theme" or "dimension"
        ctx = params.get("context", "")

        if not input_str:
            return ToolResult(success=False, data=None, error="input is required")

        try:
            result = await self._decompose(input_str, decomp_type, ctx)
            return ToolResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Decompose tool failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    async def _decompose(self, input_str: str, decomp_type: str, context: str) -> Dict:
        """调用LLM分解"""
        if decomp_type == "theme":
            prompt = f"""将主题"{input_str}"分解为多个维度/方面。

要求：
- 列出3-6个主要维度
- 每个维度应该是理解该主题的一个方面
- 维度之间应该有清晰的区分

请以 JSON 数组格式输出：
["维度1", "维度2", "维度3", ...]

请只输出 JSON 数组，不要有其他内容。"""
        else:
            prompt = f"""主题"{context}"的"{input_str}"维度下，有哪些具体的学习点？

请列出3-5个具体知识点，每个知识点应该：
- 是一个独立的概念/术语
- 适合作为单独的学习单元

请以 JSON 数组格式输出：
["知识点1", "知识点2", "知识点3", ...]

请只输出 JSON 数组，不要有其他内容。"""

        messages = [{"role": "user", "content": prompt}]
        llm = get_llm_client()
        response = llm.chat(messages, max_tokens=196607)

        return self._parse_decompose(response, decomp_type)

    def _parse_decompose(self, response: str, decomp_type: str) -> Dict:
        """解析分解结果"""
        try:
            items = self._extract_json_from_response(response)
            if isinstance(items, list):
                return {
                    "items": [str(item) for item in items],
                    "reason": f"将{'主题' if decomp_type == 'theme' else '维度'}分解为{len(items)}个部分"
                }
            return {"items": [], "reason": "解析失败"}
        except json.JSONDecodeError:
            return {"items": [], "reason": "解析失败"}


class SummarizeTool(BaseTool):
    """生成学习总结"""

    def __init__(self):
        super().__init__(
            name="summarize",
            description="基于学习过程生成结构化总结和建议",
            needs_agent=True
        )

    async def execute(self, params: Dict, context: Dict) -> ToolResult:
        term = params.get("term", "")
        anchors = params.get("anchors", {})
        qa_history = params.get("qa_history", [])

        if not term:
            return ToolResult(success=False, data=None, error="term is required")

        try:
            result = await self._summarize(term, anchors, qa_history)
            return ToolResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Summarize tool failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    async def _summarize(self, term: str, anchors: Dict, qa_history: List) -> Dict:
        """调用LLM生成总结"""
        qa_text = self._format_qa(qa_history)

        prompt = f"""请为学习主题"{term}"生成结构化学习总结。

## 知识结构

- **主题领域**: {anchors.get('topic_anchor', '未知')}
- **前置概念**: {', '.join(anchors.get('dependency_anchors', [])) or '无'}
- **核心定义**: {anchors.get('semantic_anchor', '未知')}
- **典型例子**: {anchors.get('example_anchor', '无')}

## 问答历史

{qa_text or '无'}

## 要求

1. 总结核心要点（3-5点）
2. 提炼关键原理
3. 给出下一步学习建议

请用以下JSON格式输出：
{{
    "summary": "结构化总结内容",
    "suggestions": ["建议1", "建议2", "建议3"]
}}"""

        messages = [{"role": "user", "content": prompt}]
        llm = get_llm_client()
        response = llm.chat(messages, max_tokens=196607)

        return self._parse_summary(response)

    def _format_qa(self, qa_history: List) -> str:
        if not qa_history:
            return "无"
        lines = []
        for i, qa in enumerate(qa_history, 1):
            lines.append(f"Q{i}: {qa.get('question', '')}")
            lines.append(f"A{i}: {qa.get('answer', '')}")
        return '\n'.join(lines)

    def _parse_summary(self, response: str) -> Dict:
        """解析总结"""
        try:
            data = self._extract_json_from_response(response)
            return {
                "summary": data.get("summary", ""),
                "suggestions": data.get("suggestions", [])
            }
        except json.JSONDecodeError:
            return {
                "summary": response,
                "suggestions": ["继续实践，加深理解"]
            }


# ============================================================
# P2: 交互工具 - 不需要子Agent
# ============================================================

class SelectTool(BaseTool):
    """等待用户选择"""

    def __init__(self):
        super().__init__(
            name="select",
            description="显示选项列表并等待用户选择，最后一个选项支持用户输入",
            needs_agent=False
        )

    async def execute(self, params: Dict, context: Dict) -> ToolResult:
        options = params.get("options", [])
        prompt = params.get("prompt", "请选择：")

        if not options:
            return ToolResult(success=False, data=None, error="options is required")

        try:
            result = self._show_selector(options, prompt)
            return ToolResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Select tool failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def _show_selector(self, options: List[str], prompt: str) -> Dict:
        """显示选择器并等待用户输入"""
        from cli.selector import ArrowSelector

        print(f"\n{prompt}")
        print("-" * 40)

        selector = ArrowSelector(
            items=options,
            title=None,
            multi_column=False
        )

        idx = selector.run()

        if idx is None:
            # 用户取消
            return {"index": -1, "value": "", "is_custom": False}

        # 检查是否是最后一个选项（自定义输入）
        is_custom = (idx == len(options) - 1) and self._allows_custom_input(options)

        if is_custom:
            # 获取用户自定义输入
            custom_input = readline_with_chinese("请输入：")
            return {
                "index": idx,
                "value": custom_input,
                "is_custom": True
            }

        return {
            "index": idx,
            "value": options[idx],
            "is_custom": False
        }

    def _allows_custom_input(self, options: List[str]) -> bool:
        """检查是否允许自定义输入"""
        if len(options) < 2:
            return True
        last_option = options[-1].lower()
        return "其他" in last_option or "输入" in last_option or "custom" in last_option


# ============================================================
# P3: 辅助工具 - 不需要子Agent
# ============================================================

class FetchTool(BaseTool):
    """获取术语定义"""

    def __init__(self):
        super().__init__(
            name="fetch",
            description="从外部知识源获取术语定义",
            needs_agent=False
        )

    async def execute(self, params: Dict, context: Dict) -> ToolResult:
        term = params.get("term", "")

        if not term:
            return ToolResult(success=False, data=None, error="term is required")

        try:
            result = self._fetch_definition(term)
            return ToolResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Fetch tool failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def _fetch_definition(self, term: str) -> Dict:
        """从现有模块获取定义"""
        # 尝试使用现有的 extractor 模块
        try:
            from extractor.factory import ExtractorFactory

            # 尝试提取
            extractor = ExtractorFactory.create_extractor("llm")
            result = extractor.extract(term)

            if result:
                return {
                    "definition": result[0].name if result else "",
                    "source": "extractor",
                    "url": ""
                }
        except Exception as e:
            logger.debug(f"Extractor failed: {e}")

        # 降级：返回空定义
        return {
            "definition": "",
            "source": "",
            "url": ""
        }


# ============================================================
# 控制工具 - 不需要子Agent
# ============================================================

class FinishTool(BaseTool):
    """结束对话"""

    def __init__(self):
        super().__init__(
            name="finish",
            description="结束对话",
            needs_agent=False
        )

    async def execute(self, params: Dict, context: Dict) -> ToolResult:
        message = params.get("message", "再见！")
        return ToolResult(success=True, data={"message": message})


# ============================================================
# 导出工具
# ============================================================

class ExportObsidianTool(BaseTool):
    """导出学习会话到 Obsidian"""

    def __init__(self):
        super().__init__(
            name="export_obsidian",
            description=(
                "将学习会话导出为 Obsidian 格式的 Markdown 文件。"
                "在满足以下条件时调用："
                "1) 用户问题已被完整解答；"
                "2) 对话中已形成结构化知识（如总结、步骤或要点）；"
                "3) 用户未继续追问或明确表示理解（如'明白了'、'可以了'）。"
                "不要在用户仍在提问或内容未整理完成时调用。"
            ),
            needs_agent=True
        )
        from agent.tools.export import ObsidianExporter
        vault_dir = get_vault_dir()
        self._exporter = ObsidianExporter(vault_dir)

    async def execute(self, params: Dict, context: Dict) -> ToolResult:
        """导出学习会话到 Obsidian"""
        try:
            # 从context提取信息
            message_history = context.get("message_history", [])
            current_term = context.get("current_term", "未知概念")
            anchors = context.get("anchors") or {}

            if not message_history:
                return ToolResult(
                    success=False,
                    data=None,
                    error="没有对话历史可导出"
                )

            # 使用导出器
            result = await self._exporter.export(message_history, current_term, anchors)

            return ToolResult(success=True, data=result)
        except Exception as e:
            logger.error(f"ExportObsidianTool failed: {e}")
            return ToolResult(success=False, data=None, error=str(e))

    def get_anthropic_schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }