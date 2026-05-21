"""
搜索编排器 — 统一混合检索入口

流程:
1. 意图识别 → 决定是否启用联网、检索策略
2. 并行执行: 向量检索 + BM25关键词检索 + (可选)Web实时搜索
3. RRF / 加权融合 + 重排序
4. 上下文注入与 LLM 生成

三个检索源并行 → 融合 → 重排 → 生成，整条链路可观测。
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Iterator, AsyncIterator

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


# ---------------- 意图分类 ----------------

@dataclass
class SearchIntent:
    label: str                    # "static" | "time_sensitive" | "document_lookup" | "mixed"
    needs_web: bool
    needs_knowledge_base: bool
    time_range: Optional[str] = None
    topic: Optional[str] = None
    confidence: float = 0.5

INTENT_RULES = [
    # (keywords 列表, intent_label, needs_web, needs_kb)
    (["今天", "今日", "刚刚", "最新", "本周", "本月", "今年", "新闻",
      "快讯", "热点", "突发", "实时", "现在", "当前"], "time_sensitive", True, True),
    (["进展", "趋势", "发展", "现状", "目前", "最近", "近期",
      "2025", "2026", "2027"], "time_sensitive", True, True),
    (["文档", "文献", "知识库", "上传", "我的", "资料"], "document_lookup", False, True),
    (["搜索", "查一下", "帮我找", "有什么", "什么是", "如何",
      "怎么", "为什么", "介绍一下"], "mixed", True, True),
]


def classify_intent(query: str) -> SearchIntent:
    """轻度意图分类（关键词启发式，零延迟）"""
    q = query.lower()

    for keywords, label, needs_web, needs_kb in INTENT_RULES:
        hits = sum(1 for kw in keywords if kw in q)
        if hits >= 2:
            return SearchIntent(label=label, needs_web=needs_web, needs_knowledge_base=needs_kb, confidence=0.8)
        if hits == 1 and label == "time_sensitive":
            return SearchIntent(label="time_sensitive", needs_web=True, needs_knowledge_base=True, confidence=0.6)

    # 默认: mixed — 知识库 + web
    return SearchIntent(label="mixed", needs_web=True, needs_knowledge_base=True, confidence=0.4)


# ---------------- 编排结果 ----------------

@dataclass
class OrchestratedResult:
    answer: str
    kb_documents: List[Document] = field(default_factory=list)
    web_results: List[Any] = field(default_factory=list)
    fusion_sources: List[Dict[str, Any]] = field(default_factory=list)
    intent: Optional[SearchIntent] = None
    retrieval_time_ms: int = 0
    generation_time_ms: int = 0


# ---------------- 编排器 ----------------

class SearchOrchestrator:
    """搜索编排器: 意图识别 → 并行检索 → 融合重排 → 生成"""

    def __init__(
        self,
        kb_retriever,          # RAGRetriever / WebEnhancedRAGRetriever
        web_search_tool,       # WebSearchTool
        llm_provider,          # LLMProvider
        use_reranker: bool = True,
    ):
        self.kb_retriever = kb_retriever
        self.web_search_tool = web_search_tool
        self.llm_provider = llm_provider
        self.use_reranker = use_reranker

    # ---------- 异步编排入口 ----------

    async def execute(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        top_k: int = 5,
        enable_web: bool = True,
        enable_kb: bool = True,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> OrchestratedResult:
        t0 = time.time()

        # 1. 意图识别
        intent = classify_intent(query)
        logger.info("[编排器] 意图: %s (web=%s kb=%s confidence=%.2f)",
                    intent.label, intent.needs_web, intent.needs_knowledge_base, intent.confidence)

        # 2. 并行检索
        web_override = enable_web and intent.needs_web
        kb_override = enable_kb and intent.needs_knowledge_base

        kb_task = self._run_kb_search(query, top_k, user_id) if kb_override else None
        web_task = self._run_web_search(query) if web_override else None

        kb_docs = []
        web_results = []

        if kb_task and web_task:
            kb_docs, web_results = await asyncio.gather(kb_task, web_task)
        elif kb_task:
            kb_docs = await kb_task
        elif web_task:
            web_results = await web_task

        t_retrieval = int((time.time() - t0) * 1000)

        # 3. 融合 & 去重
        fusion_sources = self._fuse_sources(kb_docs, web_results)

        # 4. 构建上下文 + 生成
        context = self._build_context(fusion_sources)
        prompt_template = self._build_prompt(system_prompt, kb_docs, web_results)

        # 5. LLM 生成
        t_gen_start = time.time()
        llm = self.llm_provider.get_langchain_llm()
        if temperature is not None:
            from src.core.llm_provider import create_llm_provider
            llm = create_llm_provider(temperature=temperature).get_langchain_llm()

        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        chain = prompt_template | llm | StrOutputParser()
        answer = await chain.ainvoke({"context": context, "question": query})

        t_generation = int((time.time() - t_gen_start) * 1000)
        logger.info("[编排器] 检索 %dms + 生成 %dms = %dms (kb=%d web=%d sources=%d)",
                    t_retrieval, t_generation, t_retrieval + t_generation,
                    len(kb_docs), len(web_results), len(fusion_sources))

        return OrchestratedResult(
            answer=answer,
            kb_documents=kb_docs,
            web_results=web_results,
            fusion_sources=fusion_sources,
            intent=intent,
            retrieval_time_ms=t_retrieval,
            generation_time_ms=t_generation,
        )

    # ---------- 检索子任务 ----------

    async def _run_kb_search(self, query: str, top_k: int, user_id: Optional[str]) -> List[Document]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.kb_retriever.retrieve(
                query, top_k=top_k, user_id=user_id, use_multi_query=False
            )
        )

    async def _run_web_search(self, query: str) -> List:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.web_search_tool.search(query, max_results=8)
        )

    # ---------- 融合 ----------

    def _fuse_sources(
        self,
        kb_docs: List[Document],
        web_results: List,
    ) -> List[Dict[str, Any]]:
        sources: List[Dict[str, Any]] = []

        # KB 来源
        for doc in kb_docs:
            sources.append({
                "type": "kb",
                "content": doc.page_content[:300],
                "source": doc.metadata.get("source") or doc.metadata.get("file_name", "未知"),
                "relevance_score": doc.metadata.get("relevance_score"),
                "full_content": doc.page_content,
            })

        # Web 来源
        for r in web_results:
            sources.append({
                "type": "web",
                "content": getattr(r, "snippet", "")[:300],
                "source": getattr(r, "title", "未知"),
                "url": getattr(r, "url", ""),
                "relevance_score": getattr(r, "relevance_score", 0.5),
                "source_type": getattr(r, "source_type", "general"),
                "publish_date": getattr(r, "publish_date", None),
            })

        # 按相关度排序
        sources.sort(key=lambda s: s.get("relevance_score", 0), reverse=True)
        return sources

    # ---------- 上下文构建 ----------

    def _build_context(self, sources: List[Dict[str, Any]], max_total_chars: int = 5000) -> str:
        if not sources:
            return "(未检索到相关信息)"

        parts: List[str] = []
        remaining = max_total_chars

        kb_sources = [s for s in sources if s["type"] == "kb"]
        web_sources = [s for s in sources if s["type"] == "web"]

        if kb_sources:
            parts.append("## 知识库文献")
            for i, s in enumerate(kb_sources, 1):
                text = s["full_content"][:min(500, remaining)]
                if not text:
                    continue
                parts.append(f"【文献{i}】来源: {s['source']}\n{text}")
                remaining -= len(text)
                if remaining <= 0:
                    break

        if web_sources:
            parts.append("\n## 网络实时信息")
            for i, s in enumerate(web_sources, 1):
                date_hint = f" ({s.get('publish_date')})" if s.get("publish_date") else ""
                text = f"标题: {s['source']}{date_hint}\n内容: {s['content']}"
                parts.append(f"【来源{i}】{text}")
                remaining -= len(text)
                if remaining <= 0:
                    break

        return "\n\n".join(parts)

    def _build_prompt(
        self,
        custom_system_prompt: Optional[str],
        kb_docs: List[Document],
        web_results: List,
    ):
        from langchain_core.prompts import ChatPromptTemplate

        has_kb = len(kb_docs) > 0
        has_web = len(web_results) > 0

        if custom_system_prompt:
            system = custom_system_prompt
        elif has_kb and has_web:
            system = """你是 Geo-Agent AI 助手。请综合知识库文献和网络实时信息回答用户问题。

原则:
- 优先使用知识库文献的权威内容，网络信息补充时效性
- 引用文献用【文献X】，引用网络信息用【来源X】
- 信息冲突时，说明差异并给出判断"""
        elif has_kb:
            system = """你是 Geo-Agent AI 助手。请基于知识库文献回答用户问题。

原则:
- 优先使用文献内容，可结合你的知识补充
- 引用文献用【文献X】"""
        elif has_web:
            system = """你是 Geo-Agent AI 助手。请基于网络实时信息回答用户问题。

原则:
- 综合多源网络信息
- 标注信息来源【来源X】
- 注明信息时效性"""
        else:
            system = """你是 Geo-Agent AI 助手。请基于你的知识回答用户问题。"""

        return ChatPromptTemplate.from_messages([
            ("system", system + "\n\n{context}"),
            ("human", "{question}"),
        ])


# ---------------- 工厂 ----------

def create_search_orchestrator(
    kb_retriever=None,
    web_search_tool=None,
    llm_provider=None,
    use_reranker: bool = True,
) -> SearchOrchestrator:
    """创建搜索编排器（自动注入默认依赖）"""
    if kb_retriever is None:
        from src.rag.web_enhanced_retriever import create_web_enhanced_rag_retriever
        kb_retriever = create_web_enhanced_rag_retriever()
    if web_search_tool is None:
        from src.tools.web_search import create_web_search_tool
        web_search_tool = create_web_search_tool()
    if llm_provider is None:
        from src.core.llm_provider import create_llm_provider
        llm_provider = create_llm_provider()

    return SearchOrchestrator(
        kb_retriever=kb_retriever,
        web_search_tool=web_search_tool,
        llm_provider=llm_provider,
        use_reranker=use_reranker,
    )
