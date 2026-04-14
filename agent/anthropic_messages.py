"""
Anthropic Messages API 格式工具模块

提供 Anthropic 消息格式的创建和转换工具函数，
确保消息格式符合 Anthropic Messages API 规范。
"""

import uuid
from typing import Any, Dict, List, Union


def text_content_block(text: str) -> Dict[str, Any]:
    """创建文本内容块"""
    return {"type": "text", "text": text}


def tool_use_content_block(tool_use_id: str, tool_name: str, tool_input: Dict) -> Dict[str, Any]:
    """创建 tool_use 内容块"""
    return {
        "type": "tool_use",
        "id": tool_use_id,
        "name": tool_name,
        "input": tool_input
    }


def tool_result_content_block(tool_use_id: str, content: str, is_error: bool = False) -> Dict[str, Any]:
    """创建 tool_result 内容块"""
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
        "is_error": is_error
    }


def user_message(content: Union[str, List[Dict]], role: str = "user") -> Dict[str, Any]:
    """创建用户消息（自动处理文本或内容块列表）"""
    if isinstance(content, str):
        return {"role": role, "content": [text_content_block(content)]}
    return {"role": role, "content": content}


def assistant_message(content: Union[str, List[Dict]]) -> Dict[str, Any]:
    """创建助手消息（自动处理文本或内容块列表）"""
    if isinstance(content, str):
        return {"role": "assistant", "content": [text_content_block(content)]}
    return {"role": "assistant", "content": content}


def assistant_message_with_tool(tool_use_id: str, tool_name: str, tool_input: Dict) -> Dict[str, Any]:
    """创建包含 tool_use 的助手消息"""
    return {
        "role": "assistant",
        "content": [tool_use_content_block(tool_use_id, tool_name, tool_input)]
    }


def convert_dict_to_anthropic_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    将简单字典消息转换为 Anthropic 格式

    输入: {"role": "user", "content": "Hello"}
    输出: {"role": "user", "content": [{"type": "text", "text": "Hello"}]}

    输入: {"role": "assistant", "content": "Hi"}
    输出: {"role": "assistant", "content": [{"type": "text", "text": "Hi"}]}
    """
    role = msg.get("role")
    content = msg.get("content", "")

    if role == "system":
        # System 消息不转换，保持原样
        return msg

    if isinstance(content, str):
        return {"role": role, "content": [text_content_block(content)]}
    elif isinstance(content, list):
        # 已经是内容块列表，直接返回
        return {"role": role, "content": content}
    else:
        return {"role": role, "content": [text_content_block(str(content))]}


def convert_messages_to_anthropic_format(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将消息列表批量转换为 Anthropic 格式"""
    return [convert_dict_to_anthropic_message(msg) for msg in messages]


def extract_text_from_message(msg: Dict[str, Any]) -> str:
    """从消息中提取文本内容（兼容多种格式）"""
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    text_parts.append(str(block.get("content", "")))
            elif isinstance(block, str):
                text_parts.append(block)
        return "\n".join(text_parts)
    return str(content)


def extract_tool_calls_from_response(response_content: List) -> List[Dict[str, Any]]:
    """从响应内容块中提取所有 tool_use 块"""
    tool_calls = []
    for block in response_content:
        if hasattr(block, 'type') and block.type == "tool_use":
            # SDK 对象
            tool_calls.append({
                "id": block.id,
                "name": block.name,
                "input": block.input
            })
        elif isinstance(block, dict) and block.get("type") == "tool_use":
            # 已经是字典格式
            tool_calls.append({
                "id": block.get("id"),
                "name": block.get("name"),
                "input": block.get("input")
            })
    return tool_calls


def create_tool_use_id() -> str:
    """生成唯一的 tool_use_id"""
    return f"toolu_{uuid.uuid4().hex[:16]}"


def is_anthropic_format(msg: Dict[str, Any]) -> bool:
    """检查消息是否已经是 Anthropic 格式（content 为列表）"""
    content = msg.get("content", "")
    return isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict)
