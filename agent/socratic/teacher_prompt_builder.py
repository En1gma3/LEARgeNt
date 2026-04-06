"""
老师 Agent System Prompt 构建器

提供统一的 prompt 生成接口，支持多轮对话上下文
"""

from typing import Dict, Any, List, Optional


def build_teacher_system_prompt(
    term: str,
    definition: str,
    anchors: Dict[str, Any],
    phase: str,
    state_description: str = "开始学习"
) -> str:
    """
    构建当前阶段的完整 system prompt

    Args:
        term: 概念名称
        definition: 概念定义
        anchors: 锚点数据
        phase: 当前阶段 ('explanation', 'q_a', 'comprehension_check', 'remediation', 'summary')
        state_description: 状态描述

    Returns:
        str: 完整的 system prompt
    """
    from agent.socratic.teacher_persona import TEACHER_PERSONA, TEACHING_PHASES

    # 构建锚点字符串
    topic_anchor = anchors.get('topic_anchor', '未知')
    dependency_anchors = ', '.join(anchors.get('dependency_anchors', [])) if anchors.get('dependency_anchors') else '暂无'
    semantic_anchor = anchors.get('semantic_anchor', '未知')
    contrast_anchor = anchors.get('contrast_anchor', '暂无')
    example_anchor = anchors.get('example_anchor', '暂无')

    # 填充 Persona 模板
    persona = TEACHER_PERSONA.format(
        term=term,
        definition=definition,
        state_description=state_description,
        topic_anchor=topic_anchor,
        dependency_anchors=dependency_anchors,
        semantic_anchor=semantic_anchor,
        contrast_anchor=contrast_anchor,
        example_anchor=example_anchor
    )

    # 添加阶段指导
    phase_guidance = TEACHING_PHASES.get(phase, "")

    # 特殊处理 phase 中包含 term 的情况
    if phase == "explanation":
        phase_guidance = phase_guidance.format(term=term)
    elif phase == "remediation":
        # remediation 阶段会单独处理
        pass

    return f"{persona}\n\n{phase_guidance}"


def build_messages(
    term: str,
    definition: str,
    anchors: Dict[str, Any],
    phase: str,
    user_input: str,
    message_history: List[Dict[str, str]] = None,
    state_description: str = "学习进行中",
    extra_context: Dict[str, str] = None
) -> List[Dict[str, str]]:
    """
    构建完整的消息列表

    Args:
        term: 概念名称
        definition: 概念定义
        anchors: 锚点数据
        phase: 当前阶段
        user_input: 用户输入
        message_history: 之前的对话历史
        state_description: 状态描述
        extra_context: 额外的上下文信息（如 user_explanation, feedback 等）

    Returns:
        List[Dict[str, str]]: 包含 system prompt + 历史消息 + 当前输入 的消息列表
    """
    system_prompt = build_teacher_system_prompt(
        term=term,
        definition=definition,
        anchors=anchors,
        phase=phase,
        state_description=state_description
    )

    messages = [{"role": "system", "content": system_prompt}]

    # 添加历史消息
    if message_history:
        messages.extend(message_history)

    # 构建用户输入
    if extra_context and phase == "remediation":
        # remediation 阶段需要特殊上下文
        user_content = user_input.format(
            user_explanation=extra_context.get('user_explanation', ''),
            feedback=extra_context.get('feedback', '')
        )
    else:
        user_content = user_input

    # 添加当前用户输入
    messages.append({"role": "user", "content": user_content})

    return messages


def format_remediation_prompt(user_explanation: str, feedback: str, user_input_template: str) -> str:
    """
    格式化 remediation 阶段的用户输入

    Args:
        user_explanation: 学生的解释
        feedback: 系统反馈
        user_input_template: 用户输入模板

    Returns:
        str: 格式化后的用户输入
    """
    return user_input_template.format(
        user_explanation=user_explanation,
        feedback=feedback
    )