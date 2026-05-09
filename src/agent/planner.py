"""Agent Planner 实现。"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Callable, Optional

from src.agent.prompts import build_planner_prompt, build_replan_prompt
from src.agent.registry import ToolRegistry, create_default_tool_registry
from src.agent.schemas import AgentConstraints, AgentPlan, AgentStep

if TYPE_CHECKING:
    from src.core.llm_provider import LLMProvider


class PlannerError(ValueError):
    """Planner 结构化错误。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AgentPlanner:
    """将 task 转换为结构化计划。"""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        llm_provider: Optional["LLMProvider"] = None,
        response_generator: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.registry = registry or create_default_tool_registry()
        self.llm_provider = llm_provider
        self.response_generator = response_generator

    def build_plan(
        self,
        *,
        task: str,
        constraints: Optional[AgentConstraints] = None,
        route_context: str = "无额外路由提示。",
    ) -> AgentPlan:
        """生成并校验结构化计划。"""
        if not task or not task.strip():
            raise PlannerError("INVALID_TASK", "任务不能为空")

        constraints = constraints or AgentConstraints()
        prompt = build_planner_prompt(
            task=task.strip(),
            available_tools=self.registry.format_for_planner(),
            max_iterations=constraints.max_iterations,
            constraints=self._format_constraints(constraints),
            route_context=route_context,
        )

        raw_response = self._generate_plan_response(prompt)
        plan = self._parse_plan_response(raw_response, task=task.strip(), constraints=constraints)
        self._validate_plan(plan, constraints)
        return plan

    def rebuild_plan(
        self,
        *,
        task: str,
        original_plan: AgentPlan,
        completed_steps: list[AgentStep],
        failed_step: AgentStep,
        failure_reason: str,
        constraints: Optional[AgentConstraints] = None,
    ) -> AgentPlan:
        """基于失败上下文生成新的剩余计划。"""
        constraints = constraints or AgentConstraints()
        remaining_budget = max(constraints.max_iterations - len(completed_steps), 0)
        prompt = build_replan_prompt(
            task=task.strip(),
            available_tools=self.registry.format_for_planner(),
            constraints=self._format_constraints(constraints),
            remaining_budget=str(remaining_budget),
            original_plan=json.dumps(original_plan.model_dump(mode="json"), ensure_ascii=False, indent=2),
            completed_steps=json.dumps(
                [step.model_dump(mode="json") for step in completed_steps],
                ensure_ascii=False,
                indent=2,
            ),
            failed_step=json.dumps(failed_step.model_dump(mode="json"), ensure_ascii=False, indent=2),
            failure_reason=failure_reason,
        )
        raw_response = self._generate_plan_response(prompt)
        plan = self._parse_plan_response(raw_response, task=task.strip(), constraints=constraints)
        self._validate_plan(plan, constraints)
        return plan

    def _generate_plan_response(self, prompt: str) -> str:
        """调用 LLM 或注入的生成器。"""
        if self.response_generator is not None:
            return self.response_generator(prompt)

        from src.core.llm_provider import create_llm_provider

        llm = self.llm_provider or create_llm_provider(temperature=0.1)
        return llm.generate(prompt)

    def _parse_plan_response(
        self,
        response: str,
        *,
        task: str,
        constraints: AgentConstraints,
    ) -> AgentPlan:
        """从模型输出中解析 JSON 计划。"""
        if not response or not response.strip():
            return self._build_fallback_plan(task=task, constraints=constraints)

        content = response.strip()
        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if fenced_match:
            content = fenced_match.group(1).strip()
        else:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                content = json_match.group(0).strip()
            else:
                array_match = re.search(r"\[.*\]", content, re.DOTALL)
                if array_match:
                    content = array_match.group(0).strip()

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            return self._build_fallback_plan(task=task, constraints=constraints)

        normalized = self._normalize_payload(payload, task=task, constraints=constraints)
        try:
            steps = [self._normalize_step(step, index=index, task=task, constraints=constraints) for index, step in enumerate(normalized["steps"], start=1)]
            return AgentPlan(summary=normalized["summary"], steps=steps)
        except PlannerError:
            raise
        except Exception:
            return self._build_fallback_plan(task=task, constraints=constraints)

    def _validate_plan(self, plan: AgentPlan, constraints: AgentConstraints) -> None:
        """校验结构化计划。"""
        if not plan.summary.strip():
            raise PlannerError("INVALID_PLAN", "计划 summary 不能为空")

        if not plan.steps:
            raise PlannerError("INVALID_PLAN", "计划 steps 不能为空")

        if len(plan.steps) > constraints.max_iterations:
            raise PlannerError(
                "INVALID_PLAN",
                f"计划步数 {len(plan.steps)} 超过限制 {constraints.max_iterations}",
            )

        seen_step_ids: set[str] = set()
        for step in plan.steps:
            if step.step_id in seen_step_ids:
                raise PlannerError("INVALID_PLAN", f"重复的 step_id: {step.step_id}")
            seen_step_ids.add(step.step_id)

            if not step.tool_name.strip():
                raise PlannerError("INVALID_PLAN", f"步骤 {step.step_id} 缺少 tool_name")

            if not step.goal.strip():
                raise PlannerError("INVALID_PLAN", f"步骤 {step.step_id} 缺少 goal")

            if self.registry.get(step.tool_name) is None:
                raise PlannerError("INVALID_PLAN", f"步骤 {step.step_id} 使用了未知工具: {step.tool_name}")

            if not isinstance(step.tool_input, dict):
                raise PlannerError("INVALID_PLAN", f"步骤 {step.step_id} 的 tool_input 必须是对象")

            if not step.expected_output.strip():
                raise PlannerError("INVALID_PLAN", f"步骤 {step.step_id} 缺少 expected_output")

    def _normalize_payload(
        self,
        payload: object,
        *,
        task: str,
        constraints: AgentConstraints,
    ) -> dict[str, object]:
        if isinstance(payload, list):
            steps_payload = payload
            summary = ""
        elif isinstance(payload, dict):
            summary = (
                payload.get("summary")
                or payload.get("plan_summary")
                or payload.get("objective")
                or payload.get("goal")
                or ""
            )
            steps_payload = (
                payload.get("steps")
                or payload.get("plan")
                or payload.get("items")
                or payload.get("actions")
                or []
            )
        else:
            return self._build_fallback_payload(task=task, constraints=constraints)

        if not isinstance(steps_payload, list) or not steps_payload:
            return self._build_fallback_payload(task=task, constraints=constraints)

        if not isinstance(summary, str) or not summary.strip():
            first_title = ""
            if isinstance(steps_payload[0], dict):
                first_title = str(
                    steps_payload[0].get("title")
                    or steps_payload[0].get("name")
                    or steps_payload[0].get("goal")
                    or steps_payload[0].get("tool_name")
                    or "执行任务"
                ).strip()
            summary = f"围绕任务“{task[:40]}”执行计划，优先完成：{first_title or '执行任务'}。"

        return {"summary": summary, "steps": steps_payload}

    def _normalize_step(
        self,
        step_payload: object,
        *,
        index: int,
        task: str,
        constraints: AgentConstraints,
    ) -> AgentStep:
        if not isinstance(step_payload, dict):
            raise PlannerError("INVALID_PLAN", "计划中的 step 必须是对象")

        tool_name = str(
            step_payload.get("tool_name")
            or step_payload.get("tool")
            or step_payload.get("action")
            or ""
        ).strip()
        if not tool_name:
            tool_name = self._infer_tool_name(task=task, constraints=constraints)

        title = str(
            step_payload.get("title")
            or step_payload.get("name")
            or step_payload.get("goal")
            or f"执行步骤 {index}"
        ).strip()
        goal = str(step_payload.get("goal") or step_payload.get("objective") or title).strip()

        tool_input = step_payload.get("tool_input")
        if tool_input is None:
            tool_input = step_payload.get("input")
        if tool_input is None:
            tool_input = step_payload.get("args")
        if tool_input is None:
            tool_input = step_payload.get("parameters")
        if not isinstance(tool_input, dict):
            tool_input = self._default_tool_input(tool_name=tool_name, task=task, constraints=constraints)
        else:
            tool_input = self._normalize_tool_input(
                tool_name=tool_name,
                tool_input=tool_input,
                task=task,
                constraints=constraints,
            )

        expected_output = str(
            step_payload.get("expected_output")
            or step_payload.get("output")
            or step_payload.get("expected")
            or self._default_expected_output(tool_name=tool_name, title=title)
        ).strip()
        step_id = str(step_payload.get("step_id") or step_payload.get("id") or f"step_{index}").strip()

        return AgentStep(
            step_id=step_id,
            title=title,
            goal=goal,
            tool_name=tool_name,
            tool_input=tool_input,
            expected_output=expected_output,
        )

    def _build_fallback_plan(self, *, task: str, constraints: AgentConstraints) -> AgentPlan:
        payload = self._build_fallback_payload(task=task, constraints=constraints)
        return AgentPlan(
            summary=str(payload["summary"]),
            steps=[
                self._normalize_step(step, index=index, task=task, constraints=constraints)
                for index, step in enumerate(payload["steps"], start=1)
            ],
        )

    def _build_fallback_payload(self, *, task: str, constraints: AgentConstraints) -> dict[str, object]:
        tool_name = self._infer_tool_name(task=task, constraints=constraints)
        title = self._default_step_title(tool_name=tool_name, task=task)
        return {
            "summary": f"围绕任务“{task[:40]}”生成保底执行计划。",
            "steps": [
                {
                    "step_id": "step_1",
                    "title": title,
                    "goal": f"为任务“{task[:40]}”获取可用信息。",
                    "tool_name": tool_name,
                    "tool_input": self._default_tool_input(tool_name=tool_name, task=task, constraints=constraints),
                    "expected_output": self._default_expected_output(tool_name=tool_name, title=title),
                }
            ],
        }

    def _infer_tool_name(self, *, task: str, constraints: AgentConstraints) -> str:
        normalized_task = task.lower()
        if re.fullmatch(r"[\d\s\+\-\*/\(\)\.%]+", normalized_task):
            return "calculator"
        if any(keyword in task for keyword in ("多少文档", "文档数量", "集合数量", "知识库数量", "metadata", "元数据", "集合信息")):
            return "document_metadata"
        if constraints.allow_web_search and any(keyword in task for keyword in ("最新", "今天", "近期", "新闻", "网络", "网页", "互联网")):
            return "web_search"
        if any(keyword in task for keyword in ("总结", "概括", "解释", "回答", "你好", "是什么")):
            return "direct_answer"
        if any(keyword in task for keyword in ("有哪些文档", "文档列表", "集合", "文件类型")):
            return "document_catalog"
        return "direct_answer"

    def _default_tool_input(
        self,
        *,
        tool_name: str,
        task: str,
        constraints: AgentConstraints,
    ) -> dict[str, object]:
        if tool_name == "calculator":
            return {"expression": task.strip()}
        if tool_name == "clarify":
            return {"task": task.strip()}
        if tool_name == "direct_answer":
            return {"question": task.strip()}
        if tool_name == "document_catalog":
            return {"action": "list_documents"}
        if tool_name == "document_read":
            return {"source": task.strip(), "max_chars": 4000}
        if tool_name == "document_metadata":
            return {"action": "summary"}
        if tool_name == "web_search":
            return {"query": task.strip(), "max_results": constraints.top_k}
        if tool_name == "knowledge_query":
            return {"query": task.strip(), "top_k": constraints.top_k}
        return {"query": task.strip(), "top_k": constraints.top_k}

    def _normalize_tool_input(
        self,
        *,
        tool_name: str,
        tool_input: dict[str, object],
        task: str,
        constraints: AgentConstraints,
    ) -> dict[str, object]:
        normalized_input = dict(tool_input)
        if tool_name == "calculator":
            expression = normalized_input.get("expression") or normalized_input.get("query") or task.strip()
            return {"expression": str(expression).strip()}
        if tool_name == "clarify":
            prompt = normalized_input.get("task") or normalized_input.get("question") or task.strip()
            return {"task": str(prompt).strip()}
        if tool_name == "direct_answer":
            question = normalized_input.get("question") or normalized_input.get("query") or task.strip()
            return {"question": str(question).strip()}
        if tool_name == "document_catalog":
            action = normalized_input.get("action") or "list_documents"
            collection_name = normalized_input.get("collection_name")
            normalized = {"action": str(action).strip()}
            if collection_name:
                normalized["collection_name"] = str(collection_name).strip()
            return normalized
        if tool_name == "document_read":
            source = normalized_input.get("source") or normalized_input.get("file_name") or task.strip()
            max_chars = normalized_input.get("max_chars") or 4000
            normalized = {"source": str(source).strip(), "max_chars": int(max_chars)}
            collection_name = normalized_input.get("collection_name") or normalized_input.get("collection")
            if collection_name:
                normalized["collection_name"] = str(collection_name).strip()
            return normalized
        if tool_name == "document_metadata":
            action = normalized_input.get("action") or "summary"
            collection_name = normalized_input.get("collection_name")
            normalized = {"action": str(action).strip()}
            if collection_name:
                normalized["collection_name"] = collection_name
            return normalized
        if tool_name == "web_search":
            query = normalized_input.get("query") or normalized_input.get("keyword") or task.strip()
            max_results = normalized_input.get("max_results") or normalized_input.get("top_k") or constraints.top_k
            return {"query": str(query).strip(), "max_results": int(max_results)}
        query = normalized_input.get("query") or normalized_input.get("question") or task.strip()
        top_k = normalized_input.get("top_k") or constraints.top_k
        return {"query": str(query).strip(), "top_k": int(top_k)}

    @staticmethod
    def _default_step_title(*, tool_name: str, task: str) -> str:
        titles = {
            "calculator": "执行计算",
            "clarify": "澄清任务",
            "direct_answer": "直接回答问题",
            "document_catalog": "查看知识库目录",
            "document_read": "读取指定文档",
            "document_metadata": "查询知识库元数据",
            "web_search": "补充网络信息",
            "knowledge_query": "基于知识库生成回答",
            "literature_search": "检索相关文献",
        }
        return titles.get(tool_name, f"处理任务：{task[:20]}")

    @staticmethod
    def _default_expected_output(*, tool_name: str, title: str) -> str:
        defaults = {
            "calculator": "获得可直接使用的计算结果。",
            "clarify": "获得继续执行所需的澄清问题。",
            "direct_answer": "获得直接回答内容。",
            "document_catalog": "获得知识库文档、集合或文件类型目录。",
            "document_read": "获得指定文档的正文、元数据与关键摘录。",
            "document_metadata": "获得知识库统计与集合信息。",
            "web_search": "获得相关网页结果与来源。",
            "knowledge_query": "获得基于知识库的归纳回答。",
            "literature_search": "获得相关文献片段与来源。",
        }
        return defaults.get(tool_name, f"完成步骤“{title}”并获得可用结果。")

    @staticmethod
    def _format_constraints(constraints: AgentConstraints) -> str:
        return (
            f"- max_iterations={constraints.max_iterations}\n"
            f"- max_failures={constraints.max_failures}\n"
            f"- timeout_seconds={constraints.timeout_seconds}\n"
            f"- top_k={constraints.top_k}\n"
            f"- allow_web_search={constraints.allow_web_search}\n"
            f"- read_only_tools={constraints.read_only_tools}"
        )


def create_agent_planner(
    *,
    registry: Optional[ToolRegistry] = None,
    llm_provider: Optional["LLMProvider"] = None,
) -> AgentPlanner:
    """创建默认 Planner。"""
    return AgentPlanner(
        registry=registry or create_default_tool_registry(),
        llm_provider=llm_provider,
    )
