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
from agent.dialogue import DialogueManager


class InteractiveMode:
    """交互模式"""

    def __init__(self):
        self.predictor = InterestPredictor()
        self.socratic = SocraticGuide()
        self.dialogue = DialogueManager()
        self.learned_terms: List[str] = []

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
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n退出")
                return 0

            if not user_input:
                continue

            if user_input.lower() in ["/exit", "/quit", "exit", "quit", "退出"]:
                print("再见!")
                return 0

            # 使用对话管理器处理输入
            response = self.dialogue.handle_input(user_input)
            print(response)
            print()

            # 检查是否退出
            if response == "再见！":
                return 0

        return 0

    def learn_concept(self, concept: str) -> int:
        """学习指定概念"""
        response = self.dialogue.handle_input(f"/learn {concept}")
        print(response)
        return 0

    def _show_help(self):
        """显示帮助"""
        print("""
核心命令:
  /learn <概念>     - 学习指定概念或主题
  /view <概念>     - 查看概念详情
  /list             - 显示已学习内容
  /tag list         - 显示标签列表
  /tag add <名词> <标签> - 添加标签
  /review           - 复习到期内容
  /stats            - 查看学习统计
  /mindmap <概念>  - 查看思维导图
  /path list        - 查看学习路径
  /reminder list    - 查看提醒
  /context show     - 显示当前语境
  /mode <类型>      - 切换模式(learn/qa/review)
  /help             - 显示帮助
  /exit             - 退出

兴趣点学习:
  /learn paper <路径> - 从PDF论文提取术语学习
  /learn news <URL>  - 从新闻提取概念学习
  /learn company <公司名> - 了解公司相关知识
  /learn whatis <问题> - 什么是...问题
        """)


# 便捷函数
def start_interactive():
    """启动交互模式"""
    mode = InteractiveMode()
    return mode.run()
