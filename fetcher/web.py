"""
网页抓取模块
"""

import re
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from dataclasses import dataclass


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    content: str
    source: str
    relevance: float = 1.0


class WebFetcher:
    """网页抓取器"""

    def __init__(self):
        self.session_timeout = 10

    def fetch(self, url: str) -> Optional[Dict[str, Any]]:
        """
        获取网页内容

        Returns:
            dict: {title, content, url, source}
        """
        try:
            import requests

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=self.session_timeout)
            response.raise_for_status()

            # 解析HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取标题
            title = soup.title.string if soup.title else ""
            if not title:
                h1 = soup.find('h1')
                title = h1.get_text(strip=True) if h1 else ""

            # 去除脚本和样式
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()

            # 提取正文
            content = soup.get_text(separator='\n', strip=True)
            # 清理空白
            content = re.sub(r'\n{3,}', '\n\n', content)

            # 提取域名作为来源
            parsed = urlparse(url)
            source = parsed.netloc

            return {
                "title": title,
                "content": content,
                "url": url,
                "source": source
            }

        except Exception as e:
            print(f"获取网页失败: {e}")
            return None

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        搜索网页

        使用DuckDuckGo API或HTML搜索
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            # 使用DuckDuckGo HTML搜索
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query}

            response = requests.post(url, data=data, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            results = []
            for result in soup.select('.result')[:max_results]:
                title_elem = result.select_one('.result__title')
                snippet_elem = result.select_one('.result__snippet')
                link_elem = result.select_one('a.result__a')

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link = link_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    # 提取真实URL
                    real_url = self._extract_url(link)

                    results.append(SearchResult(
                        title=title,
                        url=real_url,
                        content=snippet,
                        source=urlparse(real_url).netloc
                    ))

            return results

        except Exception as e:
            print(f"搜索失败: {e}")
            return []

    def _extract_url(self, ddg_url: str) -> str:
        """从DuckDuckGo链接提取真实URL"""
        match = re.search(r'uddg=([^&]+)', ddg_url)
        if match:
            import urllib.parse
            return urllib.parse.unquote(match.group(1))
        return ddg_url


class FallbackFetcher:
    """降级获取器 - 当网络不可用时使用"""

    def __init__(self):
        self.cache: Dict[str, str] = {}

    def get_cached(self, key: str) -> Optional[str]:
        """获取缓存"""
        return self.cache.get(key)

    def set_cached(self, key: str, content: str):
        """设置缓存"""
        self.cache[key] = content
