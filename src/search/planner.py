"""Query Planning — LLM-based query decomposition and rewriting"""

import logging
from typing import List

logger = logging.getLogger(__name__)

PLAN_SYSTEM_PROMPT = """你是搜索规划专家。将用户问题拆分为 3~5 个独立搜索查询。
每个查询应定位不同角度，组合后可覆盖问题所需全部信息。

规则：
- 不同查询从不同维度切入（定义/背景/对比/数据/最新进展）
- 查询中不含代词（"它""这个""那个"），必须使用完整实体名
- 使用精准术语，保持简洁（每条 ≤ 50 字符）
- 如果问题是英文，查询用英文；中文则中文
- 仅输出查询文本，每行一个，不要编号，不要解释"""


async def plan_queries(question: str, llm=None, num_queries: int = 4) -> List[str]:
    """使用 LLM 将用户问题拆解为多个搜索查询

    Args:
        question: 用户原始问题
        llm: LLMProvider 实例（不传则自动创建）
        num_queries: 期望生成的查询数（3~5）
    """
    if llm is None:
        from src.core.llm_provider import create_llm_provider
        llm = create_llm_provider()

    prompt = (
        f"{PLAN_SYSTEM_PROMPT}\n\n"
        f"用户问题：{question}\n\n"
        f"请输出 {num_queries} 个搜索查询："
    )

    try:
        # 使用同步 generate（planning 不异步关键路径）
        raw = llm.generate(prompt, max_tokens=300)
        queries = _parse_queries(raw, num_queries)
        logger.info("[Planner] 拆解: %s → %s", question[:50], queries)
        return queries
    except Exception:
        logger.exception("[Planner] LLM 调用失败，使用原始 query")
        return [question]


def _parse_queries(raw: str, expected: int) -> List[str]:
    queries = []
    for line in raw.strip().split("\n"):
        q = line.strip().lstrip("0123456789.-) ").strip()
        if q and len(q) > 3 and q not in queries:
            queries.append(q)
    # 至少返回原始 query
    if not queries:
        return []
    # 限制数量
    return queries[:expected]
