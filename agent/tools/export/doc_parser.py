"""
Markdown 文档解析
"""

import os
import re
from datetime import datetime
from typing import List, Dict


class DocParser:
    """解析并保存 Obsidian Markdown 文档"""

    def __init__(self, vault_manager):
        self.vault_manager = vault_manager

    def parse_and_save(self, markdown_content: str, current_term: str) -> List[Dict]:
        """
        解析 LLM 响应并保存为 Obsidian 文件（支持多文档）

        Args:
            markdown_content: 生成的 Markdown 内容
            current_term: 当前概念

        Returns:
            List[Dict]: 保存的文件信息列表
        """
        # 清理 markdown 代码块包装
        markdown_content = self._clean_markdown(markdown_content)

        vault_dir = self.vault_manager.get_vault_dir()
        if not os.path.exists(vault_dir):
            os.makedirs(vault_dir)

        files = []

        # 按 ===DOC_SEPARATOR=== 分割多个文档
        doc_blocks = markdown_content.split('===DOC_SEPARATOR===')

        for block in doc_blocks:
            block = block.strip()
            if not block:
                continue

            file_info = self._parse_single_doc(block, current_term)
            if file_info:
                files.append(file_info)

        # 如果没有成功解析任何文档块（兼容旧格式）
        if not files:
            file_info = self._parse_fallback(markdown_content, current_term)
            if file_info:
                files.append(file_info)

        return files

    def _clean_markdown(self, markdown_content: str) -> str:
        """清理 markdown 代码块包装"""
        lines = markdown_content.strip().split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        return '\n'.join(lines).strip()

    def _parse_single_doc(self, block: str, current_term: str) -> Dict:
        """解析单个文档块"""
        # 解析 frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---', block, re.DOTALL)
        if not frontmatter_match:
            return None

        frontmatter_text = frontmatter_match.group(1)
        full_content = block.strip()

        title = current_term
        tags = ["学习", "概念"]
        para_category = "Areas"
        subfolder = "通用"

        for line in frontmatter_text.split("\n"):
            if line.startswith("title:"):
                title = line.replace("title:", "").strip().strip('"\'')
            elif line.startswith("tags:"):
                tag_match = re.findall(r"\[([^\]]+)\]", line)
                if tag_match:
                    tags = [t.strip() for t in tag_match[0].split(",")]
            elif line.startswith("para_category:"):
                cat_match = re.findall(r"\[([^\]]+)\]", line)
                if cat_match:
                    para_category = cat_match[0].strip()
            elif line.startswith("subfolder:"):
                sub_match = re.findall(r"\[([^\]]+)\]", line)
                if sub_match:
                    subfolder = sub_match[0].strip()
                else:
                    subfolder = line.replace("subfolder:", "").strip().strip('"\'')
                if subfolder.startswith("新建:"):
                    subfolder = subfolder.replace("新建:", "").strip()

        return self._save_doc(full_content, title, tags, para_category, subfolder)

    def _parse_fallback(self, markdown_content: str, current_term: str) -> Dict:
        """回退解析（兼容没有 frontmatter 的旧格式）"""
        frontmatter_match = re.match(r'^---\n(.*?)\n---', markdown_content, re.DOTALL)
        if frontmatter_match:
            frontmatter_text = frontmatter_match.group(1)
            full_content = markdown_content.strip()

            title = current_term
            tags = ["学习", "概念"]
            para_category = "Areas"
            subfolder = "通用"

            for line in frontmatter_text.split("\n"):
                if line.startswith("title:"):
                    title = line.replace("title:", "").strip().strip('"\'')
                elif line.startswith("tags:"):
                    tag_match = re.findall(r"\[([^\]]+)\]", line)
                    if tag_match:
                        tags = [t.strip() for t in tag_match[0].split(",")]
                elif line.startswith("para_category:"):
                    cat_match = re.findall(r"\[([^\]]+)\]", line)
                    if cat_match:
                        para_category = cat_match[0].strip()
                elif line.startswith("subfolder:"):
                    sub_match = re.findall(r"\[([^\]]+)\]", line)
                    if sub_match:
                        subfolder = sub_match[0].strip()
                    else:
                        subfolder = line.replace("subfolder:", "").strip().strip('"\'')
                    if subfolder.startswith("新建:"):
                        subfolder = subfolder.replace("新建:", "").strip()

            return self._save_doc(full_content, title, tags, para_category, subfolder)
        else:
            # 没有 frontmatter，作为单个文档处理
            title = current_term
            safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)
            vault_dir = self.vault_manager.get_vault_dir()
            filepath = os.path.join(vault_dir, f"{safe_title}.md")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            return {
                "path": filepath,
                "title": title,
                "wiki_link": f"[[{title}]]",
                "tags": ["学习", "概念"]
            }

    def _save_doc(
        self,
        full_content: str,
        title: str,
        tags: List[str],
        para_category: str,
        subfolder: str
    ) -> Dict:
        """保存文档到指定目录"""
        safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)
        category_dir = self.vault_manager.ensure_directory(para_category, subfolder)
        filepath = os.path.join(category_dir, f"{safe_title}.md")

        # 更新日期
        now = datetime.now().strftime("%Y-%m-%d")
        full_content = re.sub(r'^created:.*$', f'created: {now}', full_content, flags=re.MULTILINE)
        full_content = re.sub(r'^updated:.*$', f'updated: {now}', full_content, flags=re.MULTILINE)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)

        return {
            "path": filepath,
            "title": title,
            "wiki_link": f"[[{title}]]",
            "tags": tags
        }
