from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from src.core.document_loader import DocumentLoader, create_document_loader
from src.core.text_splitter import TextSplitter, create_text_splitter
from src.database.chroma_manager import ChromaManager, create_chroma_manager
from src.rag.retriever import RAGResult, RAGRetriever, create_rag_retriever


@dataclass
class IndexStats:
    """索引构建统计信息"""

    num_source_documents: int
    num_chunks: int


class RAGChain:
    """RAG 链式处理

    职责：
    - 构建 / 重建向量索引（加载文献 -> 分割 -> 写入 Chroma）
    - 通过 RAGRetriever 执行查询
    """

    def __init__(
        self,
        retriever: RAGRetriever,
        vector_store: ChromaManager,
        document_loader: Optional[DocumentLoader] = None,
        text_splitter: Optional[TextSplitter] = None,
    ) -> None:
        self.retriever = retriever
        self.vector_store = vector_store
        self.document_loader = document_loader or create_document_loader()
        self.text_splitter = text_splitter or create_text_splitter()

    def build_index(self, rebuild: bool = False) -> IndexStats:
        """构建或重建向量索引

        Args:
            rebuild: 为 True 时使用增量更新，删除并重新添加已存在的文档
        Returns:
            IndexStats: 包含源文档数量和切分后 chunk 数量
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 1. 加载文献
        documents = self.document_loader.load()
        logger.info(f"[索引构建] 加载了 {len(documents)} 个文档")

        # 2. 文本分割
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"[索引构建] 分割为 {len(chunks)} 个片段")
        
        # 3. 增量更新：删除并重新添加
        if rebuild and chunks:
            # 获取所有新文档的来源名称
            new_sources = set()
            for chunk in chunks:
                source = chunk.metadata.get('source') or chunk.metadata.get('file_name')
                if source:
                    new_sources.add(source)
            
            logger.info(f"[索引构建] 新文档来源: {new_sources}")
            
            # 删除这些来源的旧数据
            for source in new_sources:
                try:
                    result = self.vector_store.collection.get(
                        where={"$or": [
                            {"source": source},
                            {"file_name": source}
                        ]}
                    )
                    ids_to_delete = result.get("ids", [])
                    if ids_to_delete:
                        self.vector_store.delete(ids_to_delete)
                        logger.info(f"[索引构建] 删除了 {source} 的 {len(ids_to_delete)} 个旧片段")
                except Exception as e:
                    logger.warning(f"[索引构建] 删除 {source} 失败: {e}")
        
        # 4. 添加新文档
        if chunks:
            self.vector_store.add_documents(chunks)
            logger.info(f"[索引构建] 添加了 {len(chunks)} 个新片段")

        return IndexStats(
            num_source_documents=len(documents),
            num_chunks=len(chunks),
        )

    def query(self, question: str, top_k: Optional[int] = None, user_id: Optional[str] = None) -> RAGResult:
        """执行一次完整的 RAG 查询"""
        return self.retriever.run(question=question, top_k=top_k, user_id=user_id)


def create_rag_chain(user_llm_config: Optional[dict] = None) -> RAGChain:
    """根据默认配置创建完整的 RAGChain"""

    vector_store = create_chroma_manager()
    retriever = create_rag_retriever(user_llm_config=user_llm_config)
    return RAGChain(
        retriever=retriever,
        vector_store=vector_store,
    )
