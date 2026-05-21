"""Agent Runtime。"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Callable
from uuid import uuid4

from src.agent.events import (
    AgentEvent,
    create_error_event,
    create_final_event,
    create_info_event,
    create_plan_event,
)
from src.agent.executor import AgentExecutor, ExecutorError
from src.agent.planner import AgentPlanner, PlannerError, create_agent_planner
from src.agent.prompts import build_synthesis_prompt
from src.agent.registry import ToolRegistry, create_default_tool_registry
from src.agent.schemas import AgentConstraints, AgentError, AgentPlan, AgentPlanResult, AgentRunStatus, AgentSessionState, AgentStepStatus
from src.utils.config import get_config


class AgentRuntime:
    """单 Agent 运行时骨架。"""

    def __init__(
        self,
        planner: AgentPlanner | None = None,
        registry: ToolRegistry | None = None,
        executor: AgentExecutor | None = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.registry = registry or create_default_tool_registry()
        self.planner = planner or create_agent_planner(registry=self.registry)
        self.executor = executor or AgentExecutor(registry=self.registry, planner=self.planner)

    def create_run_state(
        self,
        *,
        task: str,
        conversation_id: int | None = None,
        constraints: AgentConstraints | None = None,
    ) -> AgentSessionState:
        """创建初始运行状态。"""
        now = datetime.utcnow()
        return AgentSessionState(
            run_id=f"run_{uuid4().hex[:12]}",
            conversation_id=conversation_id,
            status=AgentRunStatus.QUEUED,
            task=task,
            constraints=constraints or self._constraints_from_config(),
            started_at=now,
            updated_at=now,
        )

    def plan_task(
        self,
        *,
        task: str,
        conversation_id: int | None = None,
        constraints: AgentConstraints | None = None,
    ) -> AgentPlanResult:
        """仅执行规划阶段。"""
        state = self.create_run_state(
            task=task,
            conversation_id=conversation_id,
            constraints=constraints,
        )
        state.status = AgentRunStatus.PLANNING
        state.updated_at = datetime.utcnow()

        plan = self.planner.build_plan(task=task, constraints=state.constraints)

        state.plan_summary = plan.summary
        state.steps = plan.steps
        state.status = AgentRunStatus.QUEUED
        state.updated_at = datetime.utcnow()
        return AgentPlanResult(state=state, plan=plan)

    def run_task(
        self,
        *,
        task: str,
        conversation_id: int | None = None,
        constraints: AgentConstraints | None = None,
    ) -> AgentSessionState:
        """执行完整 Agent 闭环。"""
        state = self.create_run_state(task=task, conversation_id=conversation_id, constraints=constraints)
        return self.run_state(state)

    def run_state(
        self,
        state: AgentSessionState,
        *,
        on_state_change: Callable[[AgentSessionState], None] | None = None,
        cancel_checker: Callable[[str], bool] | None = None,
    ) -> AgentSessionState:
        """执行已有 run state。"""
        final_state, _ = self._run_internal(
            state,
            on_state_change=on_state_change,
            cancel_checker=cancel_checker,
            collect_events=False,
        )
        return final_state

    def plan_events(
        self,
        *,
        task: str,
        conversation_id: int | None = None,
        constraints: AgentConstraints | None = None,
    ) -> list[AgentEvent]:
        """输出规划阶段的标准事件。"""
        state = self.create_run_state(
            task=task,
            conversation_id=conversation_id,
            constraints=constraints,
        )
        events = [create_info_event(state.run_id, AgentRunStatus.PLANNING.value, conversation_id=conversation_id)]

        try:
            result = self.plan_task(task=task, conversation_id=conversation_id, constraints=constraints)
        except PlannerError as exc:
            state.status = AgentRunStatus.FAILED
            state.error = AgentError(code=exc.code, message=exc.message)
            state.updated_at = datetime.utcnow()
            events.append(create_error_event(state.run_id, exc.code, exc.message))
            return events

        plan = result.plan
        events.append(
            create_plan_event(
                result.state.run_id,
                plan.summary,
                [
                    {
                        "step_id": step.step_id,
                        "title": step.title,
                        "goal": step.goal,
                        "tool_name": step.tool_name,
                    }
                    for step in plan.steps
                ],
            )
        )
        return events

    def run_events(
        self,
        *,
        task: str,
        conversation_id: int | None = None,
        constraints: AgentConstraints | None = None,
    ) -> tuple[AgentSessionState, list[AgentEvent]]:
        """输出完整执行过程事件。"""
        state = self.create_run_state(task=task, conversation_id=conversation_id, constraints=constraints)
        return self.run_state_events(state)

    def run_state_events(
        self,
        state: AgentSessionState,
        *,
        on_state_change: Callable[[AgentSessionState], None] | None = None,
        cancel_checker: Callable[[str], bool] | None = None,
    ) -> tuple[AgentSessionState, list[AgentEvent]]:
        """执行已有 run state 并返回标准事件。"""
        return self._run_internal(
            state,
            on_state_change=on_state_change,
            cancel_checker=cancel_checker,
            collect_events=True,
        )

    def _run_internal(
        self,
        state: AgentSessionState,
        *,
        on_state_change: Callable[[AgentSessionState], None] | None,
        cancel_checker: Callable[[str], bool] | None,
        collect_events: bool,
    ) -> tuple[AgentSessionState, list[AgentEvent]]:
        events: list[AgentEvent] = []
        execution_start = time.time()

        def emit(event: AgentEvent) -> None:
            if collect_events:
                events.append(event)

        self._set_state_status(state, AgentRunStatus.PLANNING, on_state_change)
        emit(create_info_event(state.run_id, AgentRunStatus.PLANNING.value, conversation_id=state.conversation_id))

        try:
            planner_started = time.time()
            plan = self.planner.build_plan(task=state.task, constraints=state.constraints)
            planner_latency_ms = int((time.time() - planner_started) * 1000)
            state.plan_summary = plan.summary
            state.steps = plan.steps
            self._touch_state(state, on_state_change)
            self.logger.info(
                "[agent] plan_ready run_id=%s conversation_id=%s planner_latency_ms=%s steps=%s",
                state.run_id,
                state.conversation_id,
                planner_latency_ms,
                len(plan.steps),
            )
            emit(
                create_plan_event(
                    state.run_id,
                    plan.summary,
                    [
                        {
                            "step_id": step.step_id,
                            "title": step.title,
                            "goal": step.goal,
                            "tool_name": step.tool_name,
                        }
                        for step in plan.steps
                    ],
                )
            )

            self._set_state_status(state, AgentRunStatus.RUNNING, on_state_change)
            emit(create_info_event(state.run_id, AgentRunStatus.RUNNING.value, conversation_id=state.conversation_id))
            self.executor.execute(
                state,
                plan,
                on_event=emit,
                on_state_change=on_state_change,
                cancel_checker=cancel_checker,
            )

            synthesis_started = time.time()
            state.final_answer = self._synthesize_answer(state)
            synthesis_latency_ms = int((time.time() - synthesis_started) * 1000)
            execution_time = round(time.time() - execution_start, 3)
            self._set_state_status(state, AgentRunStatus.COMPLETED, on_state_change)
            self.logger.info(
                "[agent] run_completed run_id=%s conversation_id=%s synthesis_latency_ms=%s total_latency_ms=%s sources=%s",
                state.run_id,
                state.conversation_id,
                synthesis_latency_ms,
                int(execution_time * 1000),
                len(state.sources),
            )
            emit(
                create_final_event(
                    state.run_id,
                    state.final_answer,
                    state.sources,
                    execution_time=execution_time,
                )
            )
            return state, events
        except PlannerError as exc:
            self._set_failure_state(
                state,
                status=AgentRunStatus.FAILED,
                error=AgentError(code=exc.code, message=exc.message),
                on_state_change=on_state_change,
            )
            self.logger.warning(
                "[agent] plan_failed run_id=%s conversation_id=%s error_code=%s message=%s",
                state.run_id,
                state.conversation_id,
                exc.code,
                exc.message,
            )
            emit(create_error_event(state.run_id, exc.code, exc.message))
            return state, events
        except ExecutorError as exc:
            status = AgentRunStatus.CANCELLED if exc.code == "RUN_CANCELLED" else AgentRunStatus.FAILED
            self._set_failure_state(
                state,
                status=status,
                error=AgentError(code=exc.code, message=exc.message),
                on_state_change=on_state_change,
            )
            self.logger.warning(
                "[agent] run_stopped run_id=%s conversation_id=%s status=%s error_code=%s message=%s",
                state.run_id,
                state.conversation_id,
                status.value,
                exc.code,
                exc.message,
            )
            emit(create_info_event(state.run_id, status.value, conversation_id=state.conversation_id))
            if status != AgentRunStatus.CANCELLED:
                emit(create_error_event(state.run_id, exc.code, exc.message))
            return state, events
        except Exception as exc:
            self._set_failure_state(
                state,
                status=AgentRunStatus.FAILED,
                error=AgentError(code="RUNTIME_ERROR", message=str(exc)),
                on_state_change=on_state_change,
            )
            self.logger.exception(
                "[agent] runtime_error run_id=%s conversation_id=%s",
                state.run_id,
                state.conversation_id,
            )
            emit(create_error_event(state.run_id, "RUNTIME_ERROR", str(exc)))
            return state, events

    @staticmethod
    def _constraints_from_config() -> AgentConstraints:
        config = get_config()
        agent_cfg = config.get_agent_config()
        return AgentConstraints(
            max_iterations=int(agent_cfg.get("max_iterations", 8)),
            max_failures=2,
            timeout_seconds=int(agent_cfg.get("timeout", 300)),
            top_k=int(config.get_rag_config().get("top_k", 5)),
            allow_web_search=True,
            read_only_tools=True,
        )

    @staticmethod
    def _format_observations(state: AgentSessionState) -> str:
        lines: list[str] = []
        for step in state.steps:
            if step.status != AgentStepStatus.COMPLETED:
                continue
            lines.append(
                f"- {step.title} ({step.tool_name}): {step.observation or '无观察结果'}"
            )
        return "\n".join(lines) if lines else "- 暂无有效 observation"

    @staticmethod
    def _format_sources(state: AgentSessionState) -> str:
        if not state.sources:
            return "- 暂无来源"
        lines = []
        for index, source in enumerate(state.sources, start=1):
            label = source.get("source", "未知来源")
            content = str(source.get("content", ""))[:120]
            lines.append(f"- 来源{index}: {label} | {content}")
        return "\n".join(lines)

    def _synthesize_answer(self, state: AgentSessionState) -> str:
        """基于 observation 生成最终答案。"""
        prompt = build_synthesis_prompt(
            task=state.task,
            plan_summary=state.plan_summary or "未提供",
            step_observations=self._format_observations(state),
            sources=self._format_sources(state),
        )
        try:
            from src.core.llm_provider import create_llm_provider

            llm = create_llm_provider(temperature=0.2)
            return llm.generate(prompt)
        except Exception:
            completed = [step.observation for step in state.steps if step.observation]
            if completed:
                return "\n".join(completed)
            if state.error:
                return f"任务执行失败：{state.error.message}"
            return "未获得足够信息生成最终答案。"

    @staticmethod
    def _touch_state(
        state: AgentSessionState,
        on_state_change: Callable[[AgentSessionState], None] | None,
    ) -> None:
        state.updated_at = datetime.utcnow()
        if on_state_change:
            on_state_change(state)

    def _set_state_status(
        self,
        state: AgentSessionState,
        status: AgentRunStatus,
        on_state_change: Callable[[AgentSessionState], None] | None,
    ) -> None:
        state.status = status
        self._touch_state(state, on_state_change)

    def _set_failure_state(
        self,
        state: AgentSessionState,
        *,
        status: AgentRunStatus,
        error: AgentError,
        on_state_change: Callable[[AgentSessionState], None] | None,
    ) -> None:
        state.status = status
        state.error = error
        self._touch_state(state, on_state_change)


def create_agent_runtime() -> AgentRuntime:
    """创建默认 Runtime。"""
    registry = create_default_tool_registry()
    planner = create_agent_planner(registry=registry)
    return AgentRuntime(planner=planner, registry=registry)
