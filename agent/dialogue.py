"""
对话管理器

管理对话流程和状态
"""

from typing import Optional, Dict, Any, List

from memory import ShortTermMemory, LongTermMemory, KnowledgePoint
from knowledge import KnowledgeDB
from knowledge.models import Term
from utils import get_logger
from agent.anthropic_messages import user_message, assistant_message
from agent.state import AgentState

# 向后兼容别名
DialogueState = AgentState

logger = get_logger(__name__)


class DialogueManager:
    """对话管理器"""

    def __init__(self):
        logger.info("Initializing DialogueManager")
        self.state = DialogueState.IDLE
        self.short_memory = ShortTermMemory()
        self.long_memory = LongTermMemory()
        self.knowledge_db = KnowledgeDB()
        self.current_term: Optional[str] = None
        self.current_mode = "learn"  # learn/qa/review

        # 苏格拉底会话
        from agent.socratic import SocraticGuide, SocraticSession
        self.socratic_guide = SocraticGuide()
        self.socratic_session: Optional[SocraticSession] = None

        # Learn 模式专用状态
        self._pending_theme: Optional[str] = None  # 待拆解的主题
        self._pending_dimensions: List[str] = []  # 拆解后的维度
        self._pending_dimension: Optional[str] = None  # 当前选择的维度
        self._pending_kpoints: List[str] = []  # 当前维度下的知识点

        logger.info("DialogueManager initialized")

    def start_session(self, mode: str = "learn") -> str:
        """开始新会话"""
        logger.info(f"Starting new session with mode={mode}")
        session = self.short_memory.create_session(mode=mode)
        self.current_mode = mode
        self.state = DialogueState.IDLE

        # 检查到期复习
        from review import ReviewScheduler
        scheduler = ReviewScheduler()
        due = scheduler.get_due_reviews()
        if due:
            logger.info(f"Found {len(due)} due reviews")
            return f"提醒: 您有 {len(due)} 个名词需要复习"

        logger.info("No due reviews")
        return """欢迎使用 LearnMate - 智能学习助手！

📖 我能帮你：
   • 学习具体概念（如：工作量证明、梯度下降）
   • 拆解大主题（如：区块链、人工智能）
   • 通过苏格拉底式提问深化理解

🔍 使用方式：
   直接输入想学习的概念，例如：学习 区块链
   或输入主题名称，我会帮你拆解为多个学习维度

📌 提示：使用方向键 ↑↓ 选择维度，回车确认"""

    def handle_input(self, user_input: str) -> str:
        """处理用户输入"""
        logger.debug(f"handle_input called with: {user_input[:50]}...")

        # 检查是否在讲解模式
        if self.state == DialogueState.EXPLAINING and self.socratic_session:
            logger.debug("Currently in EXPLAINING state")
            return self._handle_explaining_response(user_input)

        # 检查是否在用户主导问答循环模式
        if self.state == DialogueState.Q_A_LOOP and self.socratic_session:
            logger.debug("Currently in Q_A_LOOP state")
            return self._handle_qa_loop(user_input)

        # 检查是否在总结模式
        if self.state == DialogueState.SUMMARIZING and self.socratic_session:
            logger.debug("Currently in SUMMARIZING state")
            return self._handle_summarizing(user_input)

        # 检查是否在苏格拉底引导模式
        if self.state == DialogueState.GUIDING and self.socratic_session:
            logger.debug("Currently in GUIDING state, delegating to socratic handler")
            return self._handle_socratic_response(user_input)

        # 检查是否在主题拆解模式
        if self.state == DialogueState.DECOMPOSING:
            logger.debug("Currently in DECOMPOSING state, delegating to dimension selection")
            return self._handle_dimension_selection(user_input)

        # 检查是否在知识点选择模式
        if self.state == DialogueState.SELECTING_KPOINT:
            logger.debug("Currently in SELECTING_KPOINT state")
            return self._handle_kpoint_selection(user_input)

        from .intent import IntentRecognizer, Intent

        # 意图识别
        recognizer = IntentRecognizer()
        intent, entity, params = recognizer.recognize(user_input)
        logger.debug(f"Intent recognized: {intent}, entity: {entity}, params: {params}")

        # 记录用户消息
        self.short_memory.add_user_message(user_input)

        # 根据意图处理
        if intent == Intent.LEARN:
            logger.info(f"Handling LEARN intent for: {entity}")
            return self._handle_learn(entity, params)
        elif intent == Intent.ASK:
            return self._handle_ask(user_input)
        elif intent == Intent.TAG:
            return self._handle_tag(entity, params)
        elif intent == Intent.CONTEXT:
            return self._handle_context(entity, params)
        elif intent == Intent.LIST:
            return self._handle_list(entity, params)
        elif intent == Intent.VIEW:
            logger.info(f"Handling VIEW intent for: {params.get('term')}")
            return self._handle_view(params.get('term'))
        elif intent == Intent.REVIEW:
            return self._handle_review(entity, params)
        elif intent == Intent.STATS:
            return self._handle_stats(params.get('period'))
        elif intent == Intent.MINDMAP:
            return self._handle_mindmap(params.get('term'), params.get('format'))
        elif intent == Intent.PATH:
            return self._handle_path(entity, params)
        elif intent == Intent.REMINDER:
            return self._handle_reminder(entity, params)
        elif intent == Intent.HELP:
            return self._handle_help(params.get('topic'))
        elif intent == Intent.SESSIONS:
            logger.info("Handling SESSIONS intent")
            return self._handle_sessions(params.get('action'))
        elif intent == Intent.MODE:
            return self._handle_mode(params.get('mode'))
        elif intent == Intent.QUIT:
            logger.info("QUIT intent received")
            return "再见！"
        else:
            logger.warning(f"Unknown intent: {user_input}")
            return self._handle_unknown(user_input)

    def _handle_learn(self, term: str, params: Dict) -> str:
        """处理学习请求"""
        # 优先使用params中的content
        if not term and params.get('content'):
            term = params['content']

        if not term:
            return "请输入要学习内容，例如：学习 区块链"

        # 调用 Learn Mode v2
        return self._handle_learn_v2(term, params)

    def _handle_learn_v2(self, entity: str, params: Dict) -> str:
        """
        Learn Mode v2 实现

        流程：
        1. 歧义检测 - 检查是否是歧义术语
        2. 主题判断 - 调用 LLM 判断是否为主题
        3. 知识库查询 - 检查是否已学过
        4. 信息搜集 - 从 Wikipedia 等获取信息
        5. 三锚点构建 - 使用 AnchorBuilder
        6. 存储 - 存入知识库和会话上下文
        7. Socratic 引导 - 启动苏格拉底会话
        8. 推荐下一步 - 由 LLM 推断
        """
        term = entity
        logger.info(f"Learn Mode v2: processing '{term}'")

        # 1. 检查是否已学习
        if self.long_memory.is_learned(term):
            return f"您已经学习过'{term}'了。输入/view {term}查看详情，或/review开始复习。"

        # 获取会话上下文（用于惰性工具）
        session = self.short_memory.get_current_session()

        # 如果没有会话，先创建一个
        if session is None:
            session = self.short_memory.create_session()

        # 2. 主题判断
        decomposer = session.get_theme_decomposer()
        is_theme = decomposer.check_is_theme(term)

        if is_theme:
            # 主题：需要拆解
            return self._handle_theme_learning(term, decomposer, session)
        else:
            # 具体概念：直接学习
            return self._handle_concept_learning(term, session)

    def _handle_theme_learning(
        self,
        theme: str,
        decomposer,
        session
    ) -> str:
        """
        处理主题学习（需要拆解）

        Args:
            theme: 主题名称
            decomposer: 主题拆解器
            session: 会话上下文
        """
        logger.info(f"Handling theme learning for: {theme}")

        # 拆解主题为维度
        dimensions = decomposer.decompose_theme(theme)

        if not dimensions:
            return f"无法拆解主题'{theme}'，请尝试学习更具体的概念。"

        self._pending_theme = theme
        self._pending_dimensions = dimensions
        self._pending_dimension = None
        self._pending_kpoints = []
        self.state = DialogueState.DECOMPOSING

        # 构建维度选择菜单（供文本输入 fallback）
        dim_list = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(dimensions))

        return f"""📚 主题: {theme}

"{theme}"是一个包含多个方面的主题，可以从以下维度学习：

{dim_list}

请选择要学习的维度（输入序号），或输入"取消"退出：

(CLI模式会自动使用方向键选择器)"""

    def _handle_concept_learning(self, term: str, session) -> str:
        """
        处理具体概念学习 - 讲解优先模式

        Args:
            term: 概念名称
            session: 会话上下文
        """
        logger.info(f"Handling concept learning for: {term}")

        # 信息搜集
        from features import FetcherManager
        fetcher_manager = FetcherManager()
        term_info = fetcher_manager.fetch_and_enhance(term)

        definition = term_info.structured_definition or term_info.definition if term_info else f"学习: {term}"
        source = term_info.source if term_info else ""
        source_url = term_info.url if term_info else ""

        # 三锚点构建
        anchor_builder = session.get_anchor_builder()
        kp = anchor_builder.build_knowledge_point(
            term_name=term,
            definition=definition,
            source=source,
            source_url=source_url
        )

        # 存入知识库（使用 Term 对象）
        term_obj = Term(
            id=kp.id,
            name=kp.name,
            definition=kp.definition,
            summary=kp.semantic_anchor or "",  # 使用语义锚点作为摘要
            source=kp.source or "manual",
            source_url=kp.source_url or ""
        )
        self.knowledge_db.add_term(term_obj)

        # 加入复习计划
        from review import ReviewScheduler
        scheduler = ReviewScheduler()
        scheduler.add_term(term_obj.id, term)

        # 记录到会话上下文
        session_kp = KnowledgePoint(
            id=kp.id,
            name=kp.name,
            definition=kp.definition,
            topic_anchor=kp.topic_anchor,
            dependency_anchors=kp.dependency_anchors,
            semantic_anchor=kp.semantic_anchor,
            contrast_anchor=kp.contrast_anchor,
            example_anchor=kp.example_anchor,
            source=kp.source,
            source_url=kp.source_url
        )
        session.add_learned_knowledge_point(session_kp)

        # 添加到已学习
        self.long_memory.add_learned_term(term)

        # 记录统计
        from features import StatisticsCollector
        stats = StatisticsCollector()
        stats.record_new_term()

        # 启动讲解模式会话
        self.state = DialogueState.EXPLAINING
        self.socratic_session = self.socratic_guide.start_session(term, definition)

        # 存储锚点供后续使用
        self.socratic_session.anchors = {
            'topic_anchor': kp.topic_anchor,
            'dependency_anchors': kp.dependency_anchors,
            'semantic_anchor': kp.semantic_anchor,
            'contrast_anchor': kp.contrast_anchor,
            'example_anchor': kp.example_anchor
        }

        # 生成自然语言讲解
        explanation = self.socratic_guide.generate_explanation(
            term=term,
            definition=definition,
            anchors=self.socratic_session.anchors
        )

        source_note = f"\n\n📚 信息来源: {source}" if source else ""

        return f"""{explanation}{source_note}

---

请选择：
  1. 有问题想问
  2. 继续学习其他
  3. 帮我总结一下

(输入 1/2/3 选择，或直接输入你的问题)"""

    def _handle_dimension_selection(self, selection: str) -> str:
        """
        处理维度选择（文本输入 fallback）

        Args:
            selection: 用户选择（序号）
        """
        if selection.lower() in ["取消", "cancel", "q"]:
            return self._cancel_theme_learning()

        dimensions = self._pending_dimensions

        try:
            idx = int(selection) - 1
            if idx < 0 or idx >= len(dimensions):
                return f"无效的选择，请输入1-{len(dimensions)}之间的序号"
        except ValueError:
            return f"无效输入，请输入序号"

        return self._do_select_dimension(idx)

    def _do_select_dimension(self, idx: int) -> List[str]:
        """
        执行维度选择

        Args:
            idx: 维度索引（0-based）

        Returns:
            知识点列表，或错误消息
        """
        theme = self._pending_theme
        dimensions = self._pending_dimensions

        if idx < 0 or idx >= len(dimensions):
            return [f"无效的维度索引: {idx}"]

        dimension = dimensions[idx]
        self._pending_dimension = dimension

        logger.info(f"Selected dimension: {dimension}")

        # 获取该维度的知识点
        session = self.short_memory.get_current_session()
        decomposer = session.get_theme_decomposer()
        kpoints = decomposer.get_dimension_kpoints(dimension, theme)

        if not kpoints:
            kpoints = [dimension]

        self._pending_kpoints = kpoints
        self.state = DialogueState.SELECTING_KPOINT

        return kpoints

    def select_dimension(self, idx: int) -> List[str]:
        """
        选择维度（供 CLI 调用）

        Args:
            idx: 维度索引（0-based）

        Returns:
            知识点列表
        """
        return self._do_select_dimension(idx)

    def select_kpoint(self, idx: int) -> str:
        """
        选择知识点并启动学习

        Args:
            idx: 知识点索引

        Returns:
            学习开始信息
        """
        kpoints = self._pending_kpoints
        theme = self._pending_theme
        dimension = self._pending_dimension

        if idx < 0 or idx >= len(kpoints):
            return f"无效的知识点索引: {idx}"

        kp_name = kpoints[idx]
        logger.info(f"Starting learning for: {kp_name}")

        # 获取会话上下文
        session = self.short_memory.get_current_session()

        # 启动该知识点的学习
        return self._start_kpoint_learning(kp_name, theme, dimension, session)

    def _start_kpoint_learning(self, kp_name: str, theme: str, dimension: str, session) -> str:
        """
        启动知识点学习 - 讲解优先模式

        Args:
            kp_name: 知识点名称
            theme: 所属主题
            dimension: 所属维度
            session: 会话上下文
        """
        # 信息搜集
        from features import FetcherManager
        fetcher_manager = FetcherManager()
        term_info = fetcher_manager.fetch_and_enhance(kp_name)

        definition = term_info.structured_definition or term_info.definition if term_info else f"{theme} - {dimension}维度"
        source = term_info.source if term_info else ""
        source_url = term_info.url if term_info else ""

        # 三锚点构建
        anchor_builder = session.get_anchor_builder()
        kp = anchor_builder.build_knowledge_point(
            term_name=kp_name,
            definition=definition,
            source=source,
            source_url=source_url
        )

        # 存入知识库
        term_obj = Term(
            id=kp.id,
            name=kp.name,
            definition=kp.definition,
            summary=kp.semantic_anchor or "",
            source=source or "theme_decomposition",
            source_url=source_url or ""
        )
        self.knowledge_db.add_term(term_obj)

        # 加入复习计划
        from review import ReviewScheduler
        scheduler = ReviewScheduler()
        scheduler.add_term(term_obj.id, kp_name)

        # 记录到会话上下文
        session_kp = KnowledgePoint(
            id=kp.id,
            name=kp.name,
            definition=kp.definition,
            topic_anchor=kp.topic_anchor,
            dependency_anchors=kp.dependency_anchors,
            semantic_anchor=kp.semantic_anchor,
            contrast_anchor=kp.contrast_anchor,
            example_anchor=kp.example_anchor,
            source=kp.source,
            source_url=kp.source_url
        )
        session.add_learned_knowledge_point(session_kp)

        # 添加到已学习
        self.long_memory.add_learned_term(kp_name)

        # 记录统计
        from features import StatisticsCollector
        stats = StatisticsCollector()
        stats.record_new_term()

        # 启动讲解模式会话
        self.state = DialogueState.EXPLAINING
        self.socratic_session = self.socratic_guide.start_session(kp_name, definition)

        logger.info(f"[LEARN] 开始学习知识点: {kp_name}, 状态: EXPLAINING")

        # 存储锚点供后续使用
        self.socratic_session.anchors = {
            'topic_anchor': kp.topic_anchor,
            'dependency_anchors': kp.dependency_anchors,
            'semantic_anchor': kp.semantic_anchor,
            'contrast_anchor': kp.contrast_anchor,
            'example_anchor': kp.example_anchor
        }

        # 生成自然语言讲解
        logger.debug(f"[LEARN] 调用 generate_explanation, term={kp_name}")
        explanation = self.socratic_guide.generate_explanation(
            term=kp_name,
            definition=definition,
            anchors=self.socratic_session.anchors
        )
        logger.info(f"[LEARN] 讲解生成完成, 长度={len(explanation)}")

        source_note = f"\n\n📚 信息来源: {source}" if source else ""

        return f"""{explanation}{source_note}

---

请选择：
  1. 有问题想问
  2. 继续学习其他
  3. 帮我总结一下

(输入 1/2/3 选择，或直接输入你的问题)"""

    def _handle_kpoint_selection(self, selection: str) -> str:
        """
        处理知识点选择（文本输入 fallback）

        Args:
            selection: 用户选择
        """
        if selection.lower() in ["取消", "cancel", "q"]:
            return self._cancel_kpoint_selection()

        kpoints = self._pending_kpoints

        try:
            idx = int(selection) - 1
            if idx < 0 or idx >= len(kpoints):
                return f"无效的选择，请输入1-{len(kpoints)}之间的序号"
        except ValueError:
            return f"无效输入，请输入序号"

        return self._do_select_kpoint(idx)

    def _do_select_kpoint(self, idx: int) -> str:
        """
        执行知识点选择并启动学习

        Args:
            idx: 知识点索引（0-based）
        """
        kpoints = self._pending_kpoints
        theme = self._pending_theme
        dimension = self._pending_dimension

        if idx < 0 or idx >= len(kpoints):
            return f"无效的知识点索引: {idx}"

        kp_name = kpoints[idx]
        logger.info(f"Starting learning for: {kp_name}")

        # 获取会话上下文
        session = self.short_memory.get_current_session()

        # 启动该知识点的学习
        return self._start_kpoint_learning(kp_name, theme, dimension, session)

    def _cancel_theme_learning(self) -> str:
        """取消主题学习"""
        self.state = DialogueState.IDLE
        self._pending_theme = None
        self._pending_dimensions = []
        self._pending_dimension = None
        self._pending_kpoints = []
        return "已取消主题学习。"

    def _cancel_kpoint_selection(self) -> str:
        """取消知识点选择，返回维度选择"""
        self.state = DialogueState.DECOMPOSING
        self._pending_dimension = None
        self._pending_kpoints = []
        dimensions = self._pending_dimensions
        dim_list = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(dimensions))
        return f"""📚 主题: {self._pending_theme}

请选择要学习的维度：

{dim_list}

(输入序号选择，或输入'取消'退出主题学习)"""

    def _format_knowledge_point(self, kp) -> str:
        """格式化知识点展示"""
        lines = [f"📖 开始学习: {kp.name}"]

        if kp.topic_anchor:
            lines.append(f"\n🎯 主题锚点: {kp.topic_anchor}")

        if kp.dependency_anchors:
            deps = ", ".join(kp.dependency_anchors)
            lines.append(f"\n📚 依赖锚点: {deps}")

        if kp.semantic_anchor:
            lines.append(f"\n💡 语义锚点: {kp.semantic_anchor}")

        if kp.contrast_anchor:
            lines.append(f"\n⚖️ 对比锚点: {kp.contrast_anchor}")

        if kp.example_anchor:
            lines.append(f"\n🧪 举例锚点: {kp.example_anchor}")

        return "\n".join(lines)

    # 供 CLI 调用的辅助方法

    def needs_dimension_selection(self) -> bool:
        """检查是否需要维度选择"""
        return self.state == DialogueState.DECOMPOSING and self._pending_dimensions

    def needs_kpoint_selection(self) -> bool:
        """检查是否需要知识点选择"""
        return self.state == DialogueState.SELECTING_KPOINT and self._pending_kpoints

    def get_pending_dimensions(self) -> List[str]:
        """获取待选择的维度列表"""
        return self._pending_dimensions

    def get_pending_theme(self) -> Optional[str]:
        """获取待学习的主题"""
        return self._pending_theme

    def get_pending_dimension(self) -> Optional[str]:
        """获取当前选择的维度"""
        return self._pending_dimension

    def get_pending_kpoints(self) -> List[str]:
        """获取待选择的知识点列表"""
        return self._pending_kpoints

    def select_dimension(self, index: int) -> List[str]:
        """
        选择维度并获取知识点列表（供 CLI 选择器调用）

        Args:
            index: 维度索引（0-based）

        Returns:
            知识点列表，或错误消息
        """
        if not self._pending_dimensions or index < 0 or index >= len(self._pending_dimensions):
            return [f"无效的维度索引: {index}"]

        return self._handle_dimension_selection(str(index + 1))

    def select_kpoint(self, index: int) -> str:
        """
        选择知识点并启动学习（供 CLI 选择器调用）

        Args:
            index: 知识点索引（0-based）

        Returns:
            学习开始信息
        """
        if index < 0 or index >= len(self._pending_kpoints):
            return f"无效的知识点索引: {index}"
        return self._handle_kpoint_selection(str(index + 1))

    def handle_continue_choice(self, choice: str) -> str:
        """
        处理继续/结束选择

        Args:
            choice: 用户选择 (1=继续该维度, 2=其他维度, 3=结束)

        Returns:
            响应信息
        """
        if choice == "1":
            # 继续该维度的其他知识点
            return self._show_kpoint_selector()
        elif choice == "2":
            # 返回维度选择
            self.state = DialogueState.DECOMPOSING
            self._pending_dimension = None
            self._pending_kpoints = []
            return self._show_dimension_selector_text()
        elif choice == "3":
            # 结束主题学习
            return self._end_theme_learning()
        else:
            return "无效选择，请输入 1/2/3"

    def _end_theme_learning(self) -> str:
        """结束主题学习"""
        theme = self._pending_theme
        self.state = DialogueState.IDLE
        self._pending_theme = None
        self._pending_dimensions = []
        self._pending_dimension = None
        self._pending_kpoints = []
        return f"""✅ 主题学习结束！

📚 {theme}

已返回主界面。输入 /list 查看所有已学内容。"""

    def select_all_dimensions(self) -> str:
        """选择所有维度"""
        return self._handle_dimension_selection("全部")

    def _handle_socratic_response(self, user_input: str) -> str:
        """处理苏格拉底引导中的用户响应"""
        # 检查退出
        if user_input.lower() in ["退出", "exit", "quit", "q"]:
            return self._handle_learning_exit()

        # 检查是否要跳过
        if user_input.lower() in ["跳过", "skip", "继续", "next"]:
            if self.socratic_guide.should_continue(self.socratic_session):
                next_q = self.socratic_guide.get_next_question(self.socratic_session, "跳过")
                return f"\n{next_q}\n(输入您的回答继续，或输入'退出'结束学习)"
            else:
                return self._complete_kpoint_learning()

        # 获取下一个问题
        if self.socratic_guide.should_continue(self.socratic_session):
            next_question = self.socratic_guide.get_next_question(self.socratic_session, user_input)
            return f"\n{next_question}\n\n(输入您的回答继续，或输入'退出'结束学习)"
        else:
            # 完成当前知识点学习，询问是否继续
            return self._complete_kpoint_learning()

    def _handle_learning_exit(self) -> str:
        """处理学习退出"""
        summary = self.socratic_guide.complete_session(self.socratic_session)
        self.socratic_session = None

        # 检查是否在主题学习流程中
        if self._pending_kpoints:
            # 返回知识点选择
            return self._show_kpoint_selector()
        elif self._pending_dimensions:
            # 返回维度选择
            self.state = DialogueState.DECOMPOSING
            return self._show_dimension_selector_text()
        else:
            # 完全结束
            self.state = DialogueState.IDLE
            return f"{summary}\n\n已退出学习。"

    def _complete_kpoint_learning(self) -> str:
        """完成知识点学习，询问是否继续"""
        summary = self.socratic_guide.generate_ai_summary(self.socratic_session)
        self.socratic_session = None

        # 检查是否在主题学习流程中
        if self._pending_kpoints:
            # 返回知识点选择或结束
            return self._ask_continue_or_end(summary)
        else:
            # 独立概念学习，完全结束
            self.state = DialogueState.IDLE
            return f"{summary}\n\n知识点学习完成！"

    def _ask_continue_or_end(self, summary: str) -> str:
        """询问继续还是结束"""
        return f"""{summary}

✅ 该知识点学习完成！

请选择：
  1. 继续学习该维度的其他知识点
  2. 学习其他维度
  3. 结束主题学习

(输入 1/2/3 选择，或输入其他内容作为新命令)"""

    def _show_kpoint_selector(self) -> str:
        """显示知识点选择器"""
        kpoints = self._pending_kpoints
        theme = self._pending_theme
        dimension = self._pending_dimension

        kp_list = "\n".join(f"  {i+1}. {k}" for i, k in enumerate(kpoints))

        return f"""📚 主题: {theme} > {dimension}

该维度下有以下知识点，请选择：

{kp_list}

  0. 其他（输入其他需求或命令）

(输入序号选择)"""

    def _show_dimension_selector_text(self) -> str:
        """显示维度选择器（文本模式）"""
        theme = self._pending_theme
        dimensions = self._pending_dimensions

        dim_list = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(dimensions))

        return f"""📚 主题: {theme}

请选择要学习的维度：

{dim_list}

  0. 其他（输入其他需求或命令）

(输入序号选择)"""

    def _handle_ask(self, question: str) -> str:
        """处理问答"""
        self.state = DialogueState.ASKING

        # 简单回答：搜索知识库
        results = self.knowledge_db.search_terms(question, limit=3)
        if results:
            answer = f"根据知识库，我找到以下相关内容：\n\n"
            for r in results:
                answer += f"**{r.name}**\n{r.definition}\n\n"
            return answer

        return f"知识库中没有找到关于'{question}'的信息。您可以先学习这个概念。"

    def _handle_tag(self, action: Optional[str], params: Dict) -> str:
        """处理标签操作"""
        from knowledge import Tag

        if action == "list":
            tags = self.knowledge_db.list_tags()
            if not tags:
                return "暂无标签"
            return "标签列表:\n" + "\n".join(f"- {t.name}" for t in tags)

        elif action == "add":
            term_name = params.get('term')
            tag_name = params.get('tag')
            if not term_name or not tag_name:
                return "用法: /tag add <名词> <标签>"

            term = self.knowledge_db.get_term_by_name(term_name)
            if not term:
                return f"名词'{term_name}'不存在"

            tag = self.knowledge_db.get_tag_by_name(tag_name)
            if not tag:
                tag = Tag(id="", name=tag_name)
                self.knowledge_db.add_tag(tag)

            self.knowledge_db.add_term_tag(term.id, tag.id)
            return f"已为'{term_name}'添加标签'{tag_name}'"

        elif action == "create":
            tag_name = params.get('name')
            if not tag_name:
                return "用法: /tag create <标签名>"

            # 检查是否已存在
            existing = self.knowledge_db.get_tag_by_name(tag_name)
            if existing:
                return f"标签'{tag_name}'已存在"

            tag = Tag(id="", name=tag_name)
            self.knowledge_db.add_tag(tag)
            return f"标签'{tag_name}'创建成功"

        return "未知标签操作"

    def _handle_context(self, action: Optional[str], params: Dict) -> str:
        """处理语境设置"""
        if action == "show":
            ctx = self.short_memory.get_context()
            return f"当前语境: {ctx or '无'}"

        elif action == "clear":
            self.short_memory.set_context("")
            return "语境已清除"

        elif action == "set":
            # 简化实现
            return "语境设置功能开发中"

        return "未知语境操作"

    def _handle_list(self, entity: Optional[str], params: Dict) -> str:
        """处理列表请求"""
        terms = self.knowledge_db.list_terms(limit=50)
        if not terms:
            return "暂无已学名词"

        return "已学名词:\n" + "\n".join(f"- {t.name}" for t in terms)

    def _handle_view(self, term: Optional[str]) -> str:
        """处理查看请求"""
        if not term:
            return "用法: /view <名词>"

        term_obj = self.knowledge_db.get_term_by_name(term)
        if not term_obj:
            return f"名词'{term}'不存在"

        return f"=== {term_obj.name} ===\n\n{term_obj.definition}"

    def _handle_review(self, action: Optional[str], params: Dict) -> str:
        """处理复习请求"""
        from review import ReviewScheduler

        scheduler = ReviewScheduler()

        if action == "today":
            due = scheduler.get_due_reviews()
            if not due:
                return "今天没有需要复习的内容"
            return "今日复习:\n" + "\n".join(f"- {item.term_name}" for item in due)

        elif action == "random":
            count = params.get('count', 5)
            return f"随机复习功能开发中 (数量: {count})"

        return "复习功能开发中"

    def _handle_stats(self, period: Optional[str]) -> str:
        """处理统计请求"""
        from features import StatisticsCollector

        collector = StatisticsCollector()

        if period in ["today", "week", "month", None]:
            stats = collector.get_today_stats() if period == "today" else collector.get_stats(30)
            return collector.format_report(stats)

        return "统计功能开发中"

    def _handle_mindmap(self, term: Optional[str], format: Optional[str]) -> str:
        """处理思维导图请求"""
        if not term:
            return "用法: /mindmap <名词>"

        if format == "mermaid":
            from features import MindmapGenerator
            gen = MindmapGenerator()
            return gen.generate_mermaid(term)

        return f"思维导图: {term}\n(使用 /mindmap {term} mermaid 查看)"

    def _handle_path(self, action: Optional[str], params: Dict) -> str:
        """处理学习路径"""
        if action == "list":
            from features import PathManager
            pm = PathManager()
            paths = pm.list_paths()
            if not paths:
                return "暂无学习路径"
            return "学习路径:\n" + "\n".join(f"- {p.name}" for p in paths)

        elif action == "recommend":
            term = params.get('term')
            if term:
                from features import PathManager
                pm = PathManager()
                known = self.long_memory.get_learned_terms()
                rec = pm.generate_recommend(term, known)
                return f"推荐: {rec['name']}\n{rec.get('description', '')}"

        return "学习路径功能开发中"

    def _handle_reminder(self, action: Optional[str], params: Dict) -> str:
        """处理提醒"""
        from features import ReminderManager

        manager = ReminderManager()

        if action == "list":
            reminders = manager.get_reminders()
            if not reminders:
                return "暂无提醒"
            return "提醒列表:\n" + "\n".join(f"- {r.message} ({r.time})" for r in reminders)

        elif action == "add":
            return "用法: /reminder add 复习"

        return "提醒功能开发中"

    def _handle_help(self, topic: Optional[str]) -> str:
        """处理帮助请求"""
        help_text = {
            None: """
LearnMate 帮助

核心命令:
  /learn <名词>     学习新名词
  /view <名词>     查看名词详情
  /list            列出已学名词
  /tag add <名词> <标签>  添加标签
  /review          复习到期名词
  /stats           查看学习统计
  /mindmap <名词>  查看思维导图
  /path list       查看学习路径
  /help <主题>     查看特定帮助
            """,
            "learn": "学习命令帮助: /learn <名词> 或直接输入名词",
            "tag": "标签命令: /tag list/add/create",
        }

        return help_text.get(topic, help_text[None])

    def _handle_mode(self, mode: Optional[str]) -> str:
        """处理模式切换"""
        if mode:
            self.short_memory.set_mode(mode)
            self.current_mode = mode
            return f"已切换到 {mode} 模式"
        return "用法: /mode <learn/qa/review>"

    def _handle_sessions(self, action: Optional[str]) -> str:
        """处理会话历史"""
        if action == "view":
            return "用法: /sessions view <session_id>"

        sessions = self.short_memory.list_sessions()
        if not sessions:
            return "暂无会话历史"

        lines = ["会话历史:"]
        for i, s in enumerate(sessions[:10], 1):
            ctx = s.get('context', '')
            ctx_preview = ctx[:30] + "..." if len(ctx) > 30 else ctx or "(无语境)"
            lines.append(
                f"{i}. [{s['mode']}] {s['created_at'][:19]} | "
                f"{s['message_count']}条消息 | {ctx_preview}"
            )

        lines.append("\n输入 /sessions view <id> 查看详情")
        return "\n".join(lines)

    def _handle_unknown(self, user_input: str) -> str:
        """处理未知输入"""
        return f"无法理解: {user_input}\n输入 /help 查看可用命令"

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self.short_memory.get_conversation_history()

    # ============================================================
    # 新方法：讲解优先模式
    # ============================================================

    def _is_question(self, text: str) -> bool:
        """简单判断输入是否为问题"""
        if not text:
            return False
        text = text.strip()
        # 问题标记
        question_markers = ['?', '？', '什么', '怎么', '为什么', '是不是', '有没有', '如何', '哪']
        return any(marker in text for marker in question_markers)

    def _handle_explaining_response(self, user_input: str) -> str:
        """
        处理讲解阶段的用户回应

        用户可以选择：
        1. 有问题想问 -> 进入问答模式
        2. 继续学习其他 -> 结束当前学习
        3. 帮我总结 -> 生成总结
        或者直接输入问题
        """
        user_input = user_input.strip()
        term = self.socratic_session.term if self.socratic_session else "unknown"

        logger.info(f"[EXPLAINING] 用户输入: {user_input[:50]}..., term={term}")

        # 如果是退出命令
        if user_input.lower() in ['退出', 'exit', 'quit', 'q']:
            logger.info(f"[EXPLAINING] 用户退出, term={term}")
            return self._handle_learning_exit()

        # 如果用户输入问题，进入问答模式
        if self._is_question(user_input):
            logger.info(f"[EXPLAINING] 检测到问题，进入 Q&A, term={term}")
            return self._answer_user_question(user_input)

        # 处理菜单选择
        if user_input == "1":
            # 用户选择问问题 -> 先要求解释，然后进入问答
            logger.info(f"[EXPLAINING] 用户选择菜单1（问问题）, term={term}")
            return "好的，请先用自己的话解释一下这个概念，然后我再回答你的问题："

        if user_input == "2":
            # 继续学习其他
            logger.info(f"[EXPLAINING] 用户选择菜单2（继续学习）, term={term}")
            return self._finalize_learning_and_prompt_next()

        if user_input == "3":
            # 总结
            logger.info(f"[EXPLAINING] 用户选择菜单3（总结）, term={term}, 状态 -> SUMMARIZING")
            self.state = DialogueState.SUMMARIZING
            return self._generate_structured_summary()

        # 用户输入了解释，评估理解程度
        logger.info(f"[EXPLAINING] 评估理解程度, term={term}")
        level, feedback = self.socratic_guide.judge_comprehension(
            term=self.socratic_session.term,
            definition=self.socratic_session.definition,
            user_explanation=user_input,
            message_history=self.socratic_session.message_history
        )
        logger.info(f"[EXPLAINING] 理解程度: level={level}, feedback={feedback[:50]}...")

        # 如果反馈说"无需指出"，说明理解正确
        if "无需指出" in feedback:
            # 理解充分，进入用户主导循环
            self.state = DialogueState.Q_A_LOOP
            logger.info(f"[EXPLAINING] 理解充分, 状态 -> Q_A_LOOP, term={term}")
            return self._ask_if_more_questions()
        elif level >= 0.7:
            # 理解充分，进入用户主导循环
            self.state = DialogueState.Q_A_LOOP
            logger.info(f"[EXPLAINING] 理解充分(level={level}), 状态 -> Q_A_LOOP, term={term}")
            return self._ask_if_more_questions()
            return self._ask_if_more_questions()
        else:
            # 理解不充分，提供针对性补充讲解
            return self._provide_remediation(user_input, level, feedback)

    def _answer_user_question(self, question: str) -> str:
        """回答用户的具体问题 - 维护消息历史"""
        anchors = self.socratic_session.anchors or {}
        term = self.socratic_session.term

        logger.info(f"[Q&A] 用户提问, term={term}, question={question[:50]}...")
        logger.debug(f"[Q&A] 当前消息历史长度: {len(self.socratic_session.message_history)}")

        # 添加用户问题到消息历史
        self.socratic_session.message_history.append(user_message(question))

        logger.info(f"[Q&A] 调用 answer_question LLM, term={term}")
        answer = self.socratic_guide.answer_question(
            term=self.socratic_session.term,
            anchors=anchors,
            question=question,
            message_history=self.socratic_session.message_history
        )
        logger.info(f"[Q&A] LLM回答完成, 长度={len(answer)}, term={term}")

        # 添加 AI 回答到消息历史
        self.socratic_session.message_history.append(assistant_message(answer))

        # 记录到 QA 历史（兼容）
        self.socratic_session.qa_history.append({
            'question': question,
            'answer': answer
        })

        logger.info(f"[Q&A] 消息历史更新后长度: {len(self.socratic_session.message_history)}, qa_history长度: {len(self.socratic_session.qa_history)}")

        return f"""{answer}

还有其他问题吗？
  1. 有，继续问
  2. 没有了
  3. 帮我总结
"""

    def _ask_if_more_questions(self) -> str:
        """询问用户是否还有问题"""
        term = self.socratic_session.term

        return f"""很好！我来确认一下：

关于"{term}"，你已经对这个概念有了基本理解。

请选择：
  1. 有，我想深入了解某个方面（请输入你的问题）
  2. 没有了，继续学习其他
  3. 帮我总结一下

(输入 1/2/3 选择，或直接输入你的问题)
"""

    def _handle_qa_loop(self, user_input: str) -> str:
        """用户主导的问答循环"""
        user_input = user_input.strip()
        term = self.socratic_session.term if self.socratic_session else "unknown"

        logger.info(f"[Q_A_LOOP] 用户输入: {user_input[:50]}..., term={term}")

        # 如果是退出命令
        if user_input.lower() in ['退出', 'exit', 'quit', 'q']:
            logger.info(f"[Q_A_LOOP] 用户退出, term={term}")
            return self._handle_learning_exit()

        # 检查选择
        if user_input == "2":
            # 用户选择结束当前知识点
            logger.info(f"[Q_A_LOOP] 用户选择菜单2（结束学习）, term={term}")
            return self._finalize_learning_and_prompt_next()

        if user_input == "3":
            # 用户要求总结
            logger.info(f"[Q_A_LOOP] 用户选择菜单3（总结）, term={term}, 状态 -> SUMMARIZING")
            self.state = DialogueState.SUMMARIZING
            return self._generate_structured_summary()

        if user_input == "1":
            logger.info(f"[Q_A_LOOP] 用户选择菜单1（继续问）, term={term}")
            return "请输入你想深入了解的问题："

        # 用户输入了具体问题
        if self._is_question(user_input):
            logger.info(f"[Q_A_LOOP] 检测到问题，进入回答, term={term}")
            return self._answer_user_question(user_input)

        # 其他输入当作问题处理
        logger.info(f"[Q_A_LOOP] 其他输入当问题处理, term={term}")
        return self._answer_user_question(user_input)

    def _provide_remediation(self, user_input: str, level: float, feedback: str) -> str:
        """提供针对性补充讲解 - 维护消息历史"""
        term = self.socratic_session.term
        anchors = self.socratic_session.anchors or {}

        logger.info(f"[REMEDIATION] 提供补充讲解, term={term}, level={level}")

        # 添加用户输入到消息历史
        self.socratic_session.message_history.append(user_message(
            f"请详细解释一下我对{term}的理解中哪些地方有问题：{user_input}"
        ))

        logger.info(f"[REMEDIATION] 调用 answer_question LLM, term={term}")
        # 基于用户输入中的困惑点，提供补充讲解
        remediation = self.socratic_guide.answer_question(
            term=term,
            anchors=anchors,
            question=f"请详细解释一下我对{term}的理解中哪些地方有问题：{user_input}",
            message_history=self.socratic_session.message_history
        )
        logger.info(f"[REMEDIATION] LLM回答完成, 长度={len(remediation)}, term={term}")

        # 添加 AI 回答到消息历史
        self.socratic_session.message_history.append(assistant_message(remediation))

        return f"""{feedback}

让我针对你的理解进行补充说明：

{remediation}

---

请选择：
  1. 有问题想问
  2. 继续学习其他
  3. 帮我总结一下

(输入 1/2/3 选择，或直接输入你的问题)
"""

    def _generate_structured_summary(self) -> str:
        """生成结构化总结"""
        term = self.socratic_session.term
        anchors = self.socratic_session.anchors or {}
        qa_history = self.socratic_session.qa_history

        logger.info(f"[SUMMARY] 开始生成总结, term={term}, qa_history长度={len(qa_history)}, 消息历史长度={len(self.socratic_session.message_history)}")

        summary = self.socratic_guide.generate_structured_summary(
            term=term,
            anchors=anchors,
            qa_history=qa_history,
            message_history=self.socratic_session.message_history
        )

        logger.info(f"[SUMMARY] 总结生成完成, 长度={len(summary)}, term={term}")

        return f"""{summary}

---

知识点学习完成！以上内容已保存到知识库。"""

    def _finalize_learning_and_prompt_next(self) -> str:
        """完成当前知识点学习，更新锚点，提示下一步"""
        term = self.socratic_session.term

        logger.info(f"[FINALIZE] 学习完成, term={term}")
        logger.info(f"[FINALIZE] qa_history长度={len(self.socratic_session.qa_history)}, 消息历史长度={len(self.socratic_session.message_history)}")

        # 更新知识库的锚点（基于用户问答历史补充）
        self._enrich_anchors_from_qa_history()
        logger.info(f"[FINALIZE] 锚点更新完成, term={term}")

        # 重置状态
        self.socratic_session = None
        self.state = DialogueState.IDLE
        logger.info(f"[FINALIZE] 状态重置为 IDLE")

        return f"""✅ "{term}" 学习完成！

已保存到您的知识库。

输入 /list 查看已学内容，或直接输入其他概念继续学习。"""

    def _enrich_anchors_from_qa_history(self):
        """基于用户问答历史补充锚点"""
        if not self.socratic_session or not self.socratic_session.qa_history:
            return

        # 这里可以添加基于 QA 历史更新锚点的逻辑
        # 例如：如果用户问了很多关于对比的问题，可以更新 contrast_anchor
        # 目前是简化实现，暂不修改锚点
        pass

    def _handle_summarizing(self, user_input: str) -> str:
        """处理总结阶段的用户回应"""
        user_input = user_input.strip()

        # 如果是确认总结
        if user_input.lower() in ['确认', 'yes', 'y', '是']:
            return self._finalize_learning_and_prompt_next()

        # 如果是重新总结
        if user_input.lower() in ['重新总结', 'regenerate']:
            return self._generate_structured_summary()

        # 如果是退出
        if user_input.lower() in ['退出', 'exit', 'quit', 'q']:
            return self._handle_learning_exit()

        # 其他输入当作其他命令处理
        return self._finalize_learning_and_prompt_next()

    def _handle_learning_exit(self) -> str:
        """处理学习退出"""
        # 如果在主题学习流程中
        if self._pending_kpoints:
            self.state = DialogueState.SELECTING_KPOINT
            return self._show_kpoint_selector()
        elif self._pending_dimensions:
            self.state = DialogueState.DECOMPOSING
            return self._show_dimension_selector_text()
        else:
            # 完全结束
            self.socratic_session = None
            self.state = DialogueState.IDLE
            return "已退出学习。"

    def _show_kpoint_selector(self) -> str:
        """显示知识点选择器"""
        kpoints = self._pending_kpoints
        theme = self._pending_theme
        dimension = self._pending_dimension

        kp_list = "\n".join(f"  {i+1}. {k}" for i, k in enumerate(kpoints))

        return f"""📚 主题: {theme} > {dimension}

该维度下有以下知识点，请选择：

{kp_list}

  0. 其他（输入其他需求或命令）

(输入序号选择)"""

    def _show_dimension_selector_text(self) -> str:
        """显示维度选择器（文本模式）"""
        theme = self._pending_theme
        dimensions = self._pending_dimensions

        dim_list = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(dimensions))

        return f"""📚 主题: {theme}

请选择要学习的维度：

{dim_list}

  0. 其他（输入其他需求或命令）

(输入序号选择)"""
