"""
内容解析模块

支持从多种类型的兴趣点提取内容：
- PDF论文
- 新闻文章
- 公司信息
- 行业信息
- 问题/疑问
"""

from .base import BaseParser, ParseResult
from .factory import ParserFactory
from .pdf_parser import PDFParser
from .news_parser import NewsParser
from .company_parser import CompanyParser
from .industry_parser import IndustryParser
from .question_parser import QuestionParser

__all__ = [
    'BaseParser',
    'ParseResult',
    'ParserFactory',
    'PDFParser',
    'NewsParser',
    'CompanyParser',
    'IndustryParser',
    'QuestionParser',
]
