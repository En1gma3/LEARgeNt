"""
LearnMate CLI 启动入口
"""

import sys
import argparse
import asyncio
from typing import Optional

from .interactive import InteractiveMode


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="LearnMate - 智能学习助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python -m cli                    # 启动交互模式
  python -m cli learn 区块链       # 学习指定概念
  python -m cli --version          # 查看版本
        """
    )

    parser.add_argument(
        "command",
        nargs="?",
        help="命令 (learn/interactive)"
    )

    parser.add_argument(
        "args",
        nargs="*",
        help="命令参数"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细信息"
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )

    parser.add_argument(
        "--agent",
        action="store_true",
        help="使用新的Agent架构"
    )

    args = parser.parse_args()

    if args.version:
        print("LearnMate v0.1.0")
        print("智能学习助手 - 苏格拉底式引导学习")
        return 0

    # Agent 模式
    if args.agent:
        from agent.learn_agent import run_agent
        return asyncio.run(run_agent())

    # 交互模式
    if args.command == "interactive" or args.command is None:
        interactive = InteractiveMode()
        return interactive.run()

    # 学习模式
    if args.command == "learn":
        if not args.args:
            print("错误: 请指定要学习的内容")
            print("用法: python -m cli learn <概念名>")
            return 1

        concept = " ".join(args.args)
        interactive = InteractiveMode()
        return interactive.learn_concept(concept)

    # 未知命令
    print(f"未知命令: {args.command}")
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
