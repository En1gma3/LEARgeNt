"""
大模型提取器

使用LLM提取关键术语并排序
"""

import json
from typing import List, Optional

from .base import BaseExtractor, Term


class LLMExtractor(BaseExtractor):
    """大模型提取器"""

    def __init__(self, llm_client=None):
        """
        初始化

        Args:
            llm_client: LLM客户端，如果为None则使用默认
        """
        self._llm = llm_client

    def extract(self, content: str, max_terms: int = 20) -> List[Term]:
        """
        使用LLM提取术语

        Args:
            content: 文本内容
            max_terms: 最大提取数量

        Returns:
            List[Term]: 提取的术语列表
        """
        if self._llm is None:
            # 使用默认的LLM客户端
            self._llm = self._get_default_llm()

        if self._llm is None:
            raise RuntimeError("未配置LLM客户端")

        # 构建Prompt
        prompt = self._build_prompt(content, max_terms)

        # 调用LLM
        response = self._llm.chat(prompt)

        # 解析结果
        terms = self._parse_response(response)

        return terms

    def _get_default_llm(self):
        """获取默认LLM客户端"""
        # TODO: 实现默认LLM客户端
        # 这里预留接口
        return None

    def _build_prompt(self, content: str, max_terms: int) -> str:
        """构建Prompt"""
        # 截取内容（前4000字符）
        truncated_content = content[:4000]

        return f"""请从以下文本中提取关键名词和术语，并按重要性排序。

文本内容:
{truncated_content}

要求:
1. 提取所有专业术语和技术名词
2. 按重要性从高到低排序
3. 返回JSON格式: {{"terms": [{{"name": "术语名", "importance": 0.95, "reason": "提取理由"}}, ...]}}
4. 提取数量控制在{max_terms}个以内
5. importance为0-1之间的浮点数

请直接返回JSON，不要其他内容:"""

    def _parse_response(self, response: str) -> List[Term]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            json_str = self._extract_json(response)
            if not json_str:
                return []

            data = json.loads(json_str)
            terms_data = data.get("terms", [])

            terms = []
            for idx, item in enumerate(terms_data):
                terms.append(Term(
                    name=item.get("name", ""),
                    importance=item.get("importance", 0.5),
                    source_position=idx,
                    reason=item.get("reason", "LLM提取")
                ))

            return terms

        except (json.JSONDecodeError, KeyError) as e:
            # 解析失败，返回空列表
            return []

    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON"""
        import re

        # 尝试直接解析
        try:
            json.loads(text)
            return text
        except:
            pass

        # 尝试提取 ```json ... ``` 块
        pattern = r'```json\s*(.*?)\s*```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)

        # 尝试提取 { ... }
        pattern = r'\{.*\}'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(0)

        return None


# 便捷函数
def extract_with_llm(content: str, max_terms: int = 20, llm_client=None) -> List[Term]:
    """
    使用LLM提取术语的便捷函数

    Args:
        content: 文本内容
        max_terms: 最大提取数量
        llm_client: LLM客户端

    Returns:
        List[Term]: 提取的术语列表
    """
    extractor = LLMExtractor(llm_client)
    return extractor.extract(content, max_terms)
