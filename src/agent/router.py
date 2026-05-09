"""Pre-planner task router for Agent runtime."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from src.agent.schemas import AgentConstraints, AgentPlan, AgentStep


@dataclass
class RoutingDecision:
    """Lightweight routing result before planner execution."""

    intent: str
    summary: str
    reason: str
    requires_planner: bool = False
    route_context: str = ""
    plan: Optional[AgentPlan] = None
    metadata: dict[str, object] = field(default_factory=dict)


class AgentTaskRouter:
    """Heuristic router that prevents every task from falling into RAG-first flow."""

    _GREETING_KEYWORDS = ("你好", "hello", "hi", "嗨", "早上好", "晚上好")
    _LATEST_KEYWORDS = ("最新", "今天", "近期", "新闻", "刚刚", "实时")
    _DOC_CATALOG_KEYWORDS = ("有哪些文档", "文档列表", "列出文档", "知识库里有什么", "有哪些集合", "列出集合", "文件类型")
    _DOC_READ_VERBS = ("查看", "读取", "打开", "阅读", "总结", "概括", "分析")
    _RESEARCH_KEYWORDS = ("文献", "论文", "资料", "知识库", "矿床", "地质", "岩石", "构造", "成矿")
    _COMPLEX_CONNECTORS = ("然后", "再", "同时", "并且", "最后", "分别", "对比", "比较")

    def route(self, *, task: str, constraints: AgentConstraints) -> RoutingDecision:
        normalized_task = task.strip()
        lowered = normalized_task.lower()

        if not normalized_task:
            return RoutingDecision(
                intent="clarify",
                summary="任务为空，需要用户补充。",
                reason="输入为空，无法规划或执行。",
                plan=self._single_step_plan(
                    tool_name="clarify",
                    title="请求补充任务",
                    goal="请用户补充明确的任务目标、对象或范围。",
                    tool_input={"task": normalized_task},
                    expected_output="返回一个简洁的澄清问题。",
                ),
            )

        if self._looks_like_math_expression(lowered):
            return RoutingDecision(
                intent="calculate",
                summary="任务属于直接计算。",
                reason="输入主要由数学表达式组成，优先走计算工具。",
                plan=self._single_step_plan(
                    tool_name="calculator",
                    title="执行数学计算",
                    goal="计算用户提供的表达式。",
                    tool_input={"expression": normalized_task},
                    expected_output="返回准确的计算结果。",
                ),
            )

        if self._is_simple_chat(normalized_task):
            return RoutingDecision(
                intent="direct_answer",
                summary="任务更像直接对话，不需要强制工具链。",
                reason="输入属于问候、解释或一般问答，可直接回答并避免无意义检索。",
                plan=self._single_step_plan(
                    tool_name="direct_answer",
                    title="直接回答用户问题",
                    goal="基于通用模型能力直接给出清晰回答。",
                    tool_input={"question": normalized_task},
                    expected_output="返回直接、清晰的回答。",
                ),
            )

        if self._needs_clarification(normalized_task):
            return RoutingDecision(
                intent="clarify",
                summary="任务目标不充分，需要先澄清。",
                reason="输入过短或缺少对象，直接检索/执行会产生无效开销。",
                plan=self._single_step_plan(
                    tool_name="clarify",
                    title="请求补充上下文",
                    goal="向用户追问缺失的对象、范围或输出要求。",
                    tool_input={"task": normalized_task},
                    expected_output="返回一个准确的澄清问题。",
                ),
            )

        source_name = self._extract_document_name(normalized_task)
        if source_name:
            return RoutingDecision(
                intent="document_read",
                summary="任务指向特定文档，优先读取正文。",
                reason=f"识别到文档名 {source_name}，直接读取文档比先做向量检索更合适。",
                plan=self._single_step_plan(
                    tool_name="document_read",
                    title="读取指定文档",
                    goal="读取目标文档的正文、元数据与可用摘录。",
                    tool_input={"source": source_name, "max_chars": 6000},
                    expected_output="返回文档正文摘要、关键摘录与来源信息。",
                ),
                metadata={"source": source_name},
            )

        if any(keyword in normalized_task for keyword in self._DOC_CATALOG_KEYWORDS):
            action = "list_documents"
            if "集合" in normalized_task:
                action = "list_collections"
            elif "文件类型" in normalized_task:
                action = "file_types"
            return RoutingDecision(
                intent="document_catalog",
                summary="任务属于知识库结构查看。",
                reason="用户在问目录、集合或文件类型，不需要先做 RAG。",
                plan=self._single_step_plan(
                    tool_name="document_catalog",
                    title="查询知识库目录",
                    goal="列出知识库中的文档或集合信息。",
                    tool_input={"action": action},
                    expected_output="返回结构化目录、集合或文件类型统计。",
                ),
                metadata={"action": action},
            )

        if constraints.allow_web_search and any(keyword in normalized_task for keyword in self._LATEST_KEYWORDS):
            return RoutingDecision(
                intent="web_research",
                summary="任务具有时效性，需要联网补充。",
                reason="检测到明显的时效词，应优先检索网络信息而不是默认本地 RAG。",
                plan=self._single_step_plan(
                    tool_name="web_search",
                    title="检索实时网络信息",
                    goal="获取与任务相关的最新网页结果和来源。",
                    tool_input={"query": normalized_task, "max_results": constraints.top_k},
                    expected_output="返回可引用的网页结果列表。",
                ),
            )

        if self._is_complex_task(normalized_task):
            return RoutingDecision(
                intent="complex_agent",
                summary="任务包含多阶段动作，交给 Planner 编排。",
                reason="检测到复合连接词或多目标动作，需要多步规划。",
                requires_planner=True,
                route_context=(
                    "这是一个复合任务。优先只规划必要步骤；只有确实需要证据时才调用检索类工具；"
                    "如果某一步可以直接回答，不要为了形式强行走 RAG。"
                ),
            )

        if any(keyword in normalized_task for keyword in self._RESEARCH_KEYWORDS):
            return RoutingDecision(
                intent="knowledge_grounding",
                summary="任务需要依托本地知识库证据。",
                reason="输入明显指向专业地质知识或文献依据，先检索证据再综合回答。",
                plan=self._single_step_plan(
                    tool_name="literature_search",
                    title="检索本地知识证据",
                    goal="查找与任务最相关的知识库片段。",
                    tool_input={"query": normalized_task, "top_k": constraints.top_k},
                    expected_output="返回与问题最相关的文献片段和来源。",
                ),
            )

        return RoutingDecision(
            intent="planner",
            summary="任务不适合硬编码路由，交给 Planner 细化。",
            reason="未命中单步直达模式，保留 Planner 自主编排能力。",
            requires_planner=True,
            route_context=(
                "默认不要优先选择 knowledge_query 或 literature_search。"
                "先判断是否可以 direct_answer、clarify、document_catalog、document_read 或 calculator。"
                "只有任务明确需要证据或资料时才使用检索类工具。"
            ),
        )

    @staticmethod
    def _single_step_plan(
        *,
        tool_name: str,
        title: str,
        goal: str,
        tool_input: dict[str, object],
        expected_output: str,
    ) -> AgentPlan:
        return AgentPlan(
            summary=goal,
            steps=[
                AgentStep(
                    step_id="step_1",
                    title=title,
                    goal=goal,
                    tool_name=tool_name,
                    tool_input=tool_input,
                    expected_output=expected_output,
                )
            ],
        )

    @staticmethod
    def _looks_like_math_expression(task: str) -> bool:
        return bool(re.fullmatch(r"[\d\s\+\-\*/\(\)\.%]+", task))

    def _needs_clarification(self, task: str) -> bool:
        stripped = task.strip()
        if len(stripped) <= 3:
            return True
        vague_patterns = (
            "帮我看看",
            "分析一下",
            "看一下",
            "帮我做",
            "处理一下",
        )
        return any(pattern == stripped or stripped.endswith(pattern) for pattern in vague_patterns)

    def _is_simple_chat(self, task: str) -> bool:
        if any(keyword in task.lower() for keyword in self._GREETING_KEYWORDS):
            return True
        if any(keyword in task for keyword in self._RESEARCH_KEYWORDS):
            return False
        if any(keyword in task for keyword in self._LATEST_KEYWORDS):
            return False
        if self._extract_document_name(task):
            return False
        return any(keyword in task for keyword in ("解释", "是什么", "怎么", "为什么", "介绍", "区别", "优缺点"))

    def _is_complex_task(self, task: str) -> bool:
        return any(keyword in task for keyword in self._COMPLEX_CONNECTORS)

    def _extract_document_name(self, task: str) -> Optional[str]:
        quoted_match = re.search(r"[“\"]([^”\"]+\.(?:pdf|docx|doc|md|txt))[”\"]", task, re.IGNORECASE)
        if quoted_match:
            return quoted_match.group(1).strip()

        bare_match = re.search(r"([A-Za-z0-9_\-\u4e00-\u9fff][A-Za-z0-9_\-\u4e00-\u9fff\s]{0,80}\.(?:pdf|docx|doc|md|txt))", task, re.IGNORECASE)
        if bare_match and any(verb in task for verb in self._DOC_READ_VERBS):
            return bare_match.group(1).strip()
        return None
