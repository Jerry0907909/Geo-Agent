"""Agent Runtime."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Callable, Iterator
from uuid import uuid4

from src.agent.events import (
    AgentEvent,
    create_content_event,
    create_error_event,
    create_final_event,
    create_info_event,
    create_plan_event,
    create_route_event,
    create_step_start_event,
    create_thought_event,
    create_tool_call_event,
    create_tool_result_event,
)
from src.agent.executor import AgentExecutor, ExecutorError
from src.agent.planner import AgentPlanner, PlannerError, create_agent_planner
from src.agent.prompts import build_react_prompt, build_synthesis_prompt
from src.agent.registry import ToolRegistry, create_default_tool_registry
from src.agent.router import AgentTaskRouter, RoutingDecision
from src.agent.schemas import (
    AgentConstraints,
    AgentError,
    AgentPlan,
    AgentPlanResult,
    AgentRunStatus,
    AgentSessionState,
    AgentStep,
    AgentStepStatus,
)
from src.core.llm_provider import create_llm_provider
from src.utils.config import get_config


class AgentRuntime:
    """Single-agent runtime with real-time event streaming."""

    def __init__(
        self,
        planner: AgentPlanner | None = None,
        registry: ToolRegistry | None = None,
        executor: AgentExecutor | None = None,
        task_router: AgentTaskRouter | None = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.registry = registry or create_default_tool_registry()
        self.planner = planner or create_agent_planner(registry=self.registry)
        self.executor = executor or AgentExecutor(registry=self.registry, planner=self.planner)
        self.task_router = task_router or AgentTaskRouter()

    def create_run_state(
        self,
        *,
        task: str,
        conversation_id: int | None = None,
        constraints: AgentConstraints | None = None,
    ) -> AgentSessionState:
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
        state = self.create_run_state(
            task=task,
            conversation_id=conversation_id,
            constraints=constraints,
        )
        state.status = AgentRunStatus.PLANNING
        state.updated_at = datetime.utcnow()

        decision = self.task_router.route(task=task, constraints=state.constraints)
        plan = self._resolve_plan(state=state, decision=decision)
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
        state = self.create_run_state(task=task, conversation_id=conversation_id, constraints=constraints)
        return self.run_state(state)

    def run_state(
        self,
        state: AgentSessionState,
        *,
        on_state_change: Callable[[AgentSessionState], None] | None = None,
        cancel_checker: Callable[[str], bool] | None = None,
    ) -> AgentSessionState:
        for _ in self.iter_state_events(state, on_state_change=on_state_change, cancel_checker=cancel_checker):
            pass
        return state

    def plan_events(
        self,
        *,
        task: str,
        conversation_id: int | None = None,
        constraints: AgentConstraints | None = None,
    ) -> list[AgentEvent]:
        state = self.create_run_state(
            task=task,
            conversation_id=conversation_id,
            constraints=constraints,
        )
        events = [create_info_event(state.run_id, AgentRunStatus.PLANNING.value, conversation_id=conversation_id)]

        try:
            decision = self.task_router.route(task=task, constraints=state.constraints)
            events.append(
                create_route_event(
                    state.run_id,
                    decision.intent,
                    decision.summary,
                    decision.reason,
                    metadata=decision.metadata,
                )
            )
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
        state = self.create_run_state(task=task, conversation_id=conversation_id, constraints=constraints)
        return self.run_state_events(state)

    def run_state_events(
        self,
        state: AgentSessionState,
        *,
        on_state_change: Callable[[AgentSessionState], None] | None = None,
        cancel_checker: Callable[[str], bool] | None = None,
    ) -> tuple[AgentSessionState, list[AgentEvent]]:
        events = list(
            self.iter_state_events(
                state,
                on_state_change=on_state_change,
                cancel_checker=cancel_checker,
            )
        )
        return state, events

    def iter_state_events(
        self,
        state: AgentSessionState,
        *,
        on_state_change: Callable[[AgentSessionState], None] | None = None,
        cancel_checker: Callable[[str], bool] | None = None,
    ) -> Iterator[AgentEvent]:
        execution_start = time.time()

        self._set_state_status(state, AgentRunStatus.PLANNING, on_state_change)
        yield create_info_event(state.run_id, AgentRunStatus.PLANNING.value, conversation_id=state.conversation_id)

        try:
            routing_decision = self.task_router.route(task=state.task, constraints=state.constraints)
            yield create_route_event(
                state.run_id,
                routing_decision.intent,
                routing_decision.summary,
                routing_decision.reason,
                metadata=routing_decision.metadata,
            )

            if self._use_react_runtime() and self._should_use_react(routing_decision):
                state.plan_summary = routing_decision.summary or "Agent 将按需逐步决策并调用工具。"
                state.steps = []
                self._touch_state(state, on_state_change)
                yield create_plan_event(state.run_id, state.plan_summary, [])
                self._set_state_status(state, AgentRunStatus.RUNNING, on_state_change)
                yield create_info_event(state.run_id, AgentRunStatus.RUNNING.value, conversation_id=state.conversation_id)
                yield from self._iter_react_events(
                    state,
                    routing_decision=routing_decision,
                    on_state_change=on_state_change,
                    cancel_checker=cancel_checker,
                )
                final_answer = state.final_answer or self._fallback_final_answer(state)
                state.final_answer = final_answer
                self._set_state_status(state, AgentRunStatus.COMPLETED, on_state_change)
                execution_time = round(time.time() - execution_start, 3)
                yield create_final_event(
                    state.run_id,
                    final_answer,
                    state.sources,
                    execution_time=execution_time,
                )
                return

            planner_started = time.time()
            plan = self._resolve_plan(state=state, decision=routing_decision)
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
            yield create_plan_event(
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

            self._set_state_status(state, AgentRunStatus.RUNNING, on_state_change)
            yield create_info_event(state.run_id, AgentRunStatus.RUNNING.value, conversation_id=state.conversation_id)

            for event in self.executor.iter_execute(
                state,
                plan,
                on_state_change=on_state_change,
                cancel_checker=cancel_checker,
            ):
                yield event

            synthesis_started = time.time()
            state.final_answer = ""
            for chunk in self._stream_synthesis_answer(state):
                state.final_answer += chunk
                self._touch_state(state, on_state_change)
                yield create_content_event(state.run_id, chunk, conversation_id=state.conversation_id)

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
            yield create_final_event(
                state.run_id,
                state.final_answer,
                state.sources,
                execution_time=execution_time,
            )
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
            yield create_error_event(state.run_id, exc.code, exc.message)
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
            yield create_info_event(state.run_id, status.value, conversation_id=state.conversation_id)
            if status != AgentRunStatus.CANCELLED:
                yield create_error_event(state.run_id, exc.code, exc.message)
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
            yield create_error_event(state.run_id, "RUNTIME_ERROR", str(exc))

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
            retrieval_mode="hybrid",
        )

    @staticmethod
    def _format_observations(state: AgentSessionState) -> str:
        lines: list[str] = []
        for step in state.steps:
            if step.status != AgentStepStatus.COMPLETED:
                continue
            lines.append(f"- {step.title} ({step.tool_name}): {step.observation or '无观察结果'}")
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

    def _resolve_plan(self, *, state: AgentSessionState, decision: RoutingDecision) -> AgentPlan:
        if decision.plan is not None:
            return decision.plan
        return self.planner.build_plan(
            task=state.task,
            constraints=state.constraints,
            route_context=decision.route_context or "无额外路由提示。",
        )

    def _iter_react_events(
        self,
        state: AgentSessionState,
        *,
        routing_decision: RoutingDecision,
        on_state_change: Callable[[AgentSessionState], None] | None = None,
        cancel_checker: Callable[[str], bool] | None = None,
    ) -> Iterator[AgentEvent]:
        for iteration in range(1, state.constraints.max_iterations + 1):
            if cancel_checker and cancel_checker(state.run_id):
                raise ExecutorError("RUN_CANCELLED", "运行已取消")
            self._ensure_runtime_available(state)

            react_decision = self._decide_next_action(
                state=state,
                routing_decision=routing_decision,
                iteration=iteration,
            )
            thought_summary = react_decision.get("thought_summary") or f"第 {iteration} 轮决策。"
            yield create_thought_event(
                state.run_id,
                thought_summary,
                iteration=iteration,
                conversation_id=state.conversation_id,
            )

            if react_decision.get("is_final"):
                state.final_answer = str(react_decision.get("final_answer") or "").strip() or self._fallback_final_answer(state)
                self._touch_state(state, on_state_change)
                return

            tool_name = str(react_decision.get("action") or "").strip()
            tool_input = react_decision.get("action_input")
            if not tool_name or not isinstance(tool_input, dict):
                raise ExecutorError("INVALID_REACT_ACTION", "ReAct 未返回合法的工具动作。")

            if tool_name in {"literature_search", "knowledge_query"}:
                tool_input.setdefault("source_mode", self._normalize_source_mode(state.constraints.retrieval_mode))
            if tool_name == "web_search" and not state.constraints.allow_web_search:
                raise ExecutorError("WEB_SEARCH_DISABLED", "当前任务不允许调用外部网络检索。")

            step = AgentStep(
                step_id=f"react_step_{iteration}",
                title=self._default_step_title(tool_name=tool_name, task=state.task),
                goal=thought_summary,
                tool_name=tool_name,
                tool_input=tool_input,
                expected_output=self._default_expected_output(tool_name=tool_name, title=thought_summary),
                reasoning_summary=thought_summary,
                status=AgentStepStatus.RUNNING,
            )
            state.steps.append(step)
            self._touch_state(state, on_state_change)
            yield create_thought_event(
                state.run_id,
                f"准备调用 {tool_name}",
                step_id=step.step_id,
                tool_name=tool_name,
                conversation_id=state.conversation_id,
            )
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
            step.latency_ms = result.latency_ms
            step.sources = result.sources
            step.observation = result.observation
            if result.ok:
                step.status = AgentStepStatus.COMPLETED
                state.sources.extend(result.sources)
            else:
                step.status = AgentStepStatus.FAILED
            self._touch_state(state, on_state_change)
            yield create_tool_result_event(
                state.run_id,
                step.step_id,
                step.tool_name,
                result.ok,
                step.observation or ("工具执行成功" if result.ok else "工具执行失败"),
                result.latency_ms,
                sources=result.sources,
                error=result.error.model_dump() if result.error else None,
            )
            if step.status != AgentStepStatus.COMPLETED:
                continue

        if not state.final_answer:
            state.final_answer = self._fallback_final_answer(state)

    def _decide_next_action(
        self,
        *,
        state: AgentSessionState,
        routing_decision: RoutingDecision,
        iteration: int,
    ) -> dict[str, object]:
        prompt = build_react_prompt(
            task=state.task,
            available_tools=self.registry.format_for_planner(),
            constraints=self._format_constraints(state.constraints),
            route_context=routing_decision.route_context or routing_decision.reason or "无额外路由提示。",
            iteration=iteration,
            max_iterations=state.constraints.max_iterations,
            observations=self._format_observations(state),
            sources=self._format_sources(state),
        )
        try:
            llm = create_llm_provider(temperature=0.2)
            raw = llm.generate(prompt).strip()
            payload = self._extract_json(raw)
            if not isinstance(payload, dict):
                raise ValueError("ReAct 输出不是对象")
            if payload.get("is_final"):
                return {
                    "thought_summary": payload.get("thought_summary") or "信息已足够，准备收敛答案。",
                    "is_final": True,
                    "final_answer": str(payload.get("final_answer") or "").strip(),
                }
            action = str(payload.get("action") or "").strip()
            action_input = payload.get("action_input")
            if not action or not isinstance(action_input, dict):
                raise ValueError("ReAct 缺少合法 action/action_input")
            return {
                "thought_summary": payload.get("thought_summary") or f"准备调用 {action}。",
                "is_final": False,
                "action": action,
                "action_input": action_input,
            }
        except Exception as exc:
            self.logger.warning("[agent] react_decision_fallback run_id=%s iteration=%s error=%s", state.run_id, iteration, exc)
            fallback_tool = "knowledge_query" if iteration >= max(2, state.constraints.max_iterations // 2) else "literature_search"
            return {
                "thought_summary": "优先补充相关证据，再决定是否直接收敛答案。",
                "is_final": False,
                "action": fallback_tool,
                "action_input": {
                    "query": state.task,
                    "top_k": state.constraints.top_k,
                    "source_mode": self._normalize_source_mode(state.constraints.retrieval_mode),
                },
            }

    @staticmethod
    def _extract_json(raw_text: str) -> dict[str, object]:
        cleaned = raw_text.strip()
        if "```" in cleaned:
            cleaned = cleaned.split("```")[1]
            cleaned = cleaned.replace("json", "", 1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("未找到 JSON 对象")
        return json.loads(cleaned[start : end + 1])

    @staticmethod
    def _format_constraints(constraints: AgentConstraints) -> str:
        return (
            f"max_iterations={constraints.max_iterations}\n"
            f"top_k={constraints.top_k}\n"
            f"allow_web_search={constraints.allow_web_search}\n"
            f"retrieval_mode={constraints.retrieval_mode}\n"
            f"read_only_tools={constraints.read_only_tools}"
        )

    @staticmethod
    def _use_react_runtime() -> bool:
        config = get_config()
        return str(config.get_agent_config().get("agent_type", "react")).strip().lower() == "react"

    @staticmethod
    def _should_use_react(decision: RoutingDecision) -> bool:
        return decision.intent not in {"clarify", "calculate", "direct_answer", "document_read", "document_catalog"}

    @staticmethod
    def _normalize_source_mode(source_mode: str) -> str:
        normalized = str(source_mode or "hybrid").strip().lower()
        if normalized not in {"local", "external", "hybrid"}:
            return "hybrid"
        return normalized

    def _stream_synthesis_answer(self, state: AgentSessionState) -> Iterator[str]:
        shortcut = self._shortcut_final_answer(state)
        if shortcut is not None:
            yield shortcut
            return

        prompt = build_synthesis_prompt(
            task=state.task,
            plan_summary=state.plan_summary or "未提供",
            step_observations=self._format_observations(state),
            sources=self._format_sources(state),
        )
        try:
            from src.core.llm_provider import create_llm_provider

            llm = create_llm_provider(temperature=0.2)
            for chunk in llm.stream_generate(prompt):
                if chunk:
                    yield chunk
        except Exception:
            yield self._fallback_final_answer(state)

    @staticmethod
    def _shortcut_final_answer(state: AgentSessionState) -> str | None:
        completed_steps = [step for step in state.steps if step.status == AgentStepStatus.COMPLETED]
        if len(completed_steps) != 1:
            return None
        step = completed_steps[0]
        if step.tool_name in {"clarify", "direct_answer", "calculator"} and step.observation:
            return step.observation
        return None

    @staticmethod
    def _fallback_final_answer(state: AgentSessionState) -> str:
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

    @staticmethod
    def _default_step_title(*, tool_name: str, task: str) -> str:
        titles = {
            "calculator": "执行计算",
            "clarify": "请求澄清",
            "direct_answer": "直接回答",
            "document_catalog": "查看知识库目录",
            "document_read": "读取指定文档",
            "document_metadata": "查询知识库元数据",
            "web_search": "补充网络信息",
            "knowledge_query": "基于检索结果回答",
            "literature_search": "检索相关证据",
        }
        return titles.get(tool_name, f"处理任务：{task[:20]}")

    @staticmethod
    def _default_expected_output(*, tool_name: str, title: str) -> str:
        defaults = {
            "calculator": "获得可直接使用的计算结果。",
            "clarify": "获得一条明确的补充问题。",
            "direct_answer": "获得直接回答。",
            "document_catalog": "获得知识库目录或统计。",
            "document_read": "获得文档摘录与元数据。",
            "document_metadata": "获得知识库概况。",
            "web_search": "获得可引用的网页结果。",
            "knowledge_query": "获得带来源的归纳答案。",
            "literature_search": "获得相关证据片段。",
        }
        return defaults.get(tool_name, f"完成步骤“{title}”并获得可用结果。")

    @staticmethod
    def _ensure_runtime_available(state: AgentSessionState) -> None:
        elapsed = (datetime.utcnow() - state.started_at).total_seconds()
        if elapsed > state.constraints.timeout_seconds:
            raise ExecutorError("RUN_TIMEOUT", "任务执行超出总超时预算")


def create_agent_runtime() -> AgentRuntime:
    registry = create_default_tool_registry()
    planner = create_agent_planner(registry=registry)
    return AgentRuntime(planner=planner, registry=registry)
