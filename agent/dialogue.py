"""
对话管理器

管理对话流程和状态
"""

from typing import Optional, Dict, Any, List
from enum import Enum

from memory import ShortTermMemory, LongTermMemory, KnowledgePoint
from knowledge import KnowledgeDB
from knowledge.models import Term
from utils import get_logger

logger = get_logger(__name__)


class DialogueState(Enum):
    """对话状态"""
    IDLE = "idle"                 # 空闲
    LEARNING = "learning"          # 学习中
    ASKING = "asking"             # 问答中
    REVIEWING = "reviewing"       # 复习中
    GUIDING = "guiding"           # 引导中（苏格拉底模式）
    CONFIRMING = "confirming"      # 确认中
    DECOMPOSING = "decomposing"    # 主题拆解中（维度选择）
    SELECTING_KPOINT = "selecting_kpoint"  # 知识点选择


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
        处理具体概念学习

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

        # 格式化三锚点展示
        anchors_display = self._format_knowledge_point(kp)

        # 启动苏格拉底会话
        self.state = DialogueState.GUIDING
        self.socratic_session = self.socratic_guide.start_session(term, definition)

        # 获取第一个问题
        first_question = self.socratic_guide.get_first_question(self.socratic_session)

        source_note = f"\n\n📚 信息来源: {source}" if source else ""

        return f"""{anchors_display}

{first_question}

(输入您的回答继续，或输入'退出'结束学习)"""

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
        启动知识点学习

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

        # 格式化三锚点展示
        anchors_display = self._format_knowledge_point(kp)

        # 启动苏格拉底会话
        self.state = DialogueState.GUIDING
        self.socratic_session = self.socratic_guide.start_session(kp_name, definition)

        # 获取第一个问题
        first_question = self.socratic_guide.get_first_question(self.socratic_session)

        source_note = f"\n\n📚 信息来源: {source}" if source else ""

        return f"""{anchors_display}{source_note}

{first_question}

(输入您的回答继续，或输入'退出'结束学习)"""

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
