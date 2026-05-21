"""Agent Executor 实现。"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Callable, Iterator, Optional

from src.agent.events import (
    AgentEvent,
    create_replan_event,
    create_step_start_event,
    create_tool_call_event,
    create_tool_result_event,
)
from src.agent.planner import AgentPlanner
from src.agent.registry import ToolRegistry
from src.agent.schemas import AgentPlan, AgentRunStatus, AgentSessionState, AgentStepStatus
from src.agent.tools import summarize_tool_data

import logging

logger = logging.getLogger(__name__)


class ExecutorError(RuntimeError):
    """执行阶段错误。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AgentExecutor:
    """顺序执行结构化计划。"""

    def __init__(
        self,
        registry: ToolRegistry,
        planner: Optional[AgentPlanner] = None,
    ) -> None:
        self.registry = registry
        self.planner = planner

    def execute(
        self,
        state: AgentSessionState,
        plan: AgentPlan,
        on_event: Optional[Callable[[AgentEvent], None]] = None,
        on_state_change: Optional[Callable[[AgentSessionState], None]] = None,
        cancel_checker: Optional[Callable[[str], bool]] = None,
    ) -> AgentSessionState:
        """执行计划并回写状态。"""
        for event in self.iter_execute(
            state,
            plan,
            on_state_change=on_state_change,
            cancel_checker=cancel_checker,
        ):
            if on_event:
                on_event(event)
        return state

    def iter_execute(
        self,
        state: AgentSessionState,
        plan: AgentPlan,
        on_state_change: Optional[Callable[[AgentSessionState], None]] = None,
        cancel_checker: Optional[Callable[[str], bool]] = None,
    ) -> Iterator[AgentEvent]:
        """执行计划并实时产出事件。"""
        state.status = AgentRunStatus.RUNNING
        state.updated_at = datetime.utcnow()
        self._notify_state_change(state, on_state_change)

        failure_count = 0
        loop_counter: Counter[str] = Counter()
        plan_steps = list(plan.steps)
        current_index = 0

        while current_index < len(plan_steps):
            self._ensure_runtime_available(state)
            if cancel_checker and cancel_checker(state.run_id):
                raise ExecutorError("RUN_CANCELLED", "运行已取消")

            step = plan_steps[current_index]
            step_signature = f"{step.tool_name}:{json.dumps(step.tool_input, ensure_ascii=False, sort_keys=True)}"
            loop_counter[step_signature] += 1
            if loop_counter[step_signature] > 2:
                step.status = AgentStepStatus.FAILED
                step.observation = "检测到重复执行循环，任务已中止。"
                self._notify_state_change(state, on_state_change)
                raise ExecutorError("LOOP_DETECTED", step.observation)

            step.status = AgentStepStatus.RUNNING
            state.updated_at = datetime.utcnow()
            self._notify_state_change(state, on_state_change)
            yield create_step_start_event(
                state.run_id,
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "goal": step.goal,
                    "tool_name": step.tool_name,
                },
            )
            yield create_tool_call_event(state.run_id, step.step_id, step.tool_name, step.tool_input)

            result = self.registry.execute(step.tool_name, step.tool_input)
            if not result.ok and self._should_retry(result.error.code if result.error else None):
                logger.warning(
                    "[agent] tool_retry run_id=%s step_id=%s tool_name=%s error_code=%s",
                    state.run_id,
                    step.step_id,
                    step.tool_name,
                    result.error.code if result.error else None,
                )
                yield create_tool_call_event(state.run_id, step.step_id, step.tool_name, step.tool_input)
                result = self.registry.execute(step.tool_name, step.tool_input)

            step.latency_ms = result.latency_ms
            step.sources = result.sources
            step.observation = summarize_tool_data(result)
            state.updated_at = datetime.utcnow()
            logger.info(
                "[agent] tool_finished run_id=%s step_id=%s tool_name=%s status=%s tool_latency_ms=%s error_code=%s",
                state.run_id,
                step.step_id,
                step.tool_name,
                "completed" if result.ok else "failed",
                result.latency_ms,
                result.error.code if result.error else None,
            )

            if result.ok:
                step.status = AgentStepStatus.COMPLETED
                state.sources.extend(result.sources)
                self._notify_state_change(state, on_state_change)
                yield create_tool_result_event(
                    state.run_id,
                    step.step_id,
                    step.tool_name,
                    True,
                    step.observation,
                    result.latency_ms,
                    sources=result.sources,
                )
                current_index += 1
                continue

            step.status = AgentStepStatus.FAILED
            failure_count += 1
            self._notify_state_change(state, on_state_change)
            yield create_tool_result_event(
                state.run_id,
                step.step_id,
                step.tool_name,
                False,
                step.observation or "工具执行失败",
                result.latency_ms,
                sources=result.sources,
                error=result.error.model_dump() if result.error else None,
            )

            if failure_count > state.constraints.max_failures:
                raise ExecutorError("TOOL_EXECUTION_FAILED", step.observation or "工具执行失败")

            if self.planner is None:
                current_index += 1
                continue

            completed_steps = [s for s in state.steps if s.status == AgentStepStatus.COMPLETED]
            replanned = self.planner.rebuild_plan(
                task=state.task,
                original_plan=plan,
                completed_steps=completed_steps,
                failed_step=step,
                failure_reason=step.observation or "工具执行失败",
                constraints=state.constraints,
            )
            if not replanned.steps:
                raise ExecutorError("REPLAN_FAILED", "重规划未生成可执行步骤")

            replacement_steps = []
            for new_step in replanned.steps:
                if new_step.step_id not in {existing.step_id for existing in state.steps}:
                    replacement_steps.append(new_step)

            if not replacement_steps:
                raise ExecutorError("REPLAN_FAILED", "重规划未生成新的步骤")

            state.steps.extend(replacement_steps)
            state.updated_at = datetime.utcnow()
            plan_steps = state.steps
            plan.summary = replanned.summary
            state.plan_summary = replanned.summary
            self._notify_state_change(state, on_state_change)
            yield create_replan_event(
                state.run_id,
                replanned.summary,
                [
                    {
                        "step_id": item.step_id,
                        "title": item.title,
                        "goal": item.goal,
                        "tool_name": item.tool_name,
                    }
                    for item in replacement_steps
                ],
                reason=step.observation or "工具执行失败",
            )
            current_index += 1

        return state

    @staticmethod
    def _notify_state_change(
        state: AgentSessionState,
        on_state_change: Optional[Callable[[AgentSessionState], None]],
    ) -> None:
        if on_state_change:
            on_state_change(state)

    @staticmethod
    def _should_retry(error_code: Optional[str]) -> bool:
        return error_code in {"TOOL_EXECUTION_FAILED"}

    @staticmethod
    def _ensure_runtime_available(state: AgentSessionState) -> None:
        elapsed = (datetime.utcnow() - state.started_at).total_seconds()
        if elapsed > state.constraints.timeout_seconds:
            raise ExecutorError("RUN_TIMEOUT", "任务执行超出总超时预算")
