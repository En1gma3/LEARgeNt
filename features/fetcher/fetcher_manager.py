"""
Fetcher 管理器

管理多个信息获取器，按优先级尝试获取术语信息
"""

from typing import Optional, List

from .base import BaseFetcher, TermInfo
from .wikipedia_fetcher import WikipediaFetcher


class FetcherManager:
    """信息获取管理器"""

    def __init__(self):
        self.fetchers: List[BaseFetcher] = [
            WikipediaFetcher(),  # 优先 Wikipedia
        ]

    def fetch_term_info(self, term: str, language: str = "zh") -> Optional[TermInfo]:
        """
        获取术语信息

        按优先级尝试各个 fetcher，成功获取后立即返回

        Args:
            term: 术语名称
            language: 语言偏好

        Returns:
            TermInfo: 术语信息，获取失败返回 None
        """
        for fetcher in self.fetchers:
            if not fetcher.is_available():
                continue

            try:
                result = fetcher.fetch(term, language)
                if result and result.definition:
                    return result
            except Exception as e:
                print(f"Fetcher {fetcher.get_source_name()} failed: {e}")
                continue

        return None

    def add_fetcher(self, fetcher: BaseFetcher):
        """添加获取器"""
        self.fetchers.append(fetcher)

    def get_available_fetchers(self) -> List[str]:
        """获取可用的获取器列表"""
        return [
            fetcher.get_source_name()
            for fetcher in self.fetchers
            if fetcher.is_available()
        ]

    def enhance_with_llm(self, term_info: TermInfo) -> TermInfo:
        """
        使用 LLM 将原始定义结构化

        Args:
            term_info: 包含原始定义的 TermInfo

        Returns:
            TermInfo: 添加了 structured_definition 的 TermInfo
        """
        try:
            from agent.llm_client import get_llm_client

            llm_client = get_llm_client()
            if not llm_client:
                print("LLM client not available, skipping structured enhancement")
                return term_info

            messages = [
                {
                    "role": "system",
                    "content": """你是一位知识整理专家。请将以下关于概念的原始信息整理成结构化格式。

要求：
1. 核心定义：用一句话精炼概括（50字以内）
2. 关键特点：列出3-5个核心特点，每个特点一句话
3. 相关概念：列出2-3个相关概念

输出格式（严格按此格式）：
## 核心定义
[一句话精炼定义]

## 关键特点
- [特点1]
- [特点2]
- [特点3]

## 相关概念
- [概念1]
- [概念2]"""
                },
                {
                    "role": "user",
                    "content": f"""术语名称：{term_info.name}
原始定义：
{term_info.definition}

一句话描述：
{term_info.description}"""
                }
            ]

            response = llm_client.chat(messages)
            term_info.structured_definition = response.strip()
            return term_info

        except ImportError:
            print("LLM client module not available, skipping structured enhancement")
            return term_info
        except Exception as e:
            print(f"LLM structured enhancement failed: {e}")
            return term_info

    def fetch_and_enhance(self, term: str, language: str = "zh") -> Optional[TermInfo]:
        """
        获取术语信息并使用 LLM 结构化

        Args:
            term: 术语名称
            language: 语言偏好

        Returns:
            TermInfo: 结构化后的术语信息
        """
        term_info = self.fetch_term_info(term, language)
        if not term_info:
            return None

        return self.enhance_with_llm(term_info)
