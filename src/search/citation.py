"""引用溯源系统"""

from typing import List, Tuple

from src.search.schemas import RankedChunk, CitationRef

ANSWER_PROMPT = """你是 AI 搜索助手。基于以下来源回答用户问题。

要求:
1. 综合多个来源，不偏信单一来源
2. 引用时标注来源编号 [1][2]，每个关键事实必须引用
3. 不编造来源中没有的信息
4. 如果来源信息冲突，说明各方观点
5. 回答信息密度高，不重复
6. 末尾列出 References 并在文中引用对应编号

{context}

用户问题：{question}
"""


def build_citation_prompt(
    chunks: List[RankedChunk],
    question: str,
) -> Tuple[str, List[CitationRef], List[dict]]:
    """构建带引用的 answer prompt 和引用列表

    Returns:
        (prompt_text, citation_refs, source_dicts)
    """
    # 按 URL 去重分配编号
    url_to_id: dict[str, int] = {}
    citations: List[CitationRef] = []
    source_dicts = []

    for c in chunks:
        if c.source_url not in url_to_id:
            source_id = len(url_to_id) + 1
            url_to_id[c.source_url] = source_id
            citations.append(CitationRef(
                source_id=source_id,
                url=c.source_url,
                title=c.source_title,
            ))
            source_dicts.append({
                "source_id": source_id,
                "url": c.source_url,
                "title": c.source_title,
            })

    # 构建上下文
    context_parts = []
    for c in chunks:
        ref_id = url_to_id.get(c.source_url, 0)
        context_parts.append(f"[{ref_id}] {c.source_title}\n{c.text}")

    context = "\n\n".join(context_parts)
    prompt = ANSWER_PROMPT.format(context=context, question=question)

    return prompt, citations, source_dicts
