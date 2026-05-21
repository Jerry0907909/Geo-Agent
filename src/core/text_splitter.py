"""Text Splitter - 基于 LangChain 的文本分割器

使用 LangChain RecursiveCharacterTextSplitter 实现中文文本分割。
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from langchain_text_splitters import RecursiveCharacterTextSplitter as LCTextSplitter
from langchain_core.documents import Document

from src.utils.config import get_config


class LangChainTextSplitter:
    """基于 LangChain 的文本分割器
    
    使用 LangChain RecursiveCharacterTextSplitter，
    针对中文文本优化分隔符配置。
    """

    def __init__(
        self,
        chunk_size: int = 2048,
        chunk_overlap: int = 256,
        separators: Optional[Sequence[str]] = None,
        length_function: callable = len,
        is_separator_regex: bool = False,
    ) -> None:
        """初始化文本分割器
        
        Args:
            chunk_size: 每个块的最大字符数
            chunk_overlap: 块之间的重叠字符数
            separators: 分隔符列表（按优先级排序）
            length_function: 计算文本长度的函数
            is_separator_regex: 分隔符是否为正则表达式
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be in [0, chunk_size)")

        # 中文优化的默认分隔符
        if separators is None:
            separators = [
                "\n\n",      # 段落
                "\n",        # 换行
                "。",        # 中文句号
                "！",        # 中文感叹号
                "？",        # 中文问号
                "；",        # 中文分号
                "，",        # 中文逗号
                "、",        # 中文顿号
                " ",         # 空格
                "",          # 字符级别
            ]

        self._splitter = LCTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=list(separators),
            length_function=length_function,
            is_separator_regex=is_separator_regex,
            keep_separator=True,
        )
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = list(separators)

    def split_text(self, text: str) -> List[str]:
        """将单个长文本切分为多个片段
        
        Args:
            text: 输入文本
            
        Returns:
            文本片段列表
        """
        if not text:
            return []
        return self._splitter.split_text(text)

    def split_documents(self, documents: Sequence[Document]) -> List[Document]:
        """对 Document 列表进行分割
        
        Args:
            documents: LangChain Document 列表
            
        Returns:
            分割后的 Document 列表
        """
        if not documents:
            return []
        
        # 使用 LangChain 的 split_documents 方法
        split_docs = self._splitter.split_documents(list(documents))
        
        # 添加 chunk_id 到 metadata
        for idx, doc in enumerate(split_docs):
            if "chunk_id" not in doc.metadata:
                doc.metadata["chunk_id"] = idx
        
        return split_docs

    def create_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[dict]] = None,
    ) -> List[Document]:
        """从文本列表创建并分割文档
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表（可选）
            
        Returns:
            分割后的 Document 列表
        """
        return self._splitter.create_documents(texts, metadatas)


# 保留旧类名作为别名
RecursiveCharacterTextSplitter = LangChainTextSplitter
TextSplitter = LangChainTextSplitter


def create_text_splitter() -> LangChainTextSplitter:
    """根据全局配置创建默认文本分割器"""
    config = get_config()
    rag_cfg = config.get_rag_config()
    txt_cfg = config.get_text_processing_config()

    chunk_size = int(rag_cfg.get("chunk_size", 1024))
    chunk_overlap = int(rag_cfg.get("chunk_overlap", 128))
    separators = txt_cfg.get("separators") or None

    return LangChainTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
    )
