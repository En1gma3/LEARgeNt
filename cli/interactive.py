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


class InteractiveMode:
    """交互模式"""

    def __init__(self):
        self.predictor = InterestPredictor()
        self.socratic = SocraticGuide()
        self.learned_terms: List[str] = []

    def run(self) -> int:
        """运行交互模式"""
        print("=" * 50)
        print("LearnMate - 智能学习助手")
        print("=" * 50)
        print("输入命令:")
        print("  /learn <内容>   - 开始学习")
        print("  /learn paper <路径> - 学习PDF论文")
        print("  /learn news <URL>   - 学习新闻")
        print("  /learn company <公司名> - 学习公司")
        print("  /learn whatis <问题> - 什么是...")
        print("  /help          - 显示帮助")
        print("  /exit          - 退出")
        print("=" * 50)
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

            if user_input.startswith("/help"):
                self._show_help()
                continue

            if user_input.startswith("/learn"):
                self._handle_learn(user_input)
                continue

            if user_input.startswith("/list"):
                self._show_learned()
                continue

            # 其他输入当作概念学习
            self._handle_learn(f"/learn {user_input}")

        return 0

    def learn_concept(self, concept: str) -> int:
        """学习指定概念"""
        self._handle_learn(f"/learn {concept}")
        return 0

    def _show_help(self):
        """显示帮助"""
        print("""
可用命令:
  /learn <概念>     - 学习指定概念或主题
  /learn paper <路径> - 从PDF论文提取术语学习
  /learn news <URL>  - 从新闻提取概念学习
  /learn company <公司名> - 了解公司相关知识
  /learn whatis <问题> - 什么是...问题
  /list             - 显示已学习的内容
  /help             - 显示帮助
  /exit             - 退出
        """)

    def _show_learned(self):
        """显示已学习内容"""
        if not self.learned_terms:
            print("暂无已学习内容")
            return

        print("已学习内容:")
        for i, term in enumerate(self.learned_terms, 1):
            print(f"  {i}. {term}")

    def _handle_learn(self, user_input: str):
        """处理学习命令"""
        # 解析命令
        parts = user_input.split(None, 2)
        if len(parts) < 2:
            print("用法: /learn <内容>")
            return

        cmd = parts[1]
        content = parts[2] if len(parts) > 2 else ""

        # 根据命令类型选择解析器
        if cmd == "paper":
            self._learn_pdf(content)
        elif cmd == "news":
            self._learn_news(content)
        elif cmd == "company":
            self._learn_company(content)
        elif cmd == "industry":
            self._learn_industry(content)
        elif cmd == "whatis":
            self._learn_question(content)
        else:
            # 普通概念学习
            self._learn_concept(user_input[len("/learn "):].strip())

    def _learn_pdf(self, path: str):
        """学习PDF论文"""
        print(f"[解析PDF] {path}")
        parser = ParserFactory.create("pdf")
        try:
            content = parser.parse(path)
            print(f"解析成功，内容长度: {len(content)} 字符")

            # 提取术语
            from extractor import NLPExtractor
            extractor = NLPExtractor()
            terms = extractor.extract(content)
            terms = rank_terms(terms)
            print(f"提取到 {len(terms)} 个术语")

            # 兴趣推测
            context = PredictionContext(
                learned_terms=self.learned_terms,
                source_title=path,
                source_type="pdf"
            )
            top_terms = self.predictor.get_top_n(terms, context, n=5)

            print("\n推荐学习:")
            for i, term in enumerate(top_terms, 1):
                print(f"  {i}. {term.name}")

            # 启动苏格拉底引导
            self._start_socratic(top_terms[0] if top_terms else None)

        except Exception as e:
            print(f"解析失败: {e}")

    def _learn_news(self, url: str):
        """学习新闻"""
        print(f"[解析新闻] {url}")
        parser = ParserFactory.create("news")
        try:
            result = parser.parse(url)
            content = result.get("content", "")
            print(f"解析成功，内容长度: {len(content)} 字符")

            # 提取术语
            from extractor import NLPExtractor
            extractor = NLPExtractor()
            terms = extractor.extract(content)
            terms = rank_terms(terms)
            print(f"提取到 {len(terms)} 个术语")

            # 兴趣推测
            context = PredictionContext(
                learned_terms=self.learned_terms,
                source_title=result.get("title", ""),
                source_type="news"
            )
            top_terms = self.predictor.get_top_n(terms, context, n=5)

            print("\n推荐学习:")
            for i, term in enumerate(top_terms, 1):
                print(f"  {i}. {term.name}")

            self._start_socratic(top_terms[0] if top_terms else None)

        except Exception as e:
            print(f"解析失败: {e}")

    def _learn_company(self, name: str):
        """学习公司"""
        print(f"[解析公司] {name}")
        parser = ParserFactory.create("company")
        try:
            result = parser.parse(name)
            content = result.get("content", "")
            print(f"解析成功，内容长度: {len(content)} 字符")

            from extractor import NLPExtractor
            extractor = NLPExtractor()
            terms = extractor.extract(content)
            terms = rank_terms(terms)
            print(f"提取到 {len(terms)} 个术语")

            context = PredictionContext(
                learned_terms=self.learned_terms,
                source_title=name,
                source_type="company"
            )
            top_terms = self.predictor.get_top_n(terms, context, n=5)

            print("\n推荐学习:")
            for i, term in enumerate(top_terms, 1):
                print(f"  {i}. {term.name}")

            self._start_socratic(top_terms[0] if top_terms else None)

        except Exception as e:
            print(f"解析失败: {e}")

    def _learn_industry(self, name: str):
        """学习行业"""
        print(f"[解析行业] {name}")
        parser = ParserFactory.create("industry")
        try:
            result = parser.parse(name)
            content = result.get("content", "")

            from extractor import NLPExtractor
            extractor = NLPExtractor()
            terms = extractor.extract(content)
            terms = rank_terms(terms)

            context = PredictionContext(
                learned_terms=self.learned_terms,
                source_title=name,
                source_type="industry"
            )
            top_terms = self.predictor.get_top_n(terms, context, n=5)

            print("\n推荐学习:")
            for i, term in enumerate(top_terms, 1):
                print(f"  {i}. {term.name}")

            self._start_socratic(top_terms[0] if top_terms else None)

        except Exception as e:
            print(f"解析失败: {e}")

    def _learn_question(self, question: str):
        """学习问题"""
        print(f"[解析问题] {question}")
        parser = ParserFactory.create("question")
        try:
            result = parser.parse(question)
            terms = result.get("terms", [])

            if terms:
                print("\n分解出的知识点:")
                for i, term in enumerate(terms, 1):
                    print(f"  {i}. {term.name}")

                self._start_socratic(terms[0])
            else:
                print("未能解析出问题知识点")

        except Exception as e:
            print(f"解析失败: {e}")

    def _learn_concept(self, concept: str):
        """学习概念"""
        print(f"[学习概念] {concept}")

        # 模拟术语（实际需要LLM提取）
        mock_term = Term(
            name=concept,
            importance=0.9,
            source_position=0,
            reason="用户指定"
        )

        self._start_socratic(mock_term)

    def _start_socratic(self, term: Optional[Term]):
        """启动苏格拉底引导"""
        if not term:
            print("没有可学习的内容")
            return

        print(f"\n{'='*50}")
        print(f"开始学习: {term.name}")
        print(f"{'='*50}")
        print("进入苏格拉底式学习引导...")
        print("(注意: 当前版本需要配置LLM才能进行真正的对话)")
        print()

        # 添加到已学习
        self.learned_terms.append(term.name)

        # 演示苏格拉底对话流程
        print(f"AI: 你好！让我们一起学习 '{term.name}'。")
        print(f"AI: 首先，你对 '{term.name}' 有哪些了解？")
        print()
        print("(等待LLM配置完成以启用完整对话功能)")
        print()


# 便捷函数
def start_interactive():
    """启动交互模式"""
    mode = InteractiveMode()
    return mode.run()
