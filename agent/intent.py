"""
意图识别模块

识别用户输入的意图类型
"""

import re
from enum import Enum
from typing import Optional, Tuple, List, Dict, Any


class Intent(Enum):
    """意图类型"""
    LEARN = "learn"           # 学习新名词
    ASK = "ask"               # 提问
    TAG = "tag"               # 标签操作
    CONTEXT = "context"       # 语境设置
    IMPORT = "import"         # 导入文档
    REVIEW = "review"          # 复习
    SEARCH = "search"          # 搜索
    DISAMBIGUATE = "disambiguate"  # 消歧选择
    SUMMARY = "summary"       # 生成总结
    MINDMAP = "mindmap"       # 思维导图
    PATH = "path"             # 学习路径
    REMINDER = "reminder"      # 提醒设置
    STATS = "stats"            # 统计查看
    MODE = "mode"              # 模式切换
    LIST = "list"              # 列表查看
    VIEW = "view"              # 查看详情
    EDIT = "edit"              # 编辑
    HISTORY = "history"        # 历史记录
    HELP = "help"             # 帮助
    QUIT = "quit"              # 退出
    UNKNOWN = "unknown"        # 未知


# 命令模式
COMMAND_PATTERNS = {
    # 标签命令
    r'^/tag\s+create': (Intent.TAG, "create"),
    r'^/tag\s+add': (Intent.TAG, "add"),
    r'^/tag\s+remove': (Intent.TAG, "remove"),
    r'^/tag\s+list': (Intent.TAG, "list"),
    r'^/tag\s+view': (Intent.TAG, "view"),
    r'^/tag$': (Intent.TAG, "list"),

    # 语境命令
    r'^/context\s+set': (Intent.CONTEXT, "set"),
    r'^/context\s+clear': (Intent.CONTEXT, "clear"),
    r'^/context\s+show': (Intent.CONTEXT, "show"),
    r'^/context$': (Intent.CONTEXT, "show"),

    # 复习命令
    r'^/review\s+random': (Intent.REVIEW, "random"),
    r'^/review\s+tag': (Intent.REVIEW, "tag"),
    r'^/review\s+recent': (Intent.REVIEW, "recent"),
    r'^/review\s+set': (Intent.REVIEW, "set"),
    r'^/review$': (Intent.REVIEW, "today"),
    r'^/mode\s+review': (Intent.MODE, "review"),

    # 统计命令
    r'^/stats(?:\s+(today|week|month|knowledge|export))?': (Intent.STATS, None),

    # 思维导图命令
    r'^/mindmap(?:\s+(\S+)(?:\s+(mermaid|markdown|png|svg))?)?': (Intent.MINDMAP, None),

    # 学习路径命令
    r'^/path\s+create': (Intent.PATH, "create"),
    r'^/path\s+add': (Intent.PATH, "add"),
    r'^/path\s+start': (Intent.PATH, "start"),
    r'^/path\s+recommend': (Intent.PATH, "recommend"),
    r'^/path\s+progress': (Intent.PATH, "progress"),
    r'^/path\s+list': (Intent.PATH, "list"),
    r'^/path\s+view': (Intent.PATH, "view"),
    r'^/path$': (Intent.PATH, "list"),

    # 提醒命令
    r'^/reminder\s+add': (Intent.REMINDER, "add"),
    r'^/reminder\s+remove': (Intent.REMINDER, "remove"),
    r'^/reminder\s+list': (Intent.REMINDER, "list"),
    r'^/reminder\s+clear': (Intent.REMINDER, "clear"),
    r'^/reminder$': (Intent.REMINDER, "list"),

    # 消歧命令
    r'^/disambiguate\s+show': (Intent.DISAMBIGUATE, "show"),
    r'^/disambiguate\s+clear': (Intent.DISAMBIGUATE, "clear"),
    r'^/disambiguate\s+prefer': (Intent.DISAMBIGUATE, "prefer"),

    # 模式切换
    r'^/mode\s+(learn|qa|review)': (Intent.MODE, None),

    # 知识库命令
    r'^/(?:list|ls)$': (Intent.LIST, "terms"),
    r'^/view\s+(\S+)': (Intent.VIEW, "term"),
    r'^/import\s+(\S+)': (Intent.IMPORT, None),
    r'^/edit\s+(\S+)': (Intent.EDIT, None),
    r'^/history\s+(\S+)': (Intent.HISTORY, "term"),
    r'^/refresh\s+(\S+)': (Intent.EDIT, "refresh"),

    # 帮助
    r'^/help(?:\s+(\S+))?': (Intent.HELP, None),

    # 退出
    r'^/(?:exit|quit|q)$': (Intent.QUIT, None),

    # 学习命令 (含变体)
    r'^/(?:learn|l|学习)\s+': (Intent.LEARN, None),
}


class IntentRecognizer:
    """意图识别器"""

    def __init__(self):
        self._patterns = COMMAND_PATTERNS

    def recognize(self, user_input: str) -> Tuple[Intent, Optional[str], Dict[str, Any]]:
        """
        识别用户意图

        Returns:
            (意图, 实体, 额外参数)
        """
        user_input = user_input.strip()

        # 检查命令
        for pattern, (intent, sub_action) in self._patterns.items():
            match = re.match(pattern, user_input, re.IGNORECASE)
            if match:
                # 提取参数
                groups = match.groups()
                params = {}

                # 学习命令
                if intent == Intent.LEARN:
                    params['content'] = user_input.split(None, 1)[1] if len(user_input.split(None, 1)) > 1 else ""

                # 标签命令
                elif intent == Intent.TAG:
                    parts = user_input.split()
                    if sub_action in ["add", "remove"]:
                        # /tag add <term> <tag>
                        # parts[0]=/tag, parts[1]=add, parts[2]=term, parts[3]=tag
                        if len(parts) >= 4:
                            params['term'] = parts[2]
                            params['tag'] = parts[3]
                    elif sub_action == "view":
                        # /tag view <tag>
                        # parts[0]=/tag, parts[1]=view, parts[2]=tag
                        if len(parts) >= 3:
                            params['tag'] = parts[2]
                    elif sub_action == "create":
                        # /tag create <name>
                        # parts[0]=/tag, parts[1]=create, parts[2]=name
                        if len(parts) >= 3:
                            params['name'] = parts[2]

                # 统计命令
                elif intent == Intent.STATS:
                    if groups[0]:
                        params['period'] = groups[0]

                # 思维导图命令
                elif intent == Intent.MINDMAP:
                    if groups[0]:
                        params['term'] = groups[0]
                    if groups[1]:
                        params['format'] = groups[1]

                # 路径命令
                elif intent == Intent.PATH:
                    if sub_action == "recommend":
                        parts = user_input.split()
                        if len(parts) >= 2:
                            params['term'] = parts[1]
                    elif sub_action in ["start", "view"]:
                        parts = user_input.split(None, 2)
                        if len(parts) >= 2:
                            params['name'] = parts[1]
                    elif sub_action in ["add"]:
                        parts = user_input.split(None, 3)
                        if len(parts) >= 3:
                            params['path'] = parts[1]
                            params['term'] = parts[2]

                # 复习命令
                elif intent == Intent.REVIEW:
                    if sub_action == "random":
                        parts = user_input.split()
                        params['count'] = int(parts[2]) if len(parts) > 2 else 5
                    elif sub_action == "tag":
                        parts = user_input.split()
                        if len(parts) > 2:
                            params['tag'] = parts[2]
                    elif sub_action == "set":
                        parts = user_input.split()
                        if len(parts) > 2:
                            params['count'] = int(parts[2])

                # 查看/编辑/历史
                elif intent in [Intent.VIEW, Intent.EDIT, Intent.HISTORY]:
                    if groups[0]:
                        params['term'] = groups[0]

                # 导入
                elif intent == Intent.IMPORT:
                    if groups[0]:
                        params['path'] = groups[0]

                # 帮助
                elif intent == Intent.HELP:
                    if groups[0]:
                        params['topic'] = groups[0]

                # 模式
                elif intent == Intent.MODE:
                    if groups[0]:
                        params['mode'] = groups[0]

                return intent, sub_action, params

        # 检查自然语言学习请求
        learn_indicators = [
            r'^学习\s+(\S+)',
            r'^解释\s+(\S+)',
            r'^什么是\s+(\S+)',
            r'^(\S+)$',  # 单独名词
        ]

        for pattern in learn_indicators:
            match = re.match(pattern, user_input)
            if match:
                term = match.group(1)
                # 排除命令关键词
                if not term.startswith('/'):
                    return Intent.LEARN, term, {'content': term}

        # 问答模式
        question_indicators = ['是什么', '为什么', '如何', '怎么', '?', '？']
        if any(ind in user_input for ind in question_indicators):
            return Intent.ASK, user_input, {}

        return Intent.UNKNOWN, None, {}
