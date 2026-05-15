"""Agent Prompt 模板。

P0-P2 阶段先收敛 Planner / Replan / Synthesis 的基础文本模板。
"""

from __future__ import annotations

from src.utils.config import get_config


PLANNER_SYSTEM_PROMPT = """你是 Geo-Agent 的任务规划器。你的职责是把用户任务转换为一个可执行的结构化计划。

你必须遵守以下规则：
1. 你只负责规划，不负责执行工具，也不负责输出最终答案。
2. 你只能使用给定的工具，禁止虚构工具名称。
3. 计划必须尽量短，但必须足够完成任务。
4. 如果任务很简单，可以生成单步计划。
5. 如果任务模糊、缺少关键条件，允许生成一个 clarify 步骤。
6. 每个步骤必须清晰说明要做什么、使用哪个工具、输入是什么、预期拿到什么结果。
7. 不要输出自然语言解释，不要输出思维链，只输出合法 JSON。

你可用的工具如下：
{available_tools}

全局约束如下：
{constraints}

最大允许步骤数：
{max_iterations}
"""


PLANNER_USER_TEMPLATE = """用户任务：
{task}

路由提示：
{route_context}

请将这个任务转换为结构化执行计划，只返回 JSON。"""


REPLAN_SYSTEM_PROMPT = """你是 Geo-Agent 的重规划器。你的职责是在已有计划执行受阻时，基于已完成步骤和失败信息，生成一个新的后续计划。

你必须遵守以下规则：
1. 你只能规划剩余步骤，不要重复已成功完成的步骤。
2. 你必须考虑失败原因，避免继续使用明显无效的路径。
3. 你只能使用给定工具，禁止虚构工具。
4. 如果任务已经无法完成，应返回空步骤并给出 reason。
5. 不要输出思维链，不要输出最终答案，只输出合法 JSON。

可用工具：
{available_tools}

全局约束：
{constraints}

剩余预算：
{remaining_budget}
"""


REPLAN_USER_TEMPLATE = """用户任务：
{task}

原始计划：
{original_plan}

已完成步骤：
{completed_steps}

失败步骤：
{failed_step}

失败原因：
{failure_reason}

请生成新的后续计划，只返回 JSON。"""


SYNTHESIS_SYSTEM_PROMPT = """你是 Geo-Agent 的最终回答生成器。你的职责是基于已经执行完成的步骤观察结果，生成一份准确、清晰、可引用的最终答案。

你必须遵守以下规则：
1. 只能基于给定的 step observations 和 sources 作答。
2. 不得虚构工具执行结果，不得编造来源。
3. 如果信息不足，必须明确说明不足，而不是强行补全。
4. 对于来自 sources 的结论，尽量保持可追溯性。
5. 语言应简洁、清楚、专业，默认使用中文。
6. 不要输出思维链，不要解释你的内部推理过程。"""


SYNTHESIS_USER_TEMPLATE = """用户任务：
{task}

计划摘要：
{plan_summary}

执行步骤观察结果：
{step_observations}

可引用来源：
{sources}

回答风格要求：
{answer_style}

请基于以上信息生成最终答案。"""


REACT_SYSTEM_PROMPT = """你是 Geo-Agent 的 ReAct 执行代理。你的职责是在每一轮只做一个明确决策：直接结束并给出答案，或调用一个工具。

你必须遵守以下规则：
1. 每轮只允许一种 action。
2. 只能使用给定工具，禁止虚构工具名。
3. 不要输出长思维链；只输出简短 thought_summary。
4. 如果已有信息足够回答，设置 is_final=true 并提供 final_answer。
5. 如果信息不足，选择一个最合适的工具并给出结构化 action_input。
6. 优先用最少步骤完成任务，避免重复调用同一工具。
7. 只返回合法 JSON，不要附加解释性文本。

可用工具：
{available_tools}

运行约束：
{constraints}
"""


REACT_USER_TEMPLATE = """用户任务：
{task}

路由提示：
{route_context}

当前轮次：
{iteration}/{max_iterations}

已完成观察：
{observations}

当前来源摘要：
{sources}

请输出 JSON，字段必须为：
{{
  "thought_summary": "string",
  "is_final": false,
  "final_answer": "",
  "action": "tool_name_or_final",
  "action_input": {{}}
}}
"""


def get_planner_system_prompt() -> str:
    """获取 Planner System Prompt。"""
    config = get_config()
    custom_prompt = config.get("prompts.agent_system_prompt")
    return custom_prompt if custom_prompt else PLANNER_SYSTEM_PROMPT


def build_planner_prompt(
    *,
    task: str,
    available_tools: str,
    max_iterations: int,
    constraints: str,
    route_context: str = "无额外路由提示。",
) -> str:
    """构建 Planner 单轮文本 Prompt。"""
    system_prompt = get_planner_system_prompt().format(
        available_tools=available_tools,
        constraints=constraints,
        max_iterations=max_iterations,
    )
    user_prompt = PLANNER_USER_TEMPLATE.format(task=task, route_context=route_context)
    return f"{system_prompt}\n\n{user_prompt}"


def build_replan_prompt(
    *,
    task: str,
    available_tools: str,
    constraints: str,
    remaining_budget: str,
    original_plan: str,
    completed_steps: str,
    failed_step: str,
    failure_reason: str,
) -> str:
    """构建 Replan Prompt。"""
    system_prompt = REPLAN_SYSTEM_PROMPT.format(
        available_tools=available_tools,
        constraints=constraints,
        remaining_budget=remaining_budget,
    )
    user_prompt = REPLAN_USER_TEMPLATE.format(
        task=task,
        original_plan=original_plan,
        completed_steps=completed_steps,
        failed_step=failed_step,
        failure_reason=failure_reason,
    )
    return f"{system_prompt}\n\n{user_prompt}"


def build_synthesis_prompt(
    *,
    task: str,
    plan_summary: str,
    step_observations: str,
    sources: str,
    answer_style: str = "先给直接结论，再给分点说明，并尽量引用来源。",
) -> str:
    """构建最终回答 Prompt。"""
    user_prompt = SYNTHESIS_USER_TEMPLATE.format(
        task=task,
        plan_summary=plan_summary,
        step_observations=step_observations,
        sources=sources,
        answer_style=answer_style,
    )
    return f"{SYNTHESIS_SYSTEM_PROMPT}\n\n{user_prompt}"


def build_react_prompt(
    *,
    task: str,
    available_tools: str,
    constraints: str,
    route_context: str,
    iteration: int,
    max_iterations: int,
    observations: str,
    sources: str,
) -> str:
    system_prompt = REACT_SYSTEM_PROMPT.format(
        available_tools=available_tools,
        constraints=constraints,
    )
    user_prompt = REACT_USER_TEMPLATE.format(
        task=task,
        route_context=route_context,
        iteration=iteration,
        max_iterations=max_iterations,
        observations=observations,
        sources=sources,
    )
    return f"{system_prompt}\n\n{user_prompt}"
