"""
Agent模块

包含：
- socratic: 苏格拉底式学习引导
- intent: 意图识别
- dialogue: 对话管理
"""

from .socratic import SocraticGuide
from .intent import IntentRecognizer, Intent
from .dialogue import DialogueManager, DialogueState

__all__ = [
    'SocraticGuide',
    'IntentRecognizer',
    'Intent',
    'DialogueManager',
    'DialogueState',
]
