"""
苏格拉底引导核心模块

实现苏格拉底式学习引导的对话流程管理。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from .types import QuestionType, HintLevel, DialogueState
from .prompt import (
    SOCRATIC_SYSTEM_PROMPT,
    DIAGNOSIS_PROMPT,
    SUMMARY_PROMPT,
    get_socratic_prompt_for_term
)


# 导入LLM客户端
try:
    from ..llm_client import get_llm_client, create_llm_client, BaseLLMClient
except ImportError:
    BaseLLMClient = object


@dataclass
class DialogueTurn:
    """对话轮次"""

    question: str
    student_answer: str
    question_type: Optional[QuestionType] = None
    ai_feedback: Optional[str] = None


@dataclass
class SocraticSession:
    """苏格拉底学习会话"""

    term: str  # 学习的主题
    definition: str  # 主题的定义
    turns: List[DialogueTurn] = field(default_factory=list)
    state: DialogueState = DialogueState.DIAGNOSIS
    current_question_type: Optional[QuestionType] = None
    hint_level: int = 0  # 当前提示层级
    understanding_level: float = 0.0  # 理解程度 0-1
    is_completed: bool = False

    # 学生对当前问题的回答
    current_answer: Optional[str] = None


class SocraticGuide:
    """
    苏格拉底式学习引导器

    负责管理整个苏格拉底对话流程：
    1. 诊断理解
    2. 拆解问题 + 引导推理
    3. 识别错误 + 提供提示
    4. 引导学生总结
    5. AI结构化总结
    """

    def __init__(self, max_turns: int = 5, llm_client=None):
        """
        初始化

        Args:
            max_turns: 最大对话轮次
            llm_client: LLM客户端，默认使用全局客户端
        """
        self.max_turns = max_turns
        self._llm_client = llm_client

    @property
    def llm_client(self):
        """获取LLM客户端"""
        if self._llm_client is None:
            try:
                self._llm_client = get_llm_client()
            except Exception:
                pass
        return self._llm_client

    def start_session(self, term: str, definition: str) -> SocraticSession:
        """
        开始一个新的学习会话

        Args:
            term: 学习的主题
            definition: 主题的定义

        Returns:
            SocraticSession: 学习会话对象
        """
        session = SocraticSession(
            term=term,
            definition=definition,
            state=DialogueState.DIAGNOSIS
        )
        return session

    def get_first_question(self, session: SocraticSession) -> str:
        """
        获取第一个问题（诊断理解）

        Args:
            session: 当前会话

        Returns:
            str: 第一个问题
        """
        # 使用LLM生成问题
        if self.llm_client:
            return self._generate_question_with_llm(session, "diagnosis")

        # 降级到模板
        return f"在学习'{session.term}'之前，请问你对'{session.term}'有哪些了解？"

    def get_diagnosis_prompt(self, session: SocraticSession) -> str:
        """
        获取诊断理解阶段的提示

        Args:
            session: 当前会话

        Returns:
            str: 诊断提示
        """
        return f"""{session.definition}

请问：你对"{session.term}"的理解是什么？"""

    def get_next_question(
        self,
        session: SocraticSession,
        student_answer: str
    ) -> str:
        """
        根据学生回答，获取下一个问题

        Args:
            session: 当前会话
            student_answer: 学生的回答

        Returns:
            str: 下一个问题
        """
        # 记录学生的回答
        turn = DialogueTurn(
            question=session.turns[-1].question if session.turns else "",
            student_answer=student_answer,
            question_type=session.current_question_type
        )
        session.turns.append(turn)

        # 使用LLM生成下一个问题
        if self.llm_client:
            return self._generate_question_with_llm(session, "guiding", student_answer)

        # 降级到规则引擎
        return self._rule_based_question(session, student_answer)

    def _generate_question_with_llm(
        self,
        session: SocraticSession,
        phase: str,
        student_answer: str = ""
    ) -> str:
        """使用LLM生成问题"""
        try:
            # 构建消息
            messages = [
                {"role": "system", "content": self._build_system_prompt(session)}
            ]

            # 添加对话历史
            for turn in session.turns[-3:]:  # 最近3轮
                if turn.question:
                    messages.append({"role": "assistant", "content": turn.question})
                if turn.student_answer:
                    messages.append({"role": "user", "content": turn.student_answer})

            # 根据阶段添加不同的问题请求
            if phase == "diagnosis":
                messages.append({
                    "role": "user",
                    "content": f"学生正在学习'{session.term}'。请生成一个诊断问题，询问学生对这个概念的理解程度。"
                })
            elif phase == "guiding":
                messages.append({
                    "role": "user",
                    "content": f"学生的回答是：'{student_answer}'。请根据学生的回答，生成一个苏格拉底式的问题来引导学生深入思考。问题类型可以是：澄清、假设、证据、反例、推论、元认知。"
                })
            elif phase == "summary":
                messages.append({
                    "role": "user",
                    "content": "请引导学生用自己的话总结这个概念的核心要点。"
                })

            response = self.llm_client.chat(messages)
            return response.strip()

        except Exception as e:
            print(f"LLM调用失败: {e}")
            return self._rule_based_question(session, student_answer)

    def _build_system_prompt(self, session: SocraticSession) -> str:
        """构建系统提示词"""
        return f"""你是一位苏格拉底式的学习导师。你的任务是引导学生自己思考和发现答案，而不是直接给出答案。

当前学习主题: {session.term}
主题定义: {session.definition}

苏格拉底提问原则：
1. 答案保留：不直接给答案，通过提问引导
2. 小步推进：逐步拆解大问题
3. 鼓励解释：要求说明推理过程
4. 认知冲突：引导发现逻辑矛盾
5. 结构总结：最终必须总结

六类核心问题：
- 澄清问题：理解学生想法
- 假设问题：找出隐含假设
- 证据问题：要求支持理由
- 反例问题：测试理论稳固性
- 推论问题：探索结论影响
- 元认知问题：训练反思思维

请根据学生的回答，选择合适的问题类型进行提问。"""

    def _rule_based_question(
        self,
        session: SocraticSession,
        student_answer: str
    ) -> str:
        """基于规则的问题生成（LLM不可用时的降级方案）"""
        # 根据当前状态决定下一步
        if session.state == DialogueState.DIAGNOSIS:
            # 诊断完成，进入引导推理
            session.state = DialogueState.GUIDING
            return self._generate_guiding_question(session, student_answer)

        elif session.state == DialogueState.GUIDING:
            # 继续引导推理
            return self._generate_guiding_question(session, student_answer)

        elif session.state == DialogueState.HINT:
            # 用户请求提示或回答错误
            return self._generate_hint_question(session, student_answer)

        elif session.state == DialogueState.STUDENT_SUMMARY:
            # 引导学生总结
            return "现在你能用一句话总结一下这个概念吗？"

        else:
            # 默认进入总结
            return self._generate_summary_prompt(session)

    def _generate_guiding_question(
        self,
        session: SocraticSession,
        student_answer: str
    ) -> str:
        """
        生成引导问题

        根据学生的回答，动态选择合适的问题类型
        """
        # 根据回答内容判断理解程度
        if self._is_answer_correct(session, student_answer):
            # 理解正确，追问更深层问题
            session.understanding_level = min(
                1.0,
                session.understanding_level + 0.2
            )
            return self._generate_deeper_question(session)
        elif self._is_answer_partial(session, student_answer):
            # 部分理解，提供线索
            session.current_question_type = QuestionType.CLARIFICATION
            return f"你说得有些道理。那么，{session.term}的{self._get_key_aspect(session)}具体是什么呢？"
        else:
            # 理解错误或模糊，提供提示
            session.state = DialogueState.HINT
            return self._generate_hint_question(session, student_answer)

    def _generate_deeper_question(self, session: SocraticSession) -> str:
        """生成更深层的问题"""
        # 根据理解程度选择问题类型
        if session.understanding_level < 0.3:
            # 刚开始理解，用澄清问题
            session.current_question_type = QuestionType.CLARIFICATION
            return f"你说得对。那你能解释一下为什么{self._get_key_aspect(session)}吗？"

        elif session.understanding_level < 0.6:
            # 有一定理解，用推论问题
            session.current_question_type = QuestionType.IMPLICATION
            return f"很好。那{session.term}的这个特性会带来什么影响呢？"

        elif session.understanding_level < 0.9:
            # 理解较深入，用反例问题
            session.current_question_type = QuestionType.COUNTEREXAMPLE
            return f"理解得很准确。那在什么情况下{session.term}可能不适用？"

        else:
            # 理解很好了，进入总结
            session.state = DialogueState.STUDENT_SUMMARY
            return "非常好！现在你能用自己的话总结一下这个概念吗？"

    def _generate_hint_question(
        self,
        session: SocraticSession,
        student_answer: str
    ) -> str:
        """生成提示性问题"""
        session.hint_level += 1

        if session.hint_level == 1:
            # Level 1: 提醒概念
            return f"我给你一个提示：{session.term}的核心是{self._get_key_aspect(session)}，你可以从这方面想想。"

        elif session.hint_level == 2:
            # Level 2: 指出关键变量
            return f"关键在于理解{self._get_key_aspect(session)}和它的作用之间的关系。你能想到什么例子吗？"

        else:
            # Level 3: 提供部分答案
            return f"你可以这样理解：{session.term}的本质是{self._get_partial_answer(session)}。你觉得对吗？"

    def _generate_summary_prompt(self, session: SocraticSession) -> str:
        """生成总结提示"""
        return SUMMARY_PROMPT.format(term=session.term)

    def _is_answer_correct(
        self,
        session: SocraticSession,
        answer: str
    ) -> bool:
        """判断回答是否正确"""
        # 简化实现：检查回答长度
        return len(answer) > 10

    def _is_answer_partial(
        self,
        session: SocraticSession,
        answer: str
    ) -> bool:
        """判断回答是否部分正确"""
        return len(answer) > 5

    def _get_key_aspect(self, session: SocraticSession) -> str:
        """获取主题的关键方面"""
        return "核心原理"

    def _get_partial_answer(self, session: SocraticSession) -> str:
        """获取部分答案"""
        return session.definition[:50] + "..."

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return SOCRATIC_SYSTEM_PROMPT

    def get_term_prompt(self, term: str) -> str:
        """获取针对特定术语的提示词"""
        return get_socratic_prompt_for_term(term)

    def should_continue(self, session: SocraticSession) -> bool:
        """判断是否继续引导"""
        if session.is_completed:
            return False
        if len(session.turns) >= self.max_turns:
            session.is_completed = True
            return False
        return True

    def generate_ai_summary(self, session: SocraticSession) -> str:
        """
        使用LLM生成AI总结

        Args:
            session: 当前会话

        Returns:
            str: 结构化总结
        """
        # 使用LLM生成总结
        if self.llm_client:
            try:
                messages = [
                    {"role": "system", "content": "你是一位知识渊博的学习导师，请根据学生的对话生成结构化总结。"},
                    {"role": "user", "content": f"""请为学习主题'{session.term}'生成学习总结。

主题定义: {session.definition}

对话历史:
{self._format_conversation(session)}

请生成包含以下内容的总结：
1. 核心要点 (3-5点)
2. 关键原理
3. 相关概念
4. 实践建议
"""}
                ]
                response = self.llm_client.chat(messages)
                session.is_completed = True
                session.state = DialogueState.COMPLETED
                return f"✅ {session.term} 学习完成！\n\n{response}"
            except Exception as e:
                print(f"LLM总结生成失败: {e}")

        # 降级到模板
        return self._template_summary(session)

    def _format_conversation(self, session: SocraticSession) -> str:
        """格式化对话历史"""
        lines = []
        for i, turn in enumerate(session.turns, 1):
            lines.append(f"轮次{i}:")
            if turn.question:
                lines.append(f"  AI: {turn.question}")
            if turn.student_answer:
                lines.append(f"  学生: {turn.student_answer}")
        return "\n".join(lines) if lines else "无对话记录"

    def _template_summary(self, session: SocraticSession) -> str:
        """模板总结"""
        session.is_completed = True
        session.state = DialogueState.COMPLETED

        return f"""✅ {session.term} 学习完成！

📌 核心要点
{self._extract_key_points(session)}

📌 关键原理
{self._extract_principles(session)}

📌 相关概念
→ {self._get_related_terms(session)}

继续学习其他概念，或使用 /tag add {session.term} <标签> 添加标签。
"""

    def complete_session(self, session: SocraticSession) -> str:
        """
        完成会话（兼容旧接口）

        Args:
            session: 当前会话

        Returns:
            str: 结构化总结
        """
        return self.generate_ai_summary(session)

    def _extract_key_points(self, session: SocraticSession) -> str:
        """提取关键要点"""
        return f"- {session.term}的核心定义"

    def _extract_principles(self, session: SocraticSession) -> str:
        """提取原理"""
        return session.definition[:100] if session.definition else "详见定义"

    def _get_related_terms(self, session: SocraticSession) -> str:
        """获取相关术语"""
        return "无"
