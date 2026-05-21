"""Chroma Manager - 基于 LangChain 的向量数据库管理器

使用 LangChain Chroma 实现向量存储和检索。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.core.embedding_provider import create_embedding_provider
from src.utils.config import get_config

logger = logging.getLogger(__name__)

# 全局 Chroma 客户端（单例）
_chroma_client: Optional[chromadb.PersistentClient] = None
_chroma_client_path: Optional[str] = None


def get_chroma_client(persist_directory: Optional[str] = None) -> chromadb.PersistentClient:
    """获取全局 Chroma 客户端（单例模式）
    
    Args:
        persist_directory: 持久化目录
        
    Returns:
        Chroma PersistentClient 实例
    """
    global _chroma_client, _chroma_client_path
    
    config = get_config()
    chroma_cfg = config.get_chroma_config()
    
    if persist_directory is None:
        persist_directory = chroma_cfg.get("persist_directory", "./data/chroma_db")
    
    # 如果客户端不存在或路径不同，创建新客户端
    if _chroma_client is None or _chroma_client_path != persist_directory:
        _chroma_client = chromadb.PersistentClient(
            path=str(persist_directory),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
        _chroma_client_path = persist_directory
        logger.info(f"[ChromaManager] 创建全局 Chroma 客户端: {persist_directory}")
    
    return _chroma_client


class ChromaManager:
    """基于 LangChain Chroma 的向量库管理器
    
    使用 LangChain Chroma 封装，提供：
    - 文档添加和删除
    - 相似度检索
    - 多样性检索
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
        embedding_provider: Optional[Embeddings] = None,
        similarity_threshold: Optional[float] = None,
        default_top_k: int = 5,
    ) -> None:
        """初始化 Chroma 管理器
        
        Args:
            collection_name: 集合名称
            persist_directory: 持久化目录
            embedding_provider: Embedding 提供者
            similarity_threshold: 相似度阈值
            default_top_k: 默认返回数量
        """
        config = get_config()
        chroma_cfg = config.get_chroma_config()
        rag_cfg = config.get_rag_config()

        if collection_name is None:
            collection_name = chroma_cfg.get("collection_name", "geology_literature")
        if persist_directory is None:
            persist_directory = chroma_cfg.get("persist_directory", "./data/chroma_db")

        if similarity_threshold is None:
            similarity_threshold = rag_cfg.get("similarity_threshold")
        self._similarity_threshold = similarity_threshold
        self._default_top_k = int(rag_cfg.get("top_k", default_top_k))

        if embedding_provider is None:
            embedding_provider = create_embedding_provider()
        
        self._embedding_provider = embedding_provider
        self._collection_name = collection_name
        self._persist_directory = persist_directory

        # 获取全局 Chroma 客户端
        client = get_chroma_client(persist_directory)
        
        # 创建 LangChain Chroma 实例，使用共享客户端
        self._vectorstore = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embedding_provider,
        )
        
        logger.info(f"[ChromaManager] 初始化完成: collection={collection_name}, persist_dir={persist_directory}")

    @property
    def vectorstore(self) -> Chroma:
        """获取底层 LangChain Chroma 实例"""
        return self._vectorstore

    @property
    def collection(self):
        """获取底层 Chroma Collection（兼容旧接口）"""
        return self._vectorstore._collection

    def add_documents(
        self,
        documents: Sequence[Document],
        ids: Optional[Sequence[str]] = None,
        batch_size: int = 32,
    ) -> List[str]:
        """向向量库中添加文档
        
        Args:
            documents: LangChain Document 列表
            ids: 可选的自定义 ID 列表
            batch_size: 批处理大小，避免超过 embedding 限制
            
        Returns:
            实际写入的文档 ID 列表
        """
        if not documents:
            return []

        if ids is None:
            ids = [str(uuid4()) for _ in documents]

        id_list = list(ids)
        doc_list = list(documents)
        all_ids = []
        
        # 分批处理，避免超过 embedding batch size 限制
        for i in range(0, len(doc_list), batch_size):
            batch_docs = doc_list[i:i + batch_size]
            batch_ids = id_list[i:i + batch_size]
            
            # 使用 LangChain Chroma 的 add_documents 方法
            self._vectorstore.add_documents(
                documents=batch_docs,
                ids=batch_ids,
            )
            all_ids.extend(batch_ids)
            logger.info(f"[ChromaManager] 批次 {i // batch_size + 1}: 添加了 {len(batch_docs)} 个文档")
        
        logger.info(f"[ChromaManager] 总共添加了 {len(all_ids)} 个文档")
        return all_ids

    def add_texts(
        self,
        texts: Sequence[str],
        metadatas: Optional[Sequence[Dict[str, Any]]] = None,
        ids: Optional[Sequence[str]] = None,
    ) -> List[str]:
        """直接添加纯文本
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
            ids: ID 列表
            
        Returns:
            文档 ID 列表
        """
        if not texts:
            return []
        
        if ids is None:
            ids = [str(uuid4()) for _ in texts]
        
        # 使用 LangChain Chroma 的 add_texts 方法
        return self._vectorstore.add_texts(
            texts=list(texts),
            metadatas=list(metadatas) if metadatas else None,
            ids=list(ids),
        )

    def similarity_search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """相似度检索

        Args:
            query: 查询文本
            top_k: 返回数量
            filter: ChromaDB where 过滤条件

        Returns:
            Document 列表（包含相似度分数）
        """
        if not query:
            return []

        n_results = int(top_k or self._default_top_k)

        logger.info(f"[ChromaManager] 检索: query='{query[:50]}...', top_k={n_results}, collection={self._collection_name}, filter={filter}")

        # 使用 similarity_search_with_score 获取分数
        results = self._vectorstore.similarity_search_with_score(
            query=query,
            k=n_results,
            filter=filter,
        )
        
        documents: List[Document] = []
        for doc, distance in results:
            # 将距离转换为相似度分数 (cosine: similarity = 1 - distance)
            similarity = max(0.0, 1.0 - distance)
            
            # 应用相似度阈值过滤
            if self._similarity_threshold is not None:
                if similarity < self._similarity_threshold:
                    continue
            
            # 添加分数到 metadata
            doc.metadata["relevance_score"] = round(similarity, 4)
            doc.metadata["distance"] = round(distance, 4)
            doc.metadata["collection"] = self._collection_name
            documents.append(doc)
        
        logger.info(f"[ChromaManager] 检索结果: {len(documents)} 个文档")
        return documents


def search_all_collections(
    query: str,
    top_k: int = 5,
    persist_directory: Optional[str] = None,
    filter: Optional[Dict[str, Any]] = None,
    allowed_collections: Optional[List[str]] = None,
) -> List[Document]:
    """跨知识库搜索

    Args:
        query: 查询文本
        top_k: 每个集合返回的数量
        persist_directory: Chroma 持久化目录
        filter: ChromaDB where 过滤条件
        allowed_collections: 限定搜索的集合名列表

    Returns:
        合并后的 Document 列表（按相关度排序）
    """
    all_docs: List[Document] = []
    collections = allowed_collections if allowed_collections is not None else list_all_collections(persist_directory)

    logger.info(f"[跨库搜索] 搜索 {len(collections)} 个知识库: {collections}")

    for coll_name in collections:
        try:
            manager = ChromaManager(collection_name=coll_name, persist_directory=persist_directory)
            docs = manager.similarity_search(query, top_k=top_k, filter=filter)
            all_docs.extend(docs)
            logger.info(f"[跨库搜索] {coll_name}: 找到 {len(docs)} 个文档")
        except Exception as e:
            logger.warning(f"[跨库搜索] 搜索 {coll_name} 失败: {e}")
            continue

    # 按相关度排序
    all_docs.sort(key=lambda d: d.metadata.get("relevance_score", 0), reverse=True)

    # 返回 top_k 个结果
    return all_docs[:top_k]

    def similarity_search_with_score(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[tuple[Document, float]]:
        """带分数的相似度检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            (Document, score) 元组列表
        """
        if not query:
            return []

        n_results = int(top_k or self._default_top_k)
        
        return self._vectorstore.similarity_search_with_score(
            query=query,
            k=n_results,
        )

    def similarity_search_with_diversity(
        self,
        query: str,
        top_k: Optional[int] = None,
        max_per_source: int = 2,
        fetch_k_multiplier: int = 3,
    ) -> List[Document]:
        """带多样性的相似度检索（MMR）
        
        Args:
            query: 查询文本
            top_k: 最终返回数量
            max_per_source: 每个来源最多返回数量
            fetch_k_multiplier: 初始检索倍数
            
        Returns:
            多样化的 Document 列表
        """
        if not query:
            return []
        
        n_results = int(top_k or self._default_top_k)
        fetch_k = n_results * fetch_k_multiplier
        
        logger.info(f"[ChromaManager] MMR检索: top_k={n_results}, fetch_k={fetch_k}")
        
        # 使用 LangChain 的 max_marginal_relevance_search
        try:
            results = self._vectorstore.max_marginal_relevance_search(
                query=query,
                k=n_results,
                fetch_k=fetch_k,
                lambda_mult=0.5,  # 多样性参数
            )
        except Exception as e:
            logger.warning(f"MMR 检索失败，回退到普通检索: {e}")
            return self.similarity_search(query, top_k)
        
        # 按来源限制数量
        source_count: Dict[str, int] = {}
        filtered_docs: List[Document] = []
        
        for doc in results:
            source = doc.metadata.get("source", doc.metadata.get("file_name", "unknown"))
            
            if source_count.get(source, 0) >= max_per_source:
                continue
            source_count[source] = source_count.get(source, 0) + 1
            filtered_docs.append(doc)
        
        logger.info(f"[ChromaManager] MMR结果: {len(filtered_docs)} 文档, 来源: {dict(source_count)}")
        return filtered_docs

    def delete(self, ids: Sequence[str]) -> None:
        """按 ID 删除文档
        
        Args:
            ids: 要删除的文档 ID 列表
        """
        if not ids:
            return
        
        try:
            # 尝试使用 vectorstore 的 delete 方法
            if hasattr(self._vectorstore, 'delete'):
                self._vectorstore.delete(ids=list(ids))
            else:
                # 如果 vectorstore 没有 delete 方法，使用 collection 的原生方法
                self._vectorstore._collection.delete(ids=list(ids))
            
            logger.info(f"[ChromaManager] 删除了 {len(ids)} 个文档")
        except Exception as e:
            logger.error(f"[ChromaManager] 删除失败: {e}", exc_info=True)
            raise

    def delete_by_filter(self, filter_dict: Dict[str, Any]) -> int:
        """按条件删除文档
        
        Args:
            filter_dict: 过滤条件
            
        Returns:
            删除的文档数量
        """
        try:
            logger.info(f"[ChromaManager] 尝试删除，过滤条件: {filter_dict}")
            
            # 先查询匹配的文档
            result = self.collection.get(where=filter_dict)
            ids_to_delete = result.get("ids", [])
            
            logger.info(f"[ChromaManager] 找到 {len(ids_to_delete)} 个匹配的文档")
            
            if ids_to_delete:
                # 打印前几个匹配的文档信息
                metadatas = result.get("metadatas", [])
                if metadatas:
                    logger.info(f"[ChromaManager] 匹配的文档示例: {metadatas[:3]}")
                
                # 使用 collection 的原生删除方法
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"[ChromaManager] 成功删除 {len(ids_to_delete)} 个文档")
                return len(ids_to_delete)
            
            logger.warning(f"[ChromaManager] 未找到匹配的文档")
            return 0
            
        except Exception as e:
            logger.error(f"[ChromaManager] 按条件删除失败: {e}", exc_info=True)
            return 0

    def reset_collection(self) -> None:
        """清空当前集合中的所有数据"""
        try:
            result = self.collection.get()
            raw_ids = result.get("ids") or []
            
            if not raw_ids:
                return
            
            # 处理可能的嵌套列表
            all_ids: List[str] = []
            if isinstance(raw_ids[0], str):
                all_ids = list(raw_ids)
            else:
                for group in raw_ids:
                    all_ids.extend(group)
            
            if all_ids:
                unique_ids = list(dict.fromkeys(all_ids))
                self.delete(unique_ids)
                logger.info(f"[ChromaManager] 清空集合，删除了 {len(unique_ids)} 个文档")
                
        except Exception as e:
            logger.error(f"清空集合失败: {e}")

    def get_retriever(self, search_kwargs: Optional[Dict] = None):
        """获取 LangChain Retriever
        
        Args:
            search_kwargs: 检索参数
            
        Returns:
            LangChain VectorStoreRetriever
        """
        kwargs = search_kwargs or {"k": self._default_top_k}
        return self._vectorstore.as_retriever(search_kwargs=kwargs)

    def count(self) -> int:
        """获取文档数量"""
        return self.collection.count()


def create_chroma_manager(collection_name: Optional[str] = None) -> ChromaManager:
    """根据全局配置创建默认的 ChromaManager 实例
    
    Args:
        collection_name: 可选的集合名称
        
    Returns:
        ChromaManager 实例
    """
    return ChromaManager(collection_name=collection_name)


def list_all_collections(persist_directory: Optional[str] = None) -> List[str]:
    """列出向量库中的所有集合名称
    
    Args:
        persist_directory: Chroma 持久化目录
        
    Returns:
        集合名称列表
    """
    # 使用全局客户端
    client = get_chroma_client(persist_directory)
    
    collections = client.list_collections()
    return [c.name for c in collections]
