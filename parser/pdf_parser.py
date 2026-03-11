"""
PDF论文解析器
"""

from pathlib import Path
from typing import Optional
import subprocess

from .base import BaseParser, ParseResult


class PDFParser(BaseParser):
    """PDF论文解析器"""

    source_type = "paper"

    def __init__(self):
        self._pdf_extractor = None

    def parse(self, file_path: str) -> ParseResult:
        """
        解析PDF文件

        Args:
            file_path: PDF文件路径

        Returns:
            ParseResult: 解析结果
        """
        if not self.validate_input(file_path):
            raise ValueError("无效的PDF文件路径")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if path.suffix.lower() != '.pdf':
            raise ValueError("不是PDF文件")

        # 尝试使用PyMuPDF或pdfplumber提取文本
        content = self._extract_text(file_path)

        # 提取标题（从文件名或第一行）
        title = path.stem
        if content:
            first_lines = content.split('\n')[:5]
            for line in first_lines:
                if len(line) > 10 and len(line) < 200:
                    title = line.strip()
                    break

        return ParseResult(
            source_type=self.source_type,
            title=title,
            content=content,
            metadata={
                "file_path": str(path.absolute()),
                "file_size": path.stat().st_size,
            }
        )

    def _extract_text(self, file_path: str) -> str:
        """
        提取PDF文本

        尝试多种提取方法
        """
        # 方法1: 尝试使用PyMuPDF
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            if text.strip():
                return self.preprocess(text)
        except ImportError:
            pass
        except Exception:
            pass

        # 方法2: 尝试使用pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
            if text.strip():
                return self.preprocess(text)
        except ImportError:
            pass
        except Exception:
            pass

        # 方法3: 尝试使用pdftotext命令
        try:
            result = subprocess.run(
                ['pdftotext', '-layout', file_path, '-'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout:
                return self.preprocess(result.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 方法4: 尝试使用OCR
        try:
            return self._extract_with_ocr(file_path)
        except Exception:
            pass

        raise RuntimeError(
            "无法提取PDF内容。请安装PyMuPDF、pdfplumber或pdftotext：\n"
            "pip install pymupdf pdfplumber"
        )

    def _extract_with_ocr(self, file_path: str) -> str:
        """使用OCR提取文本"""
        try:
            import pdf2image
            import pytesseract

            # 将PDF转为图片
            images = pdf2image.convert_from_path(file_path)

            # OCR识别
            text = ""
            for image in images:
                text += pytesseract.image_to_string(image, lang='chi_sim+eng')

            return self.preprocess(text)
        except ImportError:
            raise RuntimeError("OCR需要安装: pip install pdf2image pytesseract")
