"""PDF 文件解析工具"""

import logging
from typing import Union
from io import BytesIO

logger = logging.getLogger(__name__)


def parse_pdf_content(content: Union[bytes, str]) -> str:
    """解析 PDF 文件内容
    
    Args:
        content: PDF 文件内容（bytes）或文件路径（str）
        
    Returns:
        提取的文本内容
    """
    try:
        import fitz  # PyMuPDF
        
        if isinstance(content, str):
            # 文件路径
            doc = fitz.open(content)
        else:
            # bytes 内容
            doc = fitz.open(stream=content, filetype="pdf")
        
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        
        doc.close()
        return "\n".join(text_parts)
        
    except ImportError:
        logger.warning("PyMuPDF 未安装，尝试使用 pypdf")
        try:
            from pypdf import PdfReader
            
            if isinstance(content, str):
                reader = PdfReader(content)
            else:
                reader = PdfReader(BytesIO(content))
            
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            
            return "\n".join(text_parts)
            
        except ImportError:
            logger.error("pypdf 也未安装，无法解析 PDF")
            raise ImportError("请安装 PyMuPDF 或 pypdf: pip install pymupdf pypdf")
    
    except Exception as e:
        logger.error(f"PDF 解析失败: {e}")
        raise
