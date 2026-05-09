from __future__ import annotations

from typing import Sequence

from langchain_core.documents import Document


def build_context_from_documents(docs: Sequence[Document], max_chars: int = 4000) -> str:
    """将检索到的文档片段整理为提示词上下文字符串

    为避免提示过长，可通过 max_chars 控制总长度上限。
    """

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
        
        # 添加相似度分数
        relevance_score = doc.metadata.get("relevance_score")
        if relevance_score is not None:
            header_lines.append(f"相关度: {relevance_score:.2%}")

        header = "\n".join(header_lines)

        if len(content) > remaining:
            content = content[:remaining]

        block = f"{header}\n{content}"
        parts.append(block)
        remaining -= len(content)

    return "\n\n".join(parts)


def build_rag_prompt(question: str, context: str) -> str:
    """构建用于 RAG 问答的提示词"""

    system_instructions = (
        "你是一名地质学文献分析助手，只能基于提供的文献片段回答问题。"
        "如果文献信息不足以回答，请明确说明'根据给定文献无法确定'，不要编造内容。"
        "回答使用中文，结构清晰、逻辑严谨。"
    )

    prompt = (
        f"{system_instructions}\n\n"
        f"【参考文献片段】\n{context}\n\n"
        f"【用户问题】\n{question}\n\n"
        "请严格依据上述文献片段作答。回答时请：\n"
        "1. 在关键观点后用【片段X】标注引用来源\n"
        "2. 如有多个来源支持同一观点，可标注【片段X, Y】\n"
        "3. 保持回答结构清晰，分点论述"
    )
    return prompt
