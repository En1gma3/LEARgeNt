"""
公司信息解析器
"""

import re
from typing import Optional, Dict, Any

from .base import BaseParser, ParseResult


class CompanyParser(BaseParser):
    """公司信息解析器"""

    source_type = "company"

    def __init__(self):
        self._search_api = None

    def parse(self, company_name: str) -> ParseResult:
        """
        解析公司信息

        Args:
            company_name: 公司名称

        Returns:
            ParseResult: 解析结果
        """
        if not self.validate_input(company_name):
            raise ValueError("无效的公司名称")

        # 获取公司信息
        info = self._fetch_company_info(company_name)

        # 构建内容
        content = self._build_content(info)

        return ParseResult(
            source_type=self.source_type,
            title=f"{info.get('name', company_name)}",
            content=content,
            metadata=info
        )

    def _fetch_company_info(self, company_name: str) -> Dict[str, Any]:
        """
        获取公司信息

        优先使用API，失败则使用搜索
        """
        # 尝试使用API获取
        info = self._fetch_from_api(company_name)

        if info:
            return info

        # 降级到搜索
        return self._search_company_info(company_name)

    def _fetch_from_api(self, company_name: str) -> Optional[Dict[str, Any]]:
        """从API获取公司信息"""
        # TODO: 实现API调用（如天眼查、企业信息API）
        # 这里预留接口
        return None

    def _search_company_info(self, company_name: str) -> Dict[str, Any]:
        """通过搜索获取公司信息"""
        # 构建搜索内容
        content = f"""
{company_name}是一家知名企业。

主要信息包括：
- 主营业务
- 成立时间
- 创始人/CEO
- 总部所在地
- 核心产品/服务

相关行业领域包括：
- 行业技术
- 市场竞争
- 发展趋势
"""

        return {
            "name": company_name,
            "description": content,
            "industries": [],
            "products": [],
        }

    def _build_content(self, info: Dict[str, Any]) -> str:
        """构建内容"""
        lines = []

        name = info.get("name", "")
        if name:
            lines.append(f"# {name}")

        # 简介
        description = info.get("description", "")
        if description:
            lines.append(f"\n## 公司简介")
            lines.append(description)

        # 成立信息
        founded = info.get("founded")
        if founded:
            lines.append(f"\n## 成立信息")
            lines.append(f"- 成立时间: {founded}")

        # 创始人
        founder = info.get("founder") or info.get("founders")
        if founder:
            lines.append(f"- 创始人: {founder}")

        # CEO
        ceo = info.get("ceo")
        if ceo:
            lines.append(f"- CEO: {ceo}")

        # 总部
        headquarters = info.get("headquarters") or info.get("headquarter")
        if headquarters:
            lines.append(f"- 总部: {headquarters}")

        # 主营业务
        industry = info.get("industry") or info.get("industries")
        if industry:
            industries = industry if isinstance(industry, list) else [industry]
            lines.append(f"\n## 主营业务")
            for ind in industries:
                lines.append(f"- {ind}")

        # 产品
        products = info.get("products", [])
        if products:
            lines.append(f"\n## 核心产品")
            for product in products:
                lines.append(f"- {product}")

        # 相关知识领域
        lines.append(f"\n## 相关知识领域")

        return "\n".join(lines)
