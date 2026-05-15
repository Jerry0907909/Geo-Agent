"""正式 Agent API 路由。"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.agent.runtime import create_agent_runtime
from src.agent.schemas import AgentConstraints, AgentSessionState
from src.agent.store import get_agent_run_store
from src.api.schemas import AgentQueryRequest, AgentQueryResponse, AgentStepResponse, DocumentSource
from src.auth.deps import get_current_active_user, get_db
from src.database.models import Conversation, Message, SearchHistory, User

router = APIRouter(prefix="/agent", tags=["Agent"])
logger = logging.getLogger(__name__)
MAX_CONCURRENT_RUNS_PER_USER = 1


def _build_constraints(request: AgentQueryRequest) -> AgentConstraints:
    return AgentConstraints(
        max_iterations=request.max_iterations,
        max_failures=2,
        timeout_seconds=300,
        top_k=request.top_k,
        allow_web_search=request.allow_web_search,
        read_only_tools=True,
        retrieval_mode=request.retrieval_mode,
    )


def _serialize_sources(sources: List[dict[str, Any]]) -> List[DocumentSource]:
    return [
        DocumentSource(
            content=str(source.get("content", "")),
            source=str(source.get("source", "未知来源")),
            relevance_score=source.get("relevance_score"),
            metadata={
                k: v
                for k, v in source.items()
                if k not in {"content", "source", "relevance_score"}
            },
        )
        for source in sources
    ]


def _serialize_steps(state: AgentSessionState, return_steps: bool) -> List[AgentStepResponse]:
    if not return_steps:
        return []
    return [
        AgentStepResponse(
            step_id=step.step_id,
            title=step.title,
            goal=step.goal,
            tool_name=step.tool_name,
            status=getattr(step.status, "value", step.status),
            tool_input=step.tool_input,
            expected_output=step.expected_output,
            reasoning_summary=step.reasoning_summary,
            observation=step.observation,
            sources=_serialize_sources(step.sources),
            latency_ms=step.latency_ms,
        )
        for step in state.steps
    ]


def _build_response(
    state: AgentSessionState,
    *,
    execution_time: float | None,
    return_steps: bool,
) -> AgentQueryResponse:
    return AgentQueryResponse(
        run_id=state.run_id,
        conversation_id=state.conversation_id,
        status=getattr(state.status, "value", state.status),
        plan_summary=state.plan_summary,
        final_answer=state.final_answer,
        steps=_serialize_steps(state, return_steps),
        sources=_serialize_sources(state.sources),
        execution_time=execution_time,
        error=state.error.model_dump() if state.error else None,
    )


def _serialize_event(
    event_type: str,
    run_id: str,
    timestamp: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "type": event_type,
        "run_id": run_id,
        "timestamp": timestamp,
        "payload": payload,
    }


def _serialize_agent_event(
    event_run_id: str,
    timestamp: str,
    event_type: str,
    payload: Dict[str, Any],
    *,
    conversation_id: int | None,
) -> str:
    body_payload = dict(payload)
    if body_payload.get("sources"):
        body_payload["sources"] = [source.model_dump() for source in _serialize_sources(body_payload["sources"])]
    if conversation_id is not None and "conversation_id" not in body_payload:
        body_payload["conversation_id"] = conversation_id
    serialized = _serialize_event(
        event_type=event_type,
        run_id=event_run_id,
        timestamp=timestamp,
        payload=body_payload,
    )
    return f"data: {json.dumps(serialized, ensure_ascii=False)}\n\n"


def _reserve_user_run(store: Any, owner_id: int, state: AgentSessionState) -> None:
    if not store.start_run(owner_id, state, max_concurrent=MAX_CONCURRENT_RUNS_PER_USER):
        active_run_ids = store.active_run_ids(owner_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"当前已有运行中的 Agent 任务，请等待完成后再发起新任务。active_runs={active_run_ids}",
        )


def _get_or_create_conversation(
    *,
    request: AgentQueryRequest,
    current_user: User,
    db: Session,
) -> Conversation:
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.is_active == True,
        ).first()
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
        return conversation

    conversation = Conversation(
        user_id=current_user.id,
        title=request.task[:50] + ("..." if len(request.task) > 50 else ""),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _persist_agent_result(
    *,
    db: Session,
    current_user: User,
    conversation: Conversation,
    request: AgentQueryRequest,
    state: AgentSessionState,
    execution_time: float,
) -> None:
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.task,
    )
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=state.final_answer or "",
        message_metadata={
            "mode": "agent",
            "run_id": state.run_id,
            "sources": [source.model_dump() for source in _serialize_sources(state.sources)],
            "reasoning_steps": [step.model_dump() for step in _serialize_steps(state, True)],
        },
    )
    search_history = SearchHistory(
        user_id=current_user.id,
        query=request.task,
        result_count=len(state.sources),
        search_type="agent",
        response_time=int(execution_time * 1000),
    )
    conversation.updated_at = datetime.now()
    db.add(user_message)
    db.add(assistant_message)
    db.add(search_history)
    db.commit()


@router.post("/query", response_model=AgentQueryResponse)
async def agent_query(
    request: AgentQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AgentQueryResponse:
    runtime = create_agent_runtime()
    constraints = _build_constraints(request)
    conversation = _get_or_create_conversation(request=request, current_user=current_user, db=db)
    store = get_agent_run_store()
    state = runtime.create_run_state(
        task=request.task,
        conversation_id=conversation.id,
        constraints=constraints,
    )
    _reserve_user_run(store, current_user.id, state)

    start_time = time.time()
    logger.info(
        "[agent-api] query_started user_id=%s conversation_id=%s run_id=%s",
        current_user.id,
        conversation.id,
        state.run_id,
    )
    try:
        state = runtime.run_state(
            state,
            on_state_change=lambda latest_state: store.save(current_user.id, latest_state, active=True),
            cancel_checker=store.is_cancel_requested,
        )
        execution_time = time.time() - start_time
        store.finish_run(current_user.id, state)
        _persist_agent_result(
            db=db,
            current_user=current_user,
            conversation=conversation,
            request=request,
            state=state,
            execution_time=execution_time,
        )
        return _build_response(state, execution_time=execution_time, return_steps=request.return_steps)
    finally:
        if state.status not in {"completed", "failed", "cancelled"}:
            store.finish_run(current_user.id, state)


@router.post("/stream")
async def agent_stream(
    request: AgentQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    runtime = create_agent_runtime()
    constraints = _build_constraints(request)
    conversation = _get_or_create_conversation(request=request, current_user=current_user, db=db)
    store = get_agent_run_store()
    state = runtime.create_run_state(
        task=request.task,
        conversation_id=conversation.id,
        constraints=constraints,
    )
    _reserve_user_run(store, current_user.id, state)

    async def generate_stream() -> AsyncGenerator[str, None]:
        start_time = time.time()
        logger.info(
            "[agent-api] stream_started user_id=%s conversation_id=%s run_id=%s",
            current_user.id,
            conversation.id,
            state.run_id,
        )
        try:
            for event in runtime.iter_state_events(
                state,
                on_state_change=lambda latest_state: store.save(current_user.id, latest_state, active=True),
                cancel_checker=store.is_cancel_requested,
            ):
                event_payload = dict(event.payload)
                if event.type.value == "final" and event_payload.get("sources"):
                    yield f"data: {json.dumps({'type': 'sources', 'sources': [source.model_dump() for source in _serialize_sources(event_payload['sources'])]}, ensure_ascii=False)}\n\n"
                yield _serialize_agent_event(
                    event.run_id,
                    event.timestamp,
                    event.type.value,
                    event_payload,
                    conversation_id=conversation.id,
                )

            execution_time = time.time() - start_time
            store.finish_run(current_user.id, state)
            _persist_agent_result(
                db=db,
                current_user=current_user,
                conversation=conversation,
                request=request,
                state=state,
                execution_time=execution_time,
            )
            yield f"data: {json.dumps({'type': 'done', 'execution_time': execution_time, 'run_id': state.run_id, 'conversation_id': conversation.id}, ensure_ascii=False)}\n\n"
        finally:
            if state.status not in {"completed", "failed", "cancelled"}:
                store.finish_run(current_user.id, state)

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runs/{run_id}", response_model=AgentQueryResponse)
async def get_agent_run(
    run_id: str = Path(..., description="Agent 运行ID"),
    current_user: User = Depends(get_current_active_user),
) -> AgentQueryResponse:
    store = get_agent_run_store()
    state = store.get(run_id, owner_id=current_user.id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运行记录不存在")
    execution_time = max((state.updated_at - state.started_at).total_seconds(), 0.0)
    return _build_response(state, execution_time=execution_time, return_steps=True)


@router.post("/runs/{run_id}/cancel", response_model=AgentQueryResponse)
async def cancel_agent_run(
    run_id: str = Path(..., description="Agent 运行ID"),
    current_user: User = Depends(get_current_active_user),
) -> AgentQueryResponse:
    store = get_agent_run_store()
    state = store.cancel(run_id, owner_id=current_user.id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运行记录不存在")
    execution_time = max((state.updated_at - state.started_at).total_seconds(), 0.0)
    return _build_response(state, execution_time=execution_time, return_steps=True)
