"""Agent 事件定义。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AgentEventType(str, Enum):
    INFO = "info"
    ROUTE = "route"
    PLAN = "plan"
    THOUGHT = "thought"
    STEP_START = "step_start"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    REPLAN = "replan"
    CONTENT = "content"
    FINAL = "final"
    ERROR = "error"


class AgentEvent(BaseModel):
    """统一事件结构。"""

    type: AgentEventType = Field(..., description="事件类型")
    run_id: str = Field(..., description="运行ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    payload: Dict[str, Any] = Field(default_factory=dict, description="事件载荷")


def create_info_event(run_id: str, status: str, **payload: Any) -> AgentEvent:
    return AgentEvent(
        type=AgentEventType.INFO,
        run_id=run_id,
        payload={"status": status, **payload},
    )


def create_plan_event(run_id: str, summary: str, steps: list[dict[str, Any]]) -> AgentEvent:
    return AgentEvent(
        type=AgentEventType.PLAN,
        run_id=run_id,
        payload={"summary": summary, "steps": steps},
    )


def create_route_event(run_id: str, intent: str, summary: str, reason: str, **payload: Any) -> AgentEvent:
    return AgentEvent(
        type=AgentEventType.ROUTE,
        run_id=run_id,
        payload={"intent": intent, "summary": summary, "reason": reason, **payload},
    )


def create_thought_event(run_id: str, summary: str, **payload: Any) -> AgentEvent:
    return AgentEvent(
        type=AgentEventType.THOUGHT,
        run_id=run_id,
        payload={"summary": summary, **payload},
    )


def create_step_start_event(run_id: str, step: dict[str, Any]) -> AgentEvent:
    return AgentEvent(type=AgentEventType.STEP_START, run_id=run_id, payload=step)


def create_tool_call_event(run_id: str, step_id: str, tool_name: str, tool_input: dict[str, Any]) -> AgentEvent:
    return AgentEvent(
        type=AgentEventType.TOOL_CALL,
        run_id=run_id,
        payload={"step_id": step_id, "tool_name": tool_name, "input": tool_input, "tool_input": tool_input},
    )


def create_tool_result_event(
    run_id: str,
    step_id: str,
    tool_name: str,
    ok: bool,
    observation: str,
    latency_ms: int,
    sources: Optional[list[dict[str, Any]]] = None,
    error: Optional[dict[str, Any]] = None,
) -> AgentEvent:
    return AgentEvent(
        type=AgentEventType.TOOL_RESULT,
        run_id=run_id,
        payload={
            "step_id": step_id,
            "tool_name": tool_name,
            "ok": ok,
            "status": "completed" if ok else "failed",
            "observation": observation,
            "latency_ms": latency_ms,
            "sources": sources or [],
            "error": error,
        },
    )


def create_replan_event(run_id: str, summary: str, steps: list[dict[str, Any]], reason: str) -> AgentEvent:
    return AgentEvent(
        type=AgentEventType.REPLAN,
        run_id=run_id,
        payload={"summary": summary, "steps": steps, "reason": reason},
    )


def create_content_event(run_id: str, content: str, **payload: Any) -> AgentEvent:
    return AgentEvent(
        type=AgentEventType.CONTENT,
        run_id=run_id,
        payload={"content": content, **payload},
    )


def create_final_event(
    run_id: str,
    final_answer: str,
    sources: list[dict[str, Any]],
    *,
    execution_time: float | None = None,
) -> AgentEvent:
    return AgentEvent(
        type=AgentEventType.FINAL,
        run_id=run_id,
        payload={
            "status": "completed",
            "final_answer": final_answer,
            "sources": sources,
            "execution_time": execution_time,
        },
    )


def create_error_event(run_id: str, code: str, message: str, **payload: Any) -> AgentEvent:
    return AgentEvent(
        type=AgentEventType.ERROR,
        run_id=run_id,
        payload={"status": "failed", "code": code, "message": message, **payload},
    )
