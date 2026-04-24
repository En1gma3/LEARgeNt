"""
Obsidian 导出器

主导出器，整合 VaultManager, DocGenerator, DocParser
"""

from typing import Dict, List

from .vault_manager import VaultManager
from .doc_generator import DocGenerator
from .doc_parser import DocParser


class ObsidianExporter:
    """导出学习会话到 Obsidian 格式"""

    def __init__(self, vault_dir: str = "vault_test"):
        self.vault_manager = VaultManager(vault_dir)
        self.doc_generator = DocGenerator()
        self.doc_parser = DocParser(self.vault_manager)

    async def export(
        self,
        message_history: List[Dict],
        current_term: str,
        anchors: Dict
    ) -> Dict:
        """
        导出学习会话

        Args:
            message_history: 对话历史
            current_term: 当前概念
            anchors: 锚点信息

        Returns:
            Dict: 导出结果，包含 success, files, message
        """
        # 生成文档
        docs = self.doc_generator.generate_docs(
            message_history,
            current_term,
            anchors,
            self.vault_manager
        )

        # 解析并保存文档
        files = self.doc_parser.parse_and_save(docs, current_term)

        return {
            "success": True,
            "files": files,
            "message": f"已导出 {len(files)} 个文件到 vault/ 目录"
        }

    def get_vault_manager(self) -> VaultManager:
        """获取 VaultManager 实例"""
        return self.vault_manager
