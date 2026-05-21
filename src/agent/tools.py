"""Agent 可执行工具实现。"""

from __future__ import annotations

import ast
import json
import logging
import math
import operator
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.agent.schemas import AgentError, AgentToolResult

logger = logging.getLogger(__name__)


@dataclass
class AgentTool:
    """Runtime 使用的可执行工具。"""

    name: str
    executor: Callable[[Dict[str, Any]], AgentToolResult]

    def execute(self, tool_input: Dict[str, Any]) -> AgentToolResult:
        return self.executor(tool_input)


def _ok(
    *,
    start_time: float,
    data: Optional[Dict[str, Any]] = None,
    sources: Optional[list[Dict[str, Any]]] = None,
    observation: Optional[str] = None,
) -> AgentToolResult:
    return AgentToolResult(
        ok=True,
        data=data or {},
        sources=sources or [],
        observation=observation,
        latency_ms=int((time.time() - start_time) * 1000),
    )


def _error(start_time: float, code: str, message: str) -> AgentToolResult:
    return AgentToolResult(
        ok=False,
        error=AgentError(code=code, message=message),
        latency_ms=int((time.time() - start_time) * 1000),
        observation=message,
    )


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"参数 {key} 必须是非空字符串")
    return value.strip()


def _optional_positive_int(payload: Dict[str, Any], key: str, default: int) -> int:
    value = payload.get(key, default)
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"参数 {key} 必须是正整数")
    return value


def _safe_excerpt(content: str, max_chars: int) -> str:
    clean = re.sub(r"\s+", " ", content).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].rstrip() + "..."


def execute_clarify(tool_input: Dict[str, Any]) -> AgentToolResult:
    start_time = time.time()
    try:
        task = _require_str(tool_input, "task")
        follow_up = (
            f"当前任务“{task}”缺少关键上下文。"
            "请补充你希望处理的对象、范围、期望输出形式，或提供具体文档名/问题。"
        )
        return _ok(
            start_time=start_time,
            data={"question": follow_up},
            observation=follow_up,
        )
    except Exception as exc:
        logger.exception("clarify 执行失败")
        return _error(start_time, "CLARIFY_FAILED", str(exc))


def execute_direct_answer(tool_input: Dict[str, Any]) -> AgentToolResult:
    start_time = time.time()
    try:
        from src.core.llm_provider import create_llm_provider

        question = _require_str(tool_input, "question")
        llm = create_llm_provider(temperature=0.3)
        prompt = (
            "你是 Geo-Agent 的直接回答模块。"
            "当前任务不要求强制检索，请直接给出简洁、准确、专业的中文回答。"
            "如果问题信息不足，请明确指出缺失点，不要虚构事实。\n\n"
            f"用户问题：{question}\n\n回答："
        )
        answer = llm.generate(prompt)
        return _ok(
            start_time=start_time,
            data={"answer": answer},
            observation=answer,
        )
    except Exception as exc:
        logger.exception("direct_answer 执行失败")
        return _error(start_time, "DIRECT_ANSWER_FAILED", str(exc))


def execute_document_catalog(tool_input: Dict[str, Any]) -> AgentToolResult:
    start_time = time.time()
    try:
        from src.api.routes import get_file_type
        from src.database.chroma_manager import create_chroma_manager, list_all_collections

        action = str(tool_input.get("action", "list_documents")).strip().lower()
        collection_name = tool_input.get("collection_name")
        collections_to_query = [collection_name] if collection_name else list_all_collections()

        if action == "list_collections":
            collections = []
            for coll_name in collections_to_query:
                manager = create_chroma_manager(collection_name=coll_name)
                collections.append({"name": coll_name, "count": manager.collection.count()})
            observation = "；".join(f"{item['name']}({item['count']})" for item in collections) or "未发现集合。"
            return _ok(
                start_time=start_time,
                data={"collections": collections},
                observation=f"当前集合：{observation}",
            )

        if action == "file_types":
            type_counts: dict[str, int] = {}
            seen_sources: set[str] = set()
            for coll_name in collections_to_query:
                manager = create_chroma_manager(collection_name=coll_name)
                result = manager.collection.get()
                for meta in result.get("metadatas", []):
                    if not meta:
                        continue
                    source = meta.get("source") or meta.get("file_name", "未知")
                    unique_key = f"{coll_name}::{source}"
                    if unique_key in seen_sources:
                        continue
                    seen_sources.add(unique_key)
                    file_type = get_file_type(source)
                    type_counts[file_type] = type_counts.get(file_type, 0) + 1
            stats = [{"type": key, "count": value} for key, value in sorted(type_counts.items())]
            observation = "；".join(f"{item['type']}={item['count']}" for item in stats) or "未发现文档类型统计。"
            return _ok(
                start_time=start_time,
                data={"file_types": stats},
                observation=f"文件类型统计：{observation}",
            )

        documents: dict[str, dict[str, Any]] = {}
        for coll_name in collections_to_query:
            manager = create_chroma_manager(collection_name=coll_name)
            result = manager.collection.get()
            for meta in result.get("metadatas", []):
                if not meta:
                    continue
                source = meta.get("source") or meta.get("file_name", "未知")
                key = f"{coll_name}::{source}"
                if key not in documents:
                    documents[key] = {
                        "source": source,
                        "collection": coll_name,
                        "file_type": get_file_type(source),
                        "chunks": 0,
                    }
                documents[key]["chunks"] += 1
        document_list = sorted(documents.values(), key=lambda item: (str(item["collection"]), str(item["source"])))
        observation = "；".join(f"{item['source']}@{item['collection']}" for item in document_list[:12])
        if len(document_list) > 12:
            observation += f"；其余 {len(document_list) - 12} 个文档未展开"
        return _ok(
            start_time=start_time,
            data={"documents": document_list, "count": len(document_list)},
            observation=f"知识库中共有 {len(document_list)} 个文档。{observation}",
        )
    except Exception as exc:
        logger.exception("document_catalog 执行失败")
        return _error(start_time, "DOCUMENT_CATALOG_FAILED", str(exc))


def execute_document_read(tool_input: Dict[str, Any]) -> AgentToolResult:
    start_time = time.time()
    try:
        from src.database.chroma_manager import create_chroma_manager, list_all_collections

        source = _require_str(tool_input, "source")
        max_chars = _optional_positive_int(tool_input, "max_chars", 4000)
        collection_name = tool_input.get("collection_name")
        collections_to_query = [collection_name] if collection_name else list_all_collections()

        chunks: list[dict[str, Any]] = []
        metadata: dict[str, Any] | None = None
        for coll_name in collections_to_query:
            manager = create_chroma_manager(collection_name=coll_name)
            result = manager.collection.get(
                where={"$or": [{"source": source}, {"file_name": source}]},
                include=["documents", "metadatas"],
            )
            documents = result.get("documents", [])
            metadatas = result.get("metadatas", [])
            for index, content in enumerate(documents):
                meta = metadatas[index] if index < len(metadatas) else {}
                chunks.append({
                    "chunk_id": meta.get("chunk_id", index),
                    "content": content,
                    "metadata": meta,
                    "collection": coll_name,
                })
                if metadata is None:
                    metadata = {
                        "source": meta.get("source", source),
                        "file_name": meta.get("file_name", source),
                        "collection": coll_name,
                        "date": meta.get("date"),
                        "author": meta.get("author"),
                    }

        if not chunks:
            raise ValueError(f"未找到文档: {source}")

        chunks.sort(key=lambda item: item.get("chunk_id", 0))
        full_content = "\n\n".join(chunk["content"] for chunk in chunks)
        excerpt = _safe_excerpt(full_content, max_chars=max_chars)
        sources = [
            {
                "content": _safe_excerpt(chunk["content"], max_chars=260),
                "source": source,
                "type": "document",
                "metadata": {
                    "chunk_id": chunk.get("chunk_id"),
                    "collection": chunk.get("collection"),
                },
            }
            for chunk in chunks[:5]
        ]
        return _ok(
            start_time=start_time,
            data={
                "source": source,
                "content": excerpt,
                "metadata": metadata or {"source": source},
                "chunk_count": len(chunks),
            },
            sources=sources,
            observation=f"已读取文档 {source}。正文摘录：{excerpt}",
        )
    except Exception as exc:
        logger.exception("document_read 执行失败")
        return _error(start_time, "DOCUMENT_READ_FAILED", str(exc))


def execute_literature_search(tool_input: Dict[str, Any]) -> AgentToolResult:
    start_time = time.time()
    try:
        from src.rag.unified_retrieval import create_unified_retrieval_service

        query = _require_str(tool_input, "query")
        top_k = _optional_positive_int(tool_input, "top_k", 5)
        source_mode = str(tool_input.get("source_mode", "local")).strip().lower() or "local"
        retrieval = create_unified_retrieval_service().retrieve(
            query=query,
            top_k=top_k,
            retrieval_mode=source_mode,
            use_multi_query=False,
        )
        sources = retrieval.sources
        documents = [
            {
                "content": source.get("content", ""),
                "source": source.get("source", "未知来源"),
                "relevance_score": source.get("relevance_score"),
                "metadata": source.get("metadata", {}),
                "url": source.get("url"),
                "type": source.get("type", "document"),
            }
            for source in sources
        ]
        observation = f"检索到 {len(documents)} 条相关文献片段。"
        return _ok(
            start_time=start_time,
            data={"documents": documents},
            sources=sources,
            observation=observation,
        )
    except Exception as exc:
        logger.exception("literature_search 执行失败")
        return _error(start_time, "LITERATURE_SEARCH_FAILED", str(exc))


def execute_knowledge_query(tool_input: Dict[str, Any]) -> AgentToolResult:
    start_time = time.time()
    try:
        from src.rag.unified_retrieval import create_unified_retrieval_service

        query = _require_str(tool_input, "query")
        top_k = _optional_positive_int(tool_input, "top_k", 5)
        source_mode = str(tool_input.get("source_mode", "local")).strip().lower() or "local"
        answer, retrieval = create_unified_retrieval_service().answer(
            query=query,
            top_k=top_k,
            retrieval_mode=source_mode,
        )
        return _ok(
            start_time=start_time,
            data={"answer": answer},
            sources=retrieval.sources,
            observation=answer,
        )
    except Exception as exc:
        logger.exception("knowledge_query 执行失败")
        return _error(start_time, "KNOWLEDGE_QUERY_FAILED", str(exc))


def execute_web_search(tool_input: Dict[str, Any]) -> AgentToolResult:
    start_time = time.time()
    try:
        from src.tools.web_search import create_web_search_tool

        query = _require_str(tool_input, "query")
        max_results = _optional_positive_int(tool_input, "max_results", 5)
        web_tool = create_web_search_tool()
        results = web_tool.search(query, max_results=max_results)
        structured_results = [
            {
                "title": result.title,
                "content": result.snippet,
                "url": result.url,
                "source_type": result.source_type,
                "relevance_score": result.relevance_score,
                "publish_date": result.publish_date,
            }
            for result in results
        ]
        sources = [
            {
                "content": result.snippet,
                "source": result.title,
                "url": result.url,
                "type": "web",
                "source_type": result.source_type,
                "metadata": {"publish_date": result.publish_date},
            }
            for result in results
        ]
        observation = f"检索到 {len(structured_results)} 条网络结果。"
        return _ok(
            start_time=start_time,
            data={"results": structured_results},
            sources=sources,
            observation=observation,
        )
    except Exception as exc:
        logger.exception("web_search 执行失败")
        return _error(start_time, "WEB_SEARCH_FAILED", str(exc))


def execute_document_metadata(tool_input: Dict[str, Any]) -> AgentToolResult:
    start_time = time.time()
    try:
        from src.database.chroma_manager import create_chroma_manager, list_all_collections

        action = str(tool_input.get("action", "summary")).strip().lower()
        collection_name = tool_input.get("collection_name")
        collections = list_all_collections()

        collection_stats: list[Dict[str, Any]] = []
        total_documents = 0
        for name in collections:
            if collection_name and name != collection_name:
                continue
            manager = create_chroma_manager(collection_name=name)
            count = manager.count()
            total_documents += count
            collection_stats.append({"name": name, "count": count})

        metadata: Dict[str, Any]
        if action == "count":
            metadata = {"count": total_documents, "collection_name": collection_name}
            observation = f"知识库共有 {total_documents} 条向量文档。"
        elif action == "collections":
            metadata = {"collections": collection_stats}
            observation = f"当前共有 {len(collection_stats)} 个知识库集合。"
        else:
            metadata = {
                "total_documents": total_documents,
                "collection_count": len(collection_stats),
                "collections": collection_stats,
            }
            observation = (
                f"当前共有 {len(collection_stats)} 个知识库集合，累计 {total_documents} 条向量文档。"
            )

        return _ok(start_time=start_time, data={"metadata": metadata}, observation=observation)
    except Exception as exc:
        logger.exception("document_metadata 执行失败")
        return _error(start_time, "DOCUMENT_METADATA_FAILED", str(exc))


_BINARY_OPERATORS: Dict[type[ast.AST], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS: Dict[type[ast.AST], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_SAFE_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "abs": abs,
    "round": round,
    "pow": pow,
    "sqrt": math.sqrt,
    "log": math.log,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": lambda: math.pi,
    "e": lambda: math.e,
}


def _eval_math_expression(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_math_expression(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        return _BINARY_OPERATORS[type(node.op)](
            _eval_math_expression(node.left),
            _eval_math_expression(node.right),
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_eval_math_expression(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func = _SAFE_FUNCTIONS.get(node.func.id)
        if func is None:
            raise ValueError(f"不支持的函数: {node.func.id}")
        args = [_eval_math_expression(arg) for arg in node.args]
        return func(*args)
    raise ValueError("仅支持安全数学表达式")


def execute_calculator(tool_input: Dict[str, Any]) -> AgentToolResult:
    start_time = time.time()
    try:
        expression = _require_str(tool_input, "expression")
        parsed = ast.parse(expression, mode="eval")
        value = _eval_math_expression(parsed)
        return _ok(
            start_time=start_time,
            data={"result": value},
            observation=f"表达式 {expression} 的结果为 {value}。",
        )
    except Exception as exc:
        logger.exception("calculator 执行失败")
        return _error(start_time, "CALCULATOR_FAILED", str(exc))


def create_default_runtime_tools() -> Dict[str, AgentTool]:
    return {
        "clarify": AgentTool(name="clarify", executor=execute_clarify),
        "direct_answer": AgentTool(name="direct_answer", executor=execute_direct_answer),
        "document_catalog": AgentTool(name="document_catalog", executor=execute_document_catalog),
        "document_read": AgentTool(name="document_read", executor=execute_document_read),
        "literature_search": AgentTool(name="literature_search", executor=execute_literature_search),
        "knowledge_query": AgentTool(name="knowledge_query", executor=execute_knowledge_query),
        "web_search": AgentTool(name="web_search", executor=execute_web_search),
        "document_metadata": AgentTool(name="document_metadata", executor=execute_document_metadata),
        "calculator": AgentTool(name="calculator", executor=execute_calculator),
    }


def summarize_tool_data(result: AgentToolResult) -> str:
    """将工具结果收敛为短 observation。"""
    if result.observation:
        return result.observation
    if result.error:
        return result.error.message
    if result.data:
        return json.dumps(result.data, ensure_ascii=False)[:400]
    return "工具已执行，但未返回可用内容。"
