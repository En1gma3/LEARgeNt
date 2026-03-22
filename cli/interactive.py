"""
交互模式
"""

import sys
from typing import Optional, List

from parser.factory import ParserFactory
from extractor.base import Term
from extractor.ranker import rank_terms
from interest_predictor import InterestPredictor
from interest_predictor.predictor import PredictionContext
from agent.socratic import SocraticGuide
from agent.dialogue import DialogueManager, DialogueState
from cli.selector import ArrowSelector
from utils import get_logger

logger = get_logger(__name__)


class InteractiveMode:
    """交互模式"""

    def __init__(self):
        logger.info("Initializing InteractiveMode")
        self.predictor = InterestPredictor()
        self.socratic = SocraticGuide()
        self.dialogue = DialogueManager()
        self.learned_terms: List[str] = []
        self._awaiting_continue_choice = False  # 等待用户选择继续/结束
        self._pending_summary = ""  # 保存学完后的总结
        logger.info("InteractiveMode initialized")

    def run(self) -> int:
        """运行交互模式"""
        # 初始化对话
        welcome = self.dialogue.start_session()

        print("=" * 50)
        print("LearnMate - 智能学习助手")
        print("=" * 50)
        print(welcome)
        print()
        self._show_help()
        print()

        while True:
            try:
                # 检查是否需要维度选择
                if self.dialogue.needs_dimension_selection():
                    theme = self.dialogue.get_pending_theme()
                    dimensions = self.dialogue.get_pending_dimensions()
                    response = self._show_dimension_selector(theme, dimensions)
                    self._awaiting_continue_choice = False

                # 检查是否需要知识点选择
                elif self.dialogue.needs_kpoint_selection():
                    theme = self.dialogue.get_pending_theme()
                    dimension = self.dialogue.get_pending_dimension()
                    kpoints = self.dialogue.get_pending_kpoints()
                    response = self._show_kpoint_selector(theme, dimension, kpoints)
                    self._awaiting_continue_choice = False

                # 检查是否在等待继续/结束选择
                elif self._awaiting_continue_choice:
                    response = self._handle_continue_choice(user_input)

                else:
                    user_input = input("> ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ["/exit", "/quit", "exit", "quit", "退出"]:
                        logger.info("User requested exit")
                        self._cleanup()
                        print("再见!")
                        return 0
                    # 使用对话管理器处理输入
                    logger.debug(f"Processing input: {user_input[:50]}...")
                    response = self.dialogue.handle_input(user_input)

                    # 检查是否进入继续/结束状态
                    if "继续学习该维度的其他知识点" in response:
                        self._awaiting_continue_choice = True
                        # 提取总结（如果有的话）
                        if "✅" in response:
                            parts = response.split("✅")
                            if len(parts) > 1:
                                self._pending_summary = parts[0].strip()

            except (EOFError, KeyboardInterrupt):
                logger.info("Received EOF/KeyboardInterrupt")
                self._cleanup()
                print("\n退出")
                return 0

            print(response)
            print()

            # 检查是否退出
            if response == "再见！":
                self._cleanup()
                return 0

        return 0

    def _show_dimension_selector(self, theme: str, dimensions: List[str]) -> str:
        """
        使用箭头选择器选择维度
        """
        print(f"\n{'='*50}")
        print(f"📚 主题: {theme}")
        print(f"{'='*50}")
        print("请选择要学习的维度（方向键导航，回车确认）：")
        print()

        # 添加"其他"选项
        all_items = dimensions + ["其他需求"]

        selector = ArrowSelector(
            items=all_items,
            title=None,
            multi_column=False
        )

        idx = selector.run()

        if idx is None:
            # 用户取消
            return self.dialogue._cancel_theme_learning()

        if idx == len(dimensions):
            # 选择了"其他需求"，清空状态让用户输入新命令
            self.dialogue.state = DialogueState.IDLE
            self.dialogue._pending_theme = None
            self.dialogue._pending_dimensions = []
            return "请输入其他需求或命令："

        # 选择维度，获取知识点
        result = self.dialogue.select_dimension(idx)

        if isinstance(result, list):
            # 返回知识点列表，等待下一步选择
            return result  # CLI 会检测 needs_kpoint_selection
        return result

    def _show_kpoint_selector(self, theme: str, dimension: str, kpoints: List[str]) -> str:
        """
        使用箭头选择器选择知识点
        """
        print(f"\n{'='*50}")
        print(f"📚 主题: {theme} > {dimension}")
        print(f"{'='*50}")
        print("请选择要学习的知识点（方向键导航，回车确认）：")
        print()

        # 添加"其他需求"选项
        all_items = kpoints + ["其他需求"]

        selector = ArrowSelector(
            items=all_items,
            title=None,
            multi_column=False
        )

        idx = selector.run()

        if idx is None:
            # 用户取消，返回维度选择
            return self.dialogue._cancel_kpoint_selection()

        if idx == len(kpoints):
            # 选择了"其他需求"
            self.dialogue.state = DialogueState.IDLE
            self.dialogue._pending_dimension = None
            self.dialogue._pending_kpoints = []
            return "请输入其他需求或命令："

        # 选择知识点，启动学习
        return self.dialogue.select_kpoint(idx)

    def _handle_continue_choice(self, choice: str) -> str:
        """处理继续/结束选择"""
        self._awaiting_continue_choice = False
        return self.dialogue.handle_continue_choice(choice)

    def _cleanup(self):
        """退出前清理 - 保存会话"""
        logger.info("Cleaning up before exit")
        # 保存当前会话
        self.dialogue.short_memory.save_session()
        logger.info("Session saved successfully")

    def learn_concept(self, concept: str) -> int:
        """学习指定概念"""
        response = self.dialogue.handle_input(f"/learn {concept}")
        print(response)
        return 0

    def _show_help(self):
        """显示帮助"""
        print("""
📚 常用命令：
   学习 <概念>      学习具体概念或主题
   /view <名词>     查看已学内容详情
   /list            列出所有已学内容
   /review          复习到期内容

🏷️ 标签管理：
   /tag list        查看标签列表
   /tag add <名词> <标签>  添加标签

📊 辅助功能：
   /stats           查看学习统计
   /mindmap <名词>  生成思维导图
   /sessions        查看会话历史

❓ 其他：
   /help            显示帮助
   /exit            退出

💡 提示：用方向键选择，回车确认，输入"其他需求"可随时输入其他命令
""")


# 便捷函数
def start_interactive():
    """启动交互模式"""
    mode = InteractiveMode()
    return mode.run()
