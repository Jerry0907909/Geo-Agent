"""文本分块 — 中文友好递归分割"""

from typing import List

from src.search.schemas import ExtractedChunk

SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    """递归字符分割，中文友好"""
    if not text:
        return []
    return _split_text(text, SEPARATORS, chunk_size, overlap)


def chunk_extracted(docs: List[ExtractedChunk], chunk_size: int = 512) -> List[ExtractedChunk]:
    """将 ExtractedChunk 进一步切分为子 chunk"""
    result = []
    idx = 0
    for doc in docs:
        sub_texts = chunk_text(doc.text, chunk_size)
        for st in sub_texts:
            result.append(ExtractedChunk(
                chunk_id=f"{doc.source_url}_{idx}",
                text=st,
                source_url=doc.source_url,
                source_title=doc.source_title,
                chunk_index=idx,
            ))
            idx += 1
    return result


def _split_text(text: str, separators: list, size: int, overlap: int) -> List[str]:
    result = []
    _split(text, separators, size, overlap, result)
    return result


def _split(text: str, seps: list, size: int, overlap: int, result: list):
    if len(text) <= size:
        if text.strip():
            result.append(text.strip())
        return

    sep = seps[0] if seps else ""
    next_seps = seps[1:] if len(seps) > 1 else [""]

    if sep and sep in text:
        parts = text.split(sep)
        current = ""
        for part in parts:
            candidate = (current + sep + part) if current else part
            if len(candidate) > size and current:
                result.append(current.strip())
                current = part if len(part) <= size else ""
            else:
                current = candidate

            if len(part) > size:
                _split(part, next_seps, size, overlap, result)
        if current.strip():
            result.append(current.strip())
    else:
        _split(text, next_seps, size, overlap, result)
