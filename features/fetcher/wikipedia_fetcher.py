"""
Wikipedia 获取器

从 Wikipedia API 获取术语定义和摘要
"""

import requests
from typing import Optional
from urllib.parse import quote

from .base import BaseFetcher, TermInfo


class WikipediaFetcher(BaseFetcher):
    """Wikipedia 信息获取器"""

    def __init__(self):
        self._available = None  # 缓存可用性检查结果

    def is_available(self) -> bool:
        """检查 Wikipedia API 是否可用"""
        if self._available is not None:
            return self._available

        try:
            # 简单的连通性检查
            response = requests.get(
                "https://zh.wikipedia.org/api/rest_v1/page/summary/Test",
                headers=self._get_headers(),
                timeout=5
            )
            self._available = response.status_code != 403
        except Exception:
            self._available = False

        return self._available

    def fetch(self, term: str, language: str = "zh") -> Optional[TermInfo]:
        """
        从 Wikipedia 获取术语信息

        Args:
            term: 术语名称
            language: 语言偏好 (zh, en)

        Returns:
            TermInfo: 术语信息
        """
        if not self.is_available():
            return None

        # 确定使用的语言
        if language == "en":
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(term)}"
            source_name = "Wikipedia (EN)"
        else:
            wiki_url = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{quote(term)}"
            source_name = "维基百科"

        try:
            response = requests.get(
                wiki_url,
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code != 200:
                # 如果中文没找到，尝试英文
                if language == "zh":
                    return self.fetch(term, language="en")
                return None

            data = response.json()
            return self._parse_response(data, source_name, language)

        except requests.exceptions.Timeout:
            print(f"Wikipedia API 超时: {term}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Wikipedia API 请求失败: {e}")
            return None
        except Exception as e:
            print(f"Wikipedia 获取失败: {e}")
            return None

    def _get_headers(self) -> dict:
        """获取请求头"""
        return {
            "User-Agent": "LearnMate/0.3.0 (CLI Learning Assistant; https://github.com/En1gma3/LEARgeNt)",
            "Accept": "application/json",
        }

    def _parse_response(self, data: dict, source_name: str, language: str) -> TermInfo:
        """解析 Wikipedia API 响应"""
        # 获取内容URL
        content_urls = data.get("content_urls", {})
        desktop_url = content_urls.get("desktop", {}).get("page", "")

        return TermInfo(
            name=data.get("title", ""),
            definition=data.get("extract", ""),
            summary=data.get("extract", "")[:200] if data.get("extract") else "",
            description=data.get("description", ""),
            source=source_name,
            url=desktop_url,
            language=language,
            raw_data=data,
        )
