from __future__ import annotations

from typing import Sequence

from langchain_core.documents import Document


def build_context_from_documents(docs: Sequence[Document], max_chars: int = 4000) -> str:
    """将检索到的文献片段整理为上下文"""

    parts: list[str] = []
    remaining = max_chars

    for idx, doc in enumerate(docs, start=1):
        if remaining <= 0:
            break

        content = (doc.page_content or "").strip()
        if not content:
            continue

        header_lines: list[str] = [f"【文献片段 {idx}】"]
        source = doc.metadata.get("source") or doc.metadata.get("file_name")
        if source:
            header_lines.append(f"来源: {source}")

        relevance_score = doc.metadata.get("relevance_score")
        if relevance_score is not None and relevance_score > 0:
            header_lines.append(f"相关度: {relevance_score:.2%}")

        header = "\n".join(header_lines)

        if len(content) > remaining:
            content = content[:remaining]

        block = f"{header}\n{content}"
        parts.append(block)
        remaining -= len(content)

    return "\n\n".join(parts)


def build_rag_prompt(question: str, context: str) -> str:
    """构建 RAG 问答提示词"""

    system_instructions = (
        "你是 Geo-Agent，一个 AI 智能助手。请结合提供的文献片段和你的知识回答问题。"
        "如果文献信息充分，优先引用文献内容；如果文献信息不足，可以基于你的知识补充。"
        "回答使用中文，结构清晰、逻辑严谨。"
    )

    prompt = (
        f"{system_instructions}\n\n"
        f"【参考文献片段】\n{context}\n\n"
        f"【用户问题】\n{question}\n\n"
        "请回答上述问题。回答时请：\n"
        "1. 引用文献内容时用【片段X】标注来源\n"
        "2. 区分文献引用和个人分析\n"
        "3. 保持结构清晰"
    )
    return prompt
