"""
新闻解析器
"""

import re
from typing import Optional

from .base import BaseParser, ParseResult


class NewsParser(BaseParser):
    """新闻文章解析器"""

    source_type = "news"

    def parse(self, input_source: str) -> ParseResult:
        """
        解析新闻内容

        Args:
            input_source: URL或新闻文本

        Returns:
            ParseResult: 解析结果
        """
        if not self.validate_input(input_source):
            raise ValueError("无效的输入")

        # 判断是URL还是文本
        if self._is_url(input_source):
            return self._parse_url(input_source)
        else:
            return self._parse_text(input_source)

    def _is_url(self, text: str) -> bool:
        """判断是否为URL"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(text.strip()))

    def _parse_url(self, url: str) -> ParseResult:
        """从URL解析新闻"""
        # 尝试获取网页内容
        content = self._fetch_content(url)

        # 提取标题和正文
        title = self._extract_title(content) or "新闻文章"
        body = self._extract_body(content)

        return ParseResult(
            source_type=self.source_type,
            title=title,
            content=body,
            metadata={
                "url": url,
                "source": self._extract_domain(url),
            }
        )

    def _parse_text(self, text: str) -> ParseResult:
        """解析文本内容"""
        lines = text.strip().split('\n')

        # 尝试提取标题（第一行或包含标题的行）
        title = lines[0] if lines else "新闻内容"
        content = text

        # 如果有多行，可能第一行是标题
        if len(lines) > 1:
            # 检查第一行是否像标题
            if len(lines[0]) < 100 and not lines[0].endswith(('.', '!', '?')):
                title = lines[0]
                content = '\n'.join(lines[1:])

        return ParseResult(
            source_type=self.source_type,
            title=title,
            content=content,
            metadata={}
        )

    def _fetch_content(self, url: str) -> str:
        """获取网页内容"""
        try:
            import requests

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            return response.text

        except ImportError:
            raise RuntimeError("请安装requests库: pip install requests")
        except Exception as e:
            raise RuntimeError(f"获取网页内容失败: {e}")

    def _extract_title(self, html: str) -> Optional[str]:
        """从HTML提取标题"""
        import re

        # 尝试多种标题标签
        patterns = [
            r'<title[^>]*>([^<]+)</title>',
            r'<h1[^>]*>([^<]+)</h1>',
            r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_body(self, html: str) -> str:
        """从HTML提取正文"""
        import re
        from html import unescape

        # 移除脚本和样式
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # 尝试获取article或main内容
        article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
        if article_match:
            html = article_match.group(1)
        else:
            main_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
            if main_match:
                html = main_match.group(1)

        # 移除HTML标签，保留文本
        text = re.sub(r'<[^>]+>', ' ', html)
        text = unescape(text)

        # 清理空白
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _extract_domain(self, url: str) -> str:
        """提取域名"""
        match = re.search(r'https?://([^/]+)', url)
        return match.group(1) if match else ""
