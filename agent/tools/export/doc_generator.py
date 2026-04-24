"""
LLM 文档生成
"""

from typing import Dict, List

from agent.llm_client import get_llm_client
from agent.anthropic_messages import extract_text_from_message


class DocGenerator:
    """生成 Obsidian 格式的 Markdown 文档"""

    def __init__(self):
        self.llm = get_llm_client()

    def format_conversation(self, message_history: List[Dict]) -> str:
        """格式化对话历史"""
        lines = []
        for msg in message_history:
            role = msg.get("role", "unknown")
            text = extract_text_from_message(msg)
            if role == "user":
                lines.append(f"用户: {text}")
            elif role == "assistant":
                lines.append(f"AI: {text}")
        return "\n\n".join(lines)

    def generate_docs(
        self,
        message_history: List[Dict],
        current_term: str,
        anchors: Dict,
        vault_manager
    ) -> str:
        """
        生成 Obsidian 格式的 Markdown 文档

        Args:
            message_history: 对话历史
            current_term: 当前概念
            anchors: 锚点信息
            vault_manager: VaultManager 实例

        Returns:
            str: 生成的 Markdown 内容
        """
        conversation_text = self.format_conversation(message_history)

        topic_anchor = anchors.get("topic_anchor", "通用")
        dependency_anchors = anchors.get("dependency_anchors", [])
        semantic_anchor = anchors.get("semantic_anchor", "")
        contrast_anchor = anchors.get("contrast_anchor", "")
        example_anchor = anchors.get("example_anchor", "")

        dependencies_str = ", ".join(dependency_anchors) if dependency_anchors else "无"

        # 获取现有子文件夹参考
        subfolders_by_category = vault_manager.get_subfolders_by_category()

        # 构建子文件夹参考文本
        subfolders_ref = "\n".join([
            f"{cat} 目录下已存在的子文件夹：\n- " + ("\n- ".join(subfolders_by_category[cat]) if subfolders_by_category[cat] else "（无）")
            for cat in vault_manager.get_all_categories()
        ])

        prompt = f"""你是一位知识工程师（Knowledge Engineer），擅长将对话整理为可复用的知识卡片（Zettelkasten 风格），并适配 Obsidian 知识库。

## 对话主题
{current_term}

## 输入结构说明
- 主题领域: {topic_anchor}（如：机器学习 / 心理学）
- 前置概念: {dependencies_str}（逗号分隔，如：A, B, C）
- 核心定义: {semantic_anchor}（一句话）
- 对比区分: {contrast_anchor}（A vs B）
- 典型例子: {example_anchor}（简要描述）

## 现有子文件夹参考（动态获取）

{subfolders_ref}

请根据内容首先选择最合适的 para_category，然后选择该 category 下的子文件夹。如果都不合适，请使用"新建:文件夹名"格式创建新文件夹。

## 对话历史
{conversation_text}

---

## 🎯 任务目标

将对话转化为**结构化、可链接、可检索的知识卡片**：

- 提炼核心知识（而不是复述对话）
- 构建概念之间的链接关系
- 输出适合 Obsidian + Dataview 的 Markdown

---

## 📦 输出要求（必须严格遵守）

### 单文档优先原则 ⭐

**核心原则**：对话围绕单一主题时，**只生成一个核心文档**。

✅ 正确做法：
- 主文档使用 [[双链]] 引用其他概念，而非生成独立文档
- 对比表格中的概念用 [[双链]] 引用
- 相关概念列表中的每个概念用 [[双链]] 引用

### 多文档生成规则

**第一性原理：对话历史是唯一来源**

- 只导出对话中实际提到过的概念
- 禁止凭空生成对话中不存在的"关键概念"
- 单文档还是多文档，由 LLM 根据对话内容自行判断
- 多文档时用 ===DOC_SEPARATOR=== 分隔，文档间用 [[双链]] 建立关联

### 文档结构模板

每个文档正文应包含：

# 🧾 概要
用 3–5 条总结核心内容（高密度信息）

# 💡 核心定义
- 用一句话给出标准定义
- 如有必要，补充解释

# 🧠 关键机制 / 原理
- 用结构化方式解释"为什么成立"
- 尽量拆成 2–4 个要点

# ⚖️ 对比与区分
- 使用表格或列表
- 明确与相似概念的区别

# 📊 典型例子
- 给出 1–3 个具体例子
- 优先使用现实场景

# 🔗 相关概念（双链）
- 使用 [[双链]] 格式
- 包含：
  - 前置概念（来自 dependencies）
  - 派生概念
  - 易混淆概念

# 📌 行动项 / 启发
- 可执行建议 或 思考问题

---

## 🔗 链接策略（关键）

- 每个重要概念必须转为 [[双链]]
- 避免大而泛的词（如：系统、方法）
- 优先原子化概念（一个概念=一张卡片）

---

## 🧠 写作风格

- 高信息密度（避免废话）
- 结构清晰（多用列表/层级）
- 可长期复用（避免上下文依赖）

---

## 🚫 禁止事项

- 不要复述对话过程
- 不要输出解释性说明
- 不要使用"根据以上对话…"等元语言

---

请直接输出 Markdown 内容。"""

        messages = [{"role": "user", "content": prompt}]
        response = self.llm.chat(messages, max_tokens=196607)

        return response
