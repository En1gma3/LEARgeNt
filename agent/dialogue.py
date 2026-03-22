"""
对话管理器

管理对话流程和状态
"""

from typing import Optional, Dict, Any, List
from enum import Enum

from memory import ShortTermMemory, LongTermMemory
from knowledge import KnowledgeDB
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
        return "欢迎使用 LearnMate！请输入要学习的内容。"

    def handle_input(self, user_input: str) -> str:
        """处理用户输入"""
        logger.debug(f"handle_input called with: {user_input[:50]}...")

        # 检查是否在苏格拉底引导模式
        if self.state == DialogueState.GUIDING and self.socratic_session:
            logger.debug("Currently in GUIDING state, delegating to socratic handler")
            return self._handle_socratic_response(user_input)

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

        self.current_term = term

        # 检查是否已学习
        if self.long_memory.is_learned(term):
            # 已学习，可以查看或复习
            return f"您已经学习过'{term}'了。输入/view {term}查看详情，或/review开始复习。"

        # 添加到已学习
        self.long_memory.add_learned_term(term)

        # 尝试从 Wikipedia 获取术语信息并使用 LLM 结构化
        from features import FetcherManager
        fetcher_manager = FetcherManager()
        term_info = fetcher_manager.fetch_and_enhance(term)

        # 存入知识库
        from knowledge import Term
        if term_info:
            term_obj = Term(
                id="",
                name=term,
                definition=term_info.structured_definition or term_info.definition,
                summary=term_info.summary,
                source=term_info.source
            )
            source_note = f"\n\n📚 信息来源: {term_info.source}"
        else:
            term_obj = Term(id="", name=term, definition=f"学习: {term}")
            source_note = ""

        self.knowledge_db.add_term(term_obj)

        # 加入复习计划
        from review import ReviewScheduler
        scheduler = ReviewScheduler()
        scheduler.add_term(term_obj.id, term)

        # 记录统计
        from features import StatisticsCollector
        stats = StatisticsCollector()
        stats.record_new_term()

        # 启动苏格拉底会话
        self.state = DialogueState.GUIDING
        self.socratic_session = self.socratic_guide.start_session(term, term_obj.definition)

        # 获取第一个问题
        first_question = self.socratic_guide.get_first_question(self.socratic_session)

        return f"""🤔 开始学习: {term}{source_note}

{first_question}

(输入您的回答继续，或输入'退出'结束学习)"""

    def _handle_socratic_response(self, user_input: str) -> str:
        """处理苏格拉底引导中的用户响应"""
        # 检查退出
        if user_input.lower() in ["退出", "exit", "quit", "q"]:
            # 结束会话
            summary = self.socratic_guide.complete_session(self.socratic_session)
            self.socratic_session = None
            self.state = DialogueState.IDLE
            return summary

        # 检查是否要跳过或继续
        if user_input.lower() in ["跳过", "skip", "继续", "next"]:
            if self.socratic_guide.should_continue(self.socratic_session):
                next_q = self.socratic_guide.get_next_question(self.socratic_session, "跳过")
                return f"\n{next_q}\n(输入您的回答继续，或输入'退出'结束学习)"
            else:
                summary = self.socratic_guide.complete_session(self.socratic_session)
                self.socratic_session = None
                self.state = DialogueState.IDLE
                return summary

        # 获取下一个问题
        if self.socratic_guide.should_continue(self.socratic_session):
            next_question = self.socratic_guide.get_next_question(self.socratic_session, user_input)
            return f"\n{next_question}\n\n(输入您的回答继续，或输入'退出'结束学习)"
        else:
            # 完成学习
            summary = self.socratic_guide.generate_ai_summary(self.socratic_session)
            self.socratic_session = None
            self.state = DialogueState.IDLE
            return summary

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
