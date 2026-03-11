"""
学习总结与思维导图模块
"""

from typing import Dict, Any, Optional


class Summarizer:
    """学习总结生成器"""

    def __init__(self):
        pass

    def generate_summary(self, term_name: str, definition: str,
                        related_terms: list = None, notes: str = "") -> str:
        """
        生成学习总结

        Args:
            term_name: 名词名称
            definition: 解释内容
            related_terms: 相关名词列表
            notes: 学习笔记

        Returns:
            格式化的总结文本
        """
        lines = [
            f"# {term_name} 学习总结",
            "",
            "## 核心要点",
            "- " + definition.split('\n')[0] if definition else "",
            "",
            "## 定义",
            definition or "无",
            "",
        ]

        if related_terms:
            lines.extend([
                "## 相关概念",
                ", ".join(f"- {t}" for t in related_terms),
                "",
            ])

        if notes:
            lines.extend([
                "## 学习笔记",
                notes,
                "",
            ])

        lines.extend([
            "## 实践建议",
            "- 深入理解核心概念",
            "- 结合实际案例学习",
            "- 与已有知识建立联系",
        ])

        return "\n".join(lines)

    def format_definition(self, term_name: str, definition: str) -> str:
        """格式化名词解释"""
        sections = definition.split('\n\n')

        lines = [
            f"=== {term_name} ===",
            ""
        ]

        for section in sections:
            if section.strip():
                lines.append(section.strip())
                lines.append("")

        return "\n".join(lines)


class MindmapGenerator:
    """思维导图生成器"""

    def __init__(self):
        pass

    def generate_markdown(self, term_name: str, definition: str,
                         related_terms: list = None) -> str:
        """
        生成Markdown格式思维导图

        Args:
            term_name: 名词名称
            definition: 解释内容
            related_terms: 相关名词列表

        Returns:
            Markdown格式思维导图
        """
        lines = [
            f"# {term_name}",
            "",
            "## 定义",
            "- " + (definition.split('\n')[0] if definition else "无"),
            "",
            "## 核心要点",
        ]

        # 解析definition中的要点
        if definition:
            for line in definition.split('\n'):
                line = line.strip()
                if line and line[0] in '-+*':
                    lines.append(line)

        if related_terms:
            lines.extend([
                "",
                "## 相关概念",
            ])
            for term in related_terms:
                lines.append(f"- {term}")

        return "\n".join(lines)

    def generate_mermaid(self, term_name: str, related_terms: list = None) -> str:
        """
        生成Mermaid格式思维导图

        Args:
            term_name: 名词名称
            related_terms: 相关名词列表

        Returns:
            Mermaid格式
        """
        lines = [
            "```mermaid",
            "graph TD",
            f"    A[{term_name}]"
        ]

        if related_terms:
            for i, term in enumerate(related_terms[:5], 1):  # 限制数量
                lines.append(f"    A --> B{i}[{term}]")

        lines.append("```")

        return "\n".join(lines)

    def export_image(self, term_name: str, format: str = "png") -> str:
        """
        导出图片（需要graphviz）

        Args:
            term_name: 名词名称
            format: 格式 (png/svg)

        Returns:
            文件路径
        """
        # 简化实现：返回提示信息
        return f"需要安装graphviz才能导出{format}格式"
