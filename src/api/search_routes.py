"""Deep Search API — SSE 流式深度搜索端点"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from src.search.schemas import DeepSearchRequest
from src.search.pipeline import execute
from src.auth.deps import get_current_active_user
from src.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["深度搜索"])


@router.post("/deep")
async def deep_search(
    request: DeepSearchRequest,
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """深度搜索 — 查询规划 → 多查询搜索 → 正文抽取 → 召回 → 重排序 → 压缩 → 带引用回答"""

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for event in execute(request):
                yield f"data: {json.dumps(event.model_dump(exclude_none=True), ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("[DeepSearch] 致命错误")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
