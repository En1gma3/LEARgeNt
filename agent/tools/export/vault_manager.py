"""
Vault 目录结构管理
"""

import os
from typing import List, Dict


class VaultManager:
    """管理 Obsidian Vault 目录结构"""

    def __init__(self, vault_dir: str = "vault_test"):
        self.vault_dir = vault_dir
        self._init_vault_structure()

    def _init_vault_structure(self):
        """初始化 vault 文件夹结构"""
        folders = {
            "Projects": ["学习中", "工作中"],
            "Areas": ["投资", "心理学", "健康管理", "学习方法"],
            "Resources": ["工具", "文章", "书籍", "课程"],
            "Archives": ["旧项目", "废弃内容"]
        }
        for category, subfolders in folders.items():
            for subfolder in subfolders:
                path = os.path.join(self.vault_dir, category, subfolder)
                os.makedirs(path, exist_ok=True)

    def get_existing_subfolders(self, para_category: str) -> List[str]:
        """获取指定 para_category 下的现有子文件夹"""
        category_path = os.path.join(self.vault_dir, para_category)
        if not os.path.exists(category_path):
            return []
        return [d for d in os.listdir(category_path)
                if os.path.isdir(os.path.join(category_path, d))]

    def get_all_categories(self) -> List[str]:
        """获取所有分类目录"""
        return ["Areas", "Resources", "Projects", "Archives"]

    def get_subfolders_by_category(self) -> Dict[str, List[str]]:
        """获取所有分类及其子文件夹"""
        result = {}
        for cat in self.get_all_categories():
            result[cat] = self.get_existing_subfolders(cat)
        return result

    def ensure_directory(self, para_category: str, subfolder: str) -> str:
        """确保目录存在并返回完整路径"""
        category_dir = os.path.join(self.vault_dir, para_category, subfolder)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)
        return category_dir

    def get_vault_dir(self) -> str:
        """获取 vault 根目录"""
        return self.vault_dir
