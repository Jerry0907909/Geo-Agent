"""Unified retrieval service for local, external, and hybrid evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from langchain_core.documents import Document

from src.core.llm_provider import create_llm_provider
from src.rag.prompt_templates import build_context_from_documents
from src.rag.retriever import create_rag_retriever
from src.tools.web_search import SearchResult, create_web_search_tool

RetrievalMode = Literal["local", "external", "hybrid"]


@dataclass
class UnifiedRetrievalResult:
    query: str
    retrieval_mode: RetrievalMode
    documents: List[Document] = field(default_factory=list)
    web_results: List[SearchResult] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    context: str = ""


class UnifiedRetrievalService:
    """Single retrieval entry for RAG endpoints and agent tools."""

    def __init__(self) -> None:
        self.local_retriever = create_rag_retriever()
        self.web_search_tool = create_web_search_tool()

    def retrieve(
        self,
        *,
        query: str,
        top_k: int,
        retrieval_mode: RetrievalMode = "local",
        min_relevance_score: float = 0.0,
        use_multi_query: bool = True,
    ) -> UnifiedRetrievalResult:
        local_docs: List[Document] = []
        web_results: List[SearchResult] = []

        if retrieval_mode in {"local", "hybrid"}:
            local_docs = self.local_retriever.retrieve(
                query,
                top_k=top_k if retrieval_mode == "local" else max(top_k, top_k * 2),
                min_relevance_score=min_relevance_score,
                use_multi_query=use_multi_query,
                search_all=True,
            )

        if retrieval_mode in {"external", "hybrid"}:
            web_results = self.web_search_tool.search(
                query,
                max_results=top_k if retrieval_mode == "external" else max(top_k, top_k * 2),
            )

        sources = self._merge_sources(local_docs, web_results, top_k, retrieval_mode)
        context = self._build_context(sources)

        result = UnifiedRetrievalResult(
            query=query,
            retrieval_mode=retrieval_mode,
            documents=local_docs,
            web_results=web_results,
            sources=sources,
            context=context,
        )
        return result

    def answer(
        self,
        *,
        query: str,
        top_k: int,
        retrieval_mode: RetrievalMode = "local",
        min_relevance_score: float = 0.0,
        answer_style: str | None = None,
    ) -> tuple[str, UnifiedRetrievalResult]:
        result = self.retrieve(
            query=query,
            top_k=top_k,
            retrieval_mode=retrieval_mode,
            min_relevance_score=min_relevance_score,
        )

        style = answer_style or "先给出直接结论，再给出依据，并尽量标注来源。"
        prompt = (
            "你是 Geo-Agent 的检索增强回答模块。"
            "你只能基于给定参考信息作答，不得编造来源。"
            "若信息不足，要明确说明不足。"
            "回答应为中文、简洁、专业，并区分本地文献和外部网页证据。\n\n"
            f"检索模式：{retrieval_mode}\n"
            f"用户问题：{query}\n"
            f"回答风格：{style}\n\n"
            f"参考信息：\n{result.context or '(未检索到相关参考信息)'}\n\n回答："
        )
        llm = create_llm_provider(temperature=0.2)
        answer = llm.generate(prompt)
        return answer, result

    @staticmethod
    def _normalize_local_source(doc: Document) -> Dict[str, Any]:
        metadata = {k: v for k, v in doc.metadata.items() if k not in {"page_content", "chroma_id"}}
        return {
            "content": doc.page_content,
            "source": doc.metadata.get("source", doc.metadata.get("file_name", "未知来源")),
            "relevance_score": doc.metadata.get("relevance_score"),
            "type": "document",
            "metadata": metadata,
        }

    @staticmethod
    def _normalize_web_source(result: SearchResult) -> Dict[str, Any]:
        return {
            "content": result.snippet,
            "source": result.title or result.url,
            "url": result.url,
            "relevance_score": result.relevance_score,
            "type": "web",
            "source_type": result.source_type,
            "metadata": {"publish_date": result.publish_date},
        }

    def _merge_sources(
        self,
        local_docs: List[Document],
        web_results: List[SearchResult],
        top_k: int,
        retrieval_mode: RetrievalMode,
    ) -> List[Dict[str, Any]]:
        if retrieval_mode == "local":
            return [self._normalize_local_source(doc) for doc in local_docs[:top_k]]
        if retrieval_mode == "external":
            return [self._normalize_web_source(result) for result in web_results[:top_k]]

        merged: List[Dict[str, Any]] = []
        local_sources = [self._normalize_local_source(doc) for doc in local_docs]
        web_sources = [self._normalize_web_source(result) for result in web_results]

        local_limit = max(1, top_k // 2)
        web_limit = max(1, top_k - local_limit)

        merged.extend(local_sources[:local_limit])
        merged.extend(web_sources[:web_limit])

        remainder = local_sources[local_limit:] + web_sources[web_limit:]
        seen: set[str] = set()
        deduped: List[Dict[str, Any]] = []
        for item in merged + remainder:
            key = f"{item.get('type')}::{item.get('source')}::{item.get('url', '')}::{str(item.get('content', ''))[:120]}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= top_k:
                break
        return deduped[:top_k]

    def _build_context(self, sources: List[Dict[str, Any]]) -> str:
        local_docs = [
            Document(page_content=str(source.get("content", "")), metadata=source.get("metadata", {}))
            for source in sources
            if source.get("type") == "document"
        ]
        local_context = build_context_from_documents(local_docs) if local_docs else ""

        web_parts: List[str] = []
        web_index = 1
        for source in sources:
            if source.get("type") != "web":
                continue
            source_label = {
                "academic": "学术",
                "official": "官方",
                "news": "新闻",
                "general": "网络",
            }.get(source.get("source_type"), "网络")
            web_parts.append(
                f"【外部来源{web_index} - {source_label}】\n"
                f"标题：{source.get('source', '未知来源')}\n"
                f"内容：{source.get('content', '')}\n"
                f"链接：{source.get('url', '')}"
            )
            web_index += 1

        if local_context and web_parts:
            return f"## 本地知识库证据\n{local_context}\n\n## 外部网页证据\n" + "\n\n".join(web_parts)
        if local_context:
            return local_context
        if web_parts:
            return "\n\n".join(web_parts)
        return ""


def create_unified_retrieval_service() -> UnifiedRetrievalService:
    return UnifiedRetrievalService()
