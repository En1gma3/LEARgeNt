"""
终端箭头键选择组件

支持单列和多列网格布局的键盘选择
"""

import sys
import os
from typing import List, Optional

# 跨平台键盘输入
try:
    import readchar
except ImportError:
    readchar = None

# 日志
try:
    from utils import get_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)
    get_logger = lambda name: logging.getLogger(name)

logger = get_logger(__name__)


class ArrowSelector:
    """终端箭头键选择组件"""

    def __init__(
        self,
        items: List[str],
        title: str = None,
        multi_column: bool = False,
        columns: int = 3,
        initial_index: int = 0
    ):
        """
        Args:
            items: 选项列表
            title: 菜单标题
            multi_column: 是否多列布局
            columns: 列数（多列模式）
            initial_index: 初始选中索引
        """
        self.items = items
        self.title = title
        self.multi_column = multi_column
        self.columns = columns if multi_column else 1

        self._selected_index = initial_index
        self._running = False

    def run(self) -> Optional[int]:
        """
        运行选择器

        Returns:
            选中的索引，或 None（用户取消）
        """
        if not self.items:
            return None

        # 检查是否是 TTY，如果不是则使用文本输入
        if not sys.stdin.isatty():
            return self._run_text_mode()

        self._selected_index = 0
        self._running = True

        # 设置终端为原始模式
        if sys.platform != 'windows':
            import tty
            import termios
            old_settings = termios.tcgetattr(sys.stdin)
        else:
            old_settings = None

        try:
            self._render()

            while self._running:
                key = self._read_key()

                if key in ('\x1b[A', 'k'):  # 上箭头 或 vim k
                    self._move_up()
                elif key in ('\x1b[B', 'j'):  # 下箭头 或 vim j
                    self._move_down()
                elif key in ('\x1b[C', 'l'):  # 右箭头 或 vim l
                    self._move_right()
                elif key in ('\x1b[D', 'h'):  # 左箭头 或 vim h
                    self._move_left()
                elif key in ('\r', '\n'):  # 回车
                    self._running = False
                    self._clear_render()
                    return self._selected_index
                elif key in ('\x1b', 'q', 'Q'):  # Esc 或 q/Q 取消
                    self._running = False
                    self._clear_render()
                    return None

        finally:
            # 恢复终端设置
            if sys.platform != 'windows' and old_settings is not None:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        self._clear_render()
        return self._selected_index

    def _run_text_mode(self) -> Optional[int]:
        """文本输入模式（非 TTY 环境）"""
        self._render_text()

        while True:
            try:
                user_input = input("请输入序号: ").strip()
            except (EOFError, KeyboardInterrupt):
                return None

            if user_input.lower() in ['q', 'quit', '退出', 'cancel']:
                return None

            try:
                idx = int(user_input) - 1
                if 0 <= idx < len(self.items):
                    return idx
                else:
                    print(f"无效序号，请输入 1-{len(self.items)} 之间的数字")
            except ValueError:
                print("无效输入，请输入数字序号")

    def _read_key(self) -> str:
        """读取按键"""
        if readchar is not None:
            return readchar.readkey()
        else:
            # 回退方案
            return sys.stdin.read(1)

    def _move_up(self):
        """向上移动"""
        if self.multi_column:
            # 多列模式：向上移动一整行
            self._selected_index -= self.columns
            if self._selected_index < 0:
                self._selected_index = len(self.items) - 1
        else:
            # 单列模式
            self._selected_index = (self._selected_index - 1) % len(self.items)
        self._render()

    def _move_down(self):
        """向下移动"""
        if self.multi_column:
            # 多列模式：向下移动一整行
            self._selected_index += self.columns
            if self._selected_index >= len(self.items):
                self._selected_index = 0
        else:
            # 单列模式
            self._selected_index = (self._selected_index + 1) % len(self.items)
        self._render()

    def _move_left(self):
        """向左移动（仅多列模式）"""
        if self.multi_column:
            if self._selected_index % self.columns > 0:
                self._selected_index -= 1
            self._render()

    def _move_right(self):
        """向右移动（仅多列模式）"""
        if self.multi_column:
            if self._selected_index % self.columns < self.columns - 1:
                if self._selected_index + 1 < len(self.items):
                    self._selected_index += 1
            self._render()

    def _render(self):
        """渲染选择菜单"""
        self._clear_render()

        # 计算布局
        rows = []
        if self.multi_column:
            rows = self._render_multi_column()
        else:
            rows = self._render_single_column()

        # 输出
        if self.title:
            print(f"\n{self.title}")
            print("-" * 40)

        for row in rows:
            print(row)

        print("-" * 40)
        print("↑↓←→ 或 k/j/h/l 导航 | Enter 确认 | Esc/q 取消")

        # 移动光标到开头
        if sys.platform != 'windows':
            sys.stdout.write(f"\033[{len(rows) + 3}A")

    def _render_text(self):
        """渲染文本模式选择菜单"""
        if self.title:
            print(f"\n{self.title}")
            print("=" * 40)

        for i, item in enumerate(self.items, 1):
            print(f"  {i}. {item}")

        print("=" * 40)
        print(f"输入 q 取消")

    def _render_single_column(self) -> List[str]:
        """渲染单列布局"""
        lines = []
        for i, item in enumerate(self.items):
            prefix = "▶ " if i == self._selected_index else "  "
            lines.append(f"{prefix}{item}")
        return lines

    def _render_multi_column(self) -> List[str]:
        """渲染多列布局"""
        lines = []
        max_width = max(len(item) for item in self.items)
        col_width = max_width + 4  # prefix + padding

        # 计算行数
        num_items = len(self.items)
        num_rows = (num_items + self.columns - 1) // self.columns

        for row in range(num_rows):
            line_parts = []
            for col in range(self.columns):
                idx = row + col * num_rows
                if idx < num_items:
                    item = self.items[idx]
                    prefix = "▶" if idx == self._selected_index else " "
                    # 计算对齐
                    padding = max_width - len(item) + 2
                    line_parts.append(f"{prefix} {item}{' ' * padding}")
                else:
                    line_parts.append(" " * col_width)
            lines.append("  ".join(line_parts))

        return lines

    def _clear_render(self):
        """清除已渲染的内容"""
        if sys.platform == 'windows':
            os.system('cls')
        else:
            # 使用 ANSI 转义序列清除
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()


class DimensionSelector(ArrowSelector):
    """维度选择器（专门用于 Learn 模式选择主题维度）"""

    def __init__(self, dimensions: List[str]):
        super().__init__(
            items=dimensions,
            title="请选择方面：",
            multi_column=False
        )


def readline_with_chinese(prompt: str = "> ") -> str:
    """
    支持中文输入的 readline 风格函数

    使用 readchar 逐字符读取，自行处理退格键
    解决 Python input() 在中文输入时的兼容性问题
    """
    if readchar is None:
        # 降级到普通 input
        return input(prompt).strip()

    # 检查是否 TTY，非 TTY 使用普通 input
    if not sys.stdin.isatty():
        return input(prompt).strip()

    print(prompt, end="", flush=True)
    buffer = []

    while True:
        key = readchar.readkey()
        logger.debug(f"[readline] key={repr(key)}, buffer={buffer}")

        if key in ("\r", "\n"):
            # 回车：输出换行并返回
            print()
            return "".join(buffer)

        elif key in ("\x7f", "\b"):  # DEL (Backspace) 或 BS
            if buffer:
                buffer.pop()
                # 清除当前行并重新显示
                sys.stdout.write("\r\033[K")  # 回车 + 清除到行尾
                sys.stdout.write(prompt)
                sys.stdout.write("".join(buffer))
                sys.stdout.flush()
            # else: 已经空了，忽略

        elif len(key) == 1 and ord(key) < 32:
            # 控制字符，忽略
            pass

        else:
            # 普通字符（包括中文）添加到缓冲区
            buffer.append(key)
            # 立即显示字符
            sys.stdout.write(key)
            sys.stdout.flush()
