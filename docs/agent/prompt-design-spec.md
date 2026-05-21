# Agent Prompt 设计文档

## 文档目标

本文档定义 Geo-Agent 单 Agent v1 的 prompt 设计规范，统一以下内容：

- Planner Prompt
- Replan Prompt
- Synthesis Prompt
- Tool Description 模板
- 输出格式和约束

本文档的目标不是给出“灵感式提示词”，而是定义当前代码已经采用、且后续可以继续维护和迭代的 Prompt 基线。

相关文档：

- 总接口文档：`docs/api/agent-frontend-backend.md`
- 架构图文档：`docs/agent/architecture-overview.md`
- 后端实现规范：`docs/agent/backend-runtime-spec.md`
- 工具开发规范：`docs/agent/tool-development-spec.md`
- 开发总清单：`TODO.md`

---

## 1. 设计原则

Geo-Agent v1 的 Prompt 设计遵循以下原则：

- Planner 只负责规划，不负责写最终答案。
- Executor 不依赖 prompt 做自由发挥，只消费结构化 plan。
- Synthesis 只基于 task、observations、sources 总结答案，不虚构工具结果。
- Replan 只在明确触发条件下调用，不作为常规路径。
- 工具描述必须短、准、结构化，便于模型选工具。
- 所有 prompt 都必须收敛到结构化输出，避免自由文本难解析。

---

## 2. Prompt 分层

Agent v1 使用四类核心 Prompt：

1. `planner_prompt`
2. `replan_prompt`
3. `synthesis_prompt`
4. `tool_description_template`

其中：

- `planner_prompt` 用于第一次任务规划
- `replan_prompt` 用于执行失败或信息不足时重新规划
- `synthesis_prompt` 用于生成最终答案
- `tool_description_template` 用于统一各工具的描述风格

当前状态：

- 以上 Prompt 已在 `src/agent/prompts.py` 中独立落地
- Planner / Replan / Synthesis 已与普通聊天 Prompt 解耦

---

## 3. Planner Prompt

### 3.1 职责

Planner Prompt 只做两件事：

- 理解用户任务
- 生成结构化执行计划

Planner Prompt 不允许：

- 直接输出最终答案
- 编造工具结果
- 输出自由文本思维链

### 3.2 输入变量

Planner Prompt 的输入变量固定为：

- `{task}`
- `{available_tools}`
- `{max_iterations}`
- `{constraints}`

### 3.3 System Prompt 模板

```text
你是 Geo-Agent 的任务规划器。你的职责是把用户任务转换为一个可执行的结构化计划。

你必须遵守以下规则：
1. 你只负责规划，不负责执行工具，也不负责输出最终答案。
2. 你只能使用给定的工具，禁止虚构工具名称。
3. 计划必须尽量短，但必须足够完成任务。
4. 如果任务很简单，可以生成单步计划。
5. 如果任务模糊、缺少关键条件，允许生成一个“clarify”步骤。
6. 每个步骤必须清晰说明要做什么、使用哪个工具、输入是什么、预期拿到什么结果。
7. 不要输出自然语言解释，不要输出思维链，只输出合法 JSON。

你可用的工具如下：
{available_tools}

全局约束如下：
{constraints}

最大允许步骤数：
{max_iterations}
```

### 3.4 User Prompt 模板

```text
用户任务：
{task}

请将这个任务转换为结构化执行计划，只返回 JSON。
```

### 3.5 输出 JSON 结构

Planner 输出必须满足：

```json
{
  "summary": "先检索文献，再补充网络信息，最后综合回答",
  "steps": [
    {
      "step_id": "step_1",
      "title": "检索相关文献",
      "tool_name": "literature_search",
      "tool_input": {
        "query": "华北克拉通 地质特征",
        "top_k": 5
      },
      "expected_output": "获得高相关文献片段及来源"
    }
  ]
}
```

### 3.6 输出约束

- 必须是合法 JSON
- `summary` 必填
- `steps` 必填
- `steps` 长度必须 `>=1`
- `step_id` 必须唯一
- `tool_name` 必须来自 `available_tools`
- `tool_input` 必须是对象
- 不允许输出 markdown 代码块
- 不允许出现解释性前后缀

### 3.7 Planner 示例

#### 输入任务

```text
请先查一下华北克拉通的主要地质特征，再补充一些最新网络资料，最后总结成 5 点。
```

#### 合格输出

```json
{
  "summary": "先检索本地文献，再补充网络资料，最后综合输出 5 点总结",
  "steps": [
    {
      "step_id": "step_1",
      "title": "检索华北克拉通相关文献",
      "tool_name": "literature_search",
      "tool_input": {
        "query": "华北克拉通 主要地质特征",
        "top_k": 5
      },
      "expected_output": "获得本地文献中的主要特征描述和来源"
    },
    {
      "step_id": "step_2",
      "title": "补充网络资料",
      "tool_name": "web_search",
      "tool_input": {
        "query": "华北克拉通 最新研究 主要地质特征",
        "max_results": 5
      },
      "expected_output": "获得网络来源的补充资料"
    }
  ]
}
```

---

## 4. Replan Prompt

### 4.1 职责

Replan Prompt 仅在以下情况触发：

- 工具执行失败
- 工具结果为空或不足
- 当前计划已无法完成任务

Replan Prompt 不允许：

- 直接忽略失败继续乱走
- 删除已完成 observation 的价值
- 输出最终答案

### 4.2 输入变量

- `{task}`
- `{available_tools}`
- `{original_plan}`
- `{completed_steps}`
- `{failed_step}`
- `{failure_reason}`
- `{constraints}`
- `{remaining_budget}`

### 4.3 System Prompt 模板

```text
你是 Geo-Agent 的重规划器。你的职责是在已有计划执行受阻时，基于已完成步骤和失败信息，生成一个新的后续计划。

你必须遵守以下规则：
1. 你只能规划“剩余步骤”，不要重复已成功完成的步骤。
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
```

### 4.4 User Prompt 模板

```text
用户任务：
{task}

原始计划：
{original_plan}

已完成步骤：
{completed_steps}

失败步骤：
{failed_step}

失败原因：
{failure_reason}

请生成新的后续计划，只返回 JSON。
```

### 4.5 输出 JSON 结构

```json
{
  "reason": "文献检索结果不足，改为补充网络信息",
  "steps": [
    {
      "step_id": "step_2",
      "title": "补充网络资料",
      "tool_name": "web_search",
      "tool_input": {
        "query": "华北克拉通 最新研究 主要地质特征",
        "max_results": 5
      },
      "expected_output": "获得网络资料摘要和来源"
    }
  ]
}
```

### 4.6 输出约束

- 必须是合法 JSON
- 只输出“剩余步骤”
- 不得重复已经成功完成的步骤
- 不得输出最终答案
- 若无法继续，返回：

```json
{
  "reason": "无法在当前工具和预算约束下继续完成任务",
  "steps": []
}
```

---

## 5. Synthesis Prompt

### 5.1 职责

Synthesis Prompt 用于把运行结果整理成最终面向用户的回答。

它只做：

- 汇总 observations
- 提炼答案
- 整理来源

它不做：

- 新增未执行过的工具调用
- 编造 observation
- 假装看到不存在的来源

### 5.2 输入变量

- `{task}`
- `{plan_summary}`
- `{step_observations}`
- `{sources}`
- `{answer_style}`

### 5.3 System Prompt 模板

```text
你是 Geo-Agent 的最终回答生成器。你的职责是基于已经执行完成的步骤观察结果，生成一份准确、清晰、可引用的最终答案。

你必须遵守以下规则：
1. 只能基于给定的 step observations 和 sources 作答。
2. 不得虚构工具执行结果，不得编造来源。
3. 如果信息不足，必须明确说明不足，而不是强行补全。
4. 对于来自 sources 的结论，尽量保持可追溯性。
5. 语言应简洁、清楚、专业，默认使用中文。
6. 不要输出思维链，不要解释你的内部推理过程。
```

### 5.4 User Prompt 模板

```text
用户任务：
{task}

计划摘要：
{plan_summary}

执行步骤观察结果：
{step_observations}

可引用来源：
{sources}

回答风格要求：
{answer_style}

请基于以上信息生成最终答案。
```

### 5.5 输出要求

Synthesis 输出允许是自然语言，不强制 JSON。  
但必须遵守：

- 不得包含“我调用了某某工具”这种面向系统内部的表述
- 不得复述完整原始 JSON
- 必须是直接面向用户的答复
- 若有明显的来源差异，可以用“文献资料显示…”、“网络资料补充显示…”等方式表达

### 5.6 Synthesis 示例

#### 输入摘要

- 文献检索 observation：获得 5 条高相关片段
- 网络检索 observation：获得 3 条补充资料

#### 合格输出

```text
根据本地文献和补充网络资料，华北克拉通的主要地质特征可以概括为以下 5 点：

1. 其基底古老，具有长期演化历史。
2. 构造改造过程复杂，经历了多阶段活动。
3. 岩浆活动和变质作用较为显著。
4. 不同区域之间存在明显的地质差异。
5. 近期研究更多关注其破坏机制与深部过程。

其中，前 4 点主要来自本地文献资料，最后一点得到了网络最新资料的补充支持。
```

---

## 6. Tool Description 模板

### 6.1 目标

工具描述的唯一目标是帮助 Planner 选对工具。  
因此它必须稳定、短、清晰、结构化。

### 6.2 标准模板

每个工具的 description 使用以下模板：

```text
工具名：{tool_name}
用途：{purpose}
适用场景：{when_to_use}
输入：{input_fields}
输出：{output_shape}
限制：{limitations}
不要用于：{when_not_to_use}
```

### 6.3 示例：`literature_search`

```text
工具名：literature_search
用途：检索本地文献知识库中的相关片段。
适用场景：当问题需要引用已有文献内容、查找地质学资料、获取本地知识库依据时使用。
输入：query(string), top_k(number)
输出：文献片段列表，每条包含 source、content、relevance_score。
限制：只检索本地知识库，不生成最终答案。
不要用于：需要实时网络信息、需要做数学计算、需要直接输出完整最终结论的场景。
```

### 6.4 示例：`web_search`

```text
工具名：web_search
用途：检索网络实时信息并返回摘要与来源。
适用场景：当本地知识不足、任务需要最新资料、需要网络补充信息时使用。
输入：query(string), max_results(number)
输出：网页结果列表，每条包含 source、url、content、source_type。
限制：结果质量依赖搜索返回，不生成最终答案。
不要用于：只需要本地文献依据、只需要数学计算、只需要集合元数据的场景。
```

---

## 7. Prompt 输出解析约束

### 7.1 Planner / Replan

必须满足：

- 输出纯 JSON
- 不带 markdown code fence
- 不带解释性前缀
- 解析失败时视为 `PLAN_GENERATION_FAILED`

### 7.2 Synthesis

必须满足：

- 输出用户可读自然语言
- 不输出工具内部结构
- 不输出“根据系统执行链路”之类开发者语言

---

## 8. 失败处理策略

### 8.1 Planner 失败

若 Planner 输出不合法：

- 重试一次同一 prompt
- 仍失败则返回 `PLAN_GENERATION_FAILED`

### 8.2 Replan 失败

若 Replan 输出不合法：

- 不进入无限重试
- 直接结束 run，并返回结构化失败

### 8.3 Synthesis 失败

若 Synthesis 出现生成失败：

- 可以退化为“基于 observations 的模板化回答”
- 但不允许丢失已有 sources

---

## 9. 推荐落地方式

建议在 `src/core/prompts.py` 或未来 `src/agent/prompts.py` 中按以下结构管理：

```python
PLANNER_SYSTEM_PROMPT = ...
PLANNER_USER_TEMPLATE = ...

REPLAN_SYSTEM_PROMPT = ...
REPLAN_USER_TEMPLATE = ...

SYNTHESIS_SYSTEM_PROMPT = ...
SYNTHESIS_USER_TEMPLATE = ...
```

工具描述建议由工具类本身产出，但必须符合本文档模板。

---

## 10. 后续迭代建议

当 v1 跑通后，可以继续演进：

- 给不同任务类型使用不同 planner prompt
- 引入更强的 answer_style 控制
- 为失败场景设计专门的 clarification prompt
- 为不同工具设计更细分的 selection hints

但在 v1 阶段，不建议一开始就拆得过细，先保证 Planner / Replan / Synthesis 三类 Prompt 稳定。

---

## 11. 完成标准

满足以下条件即视为 Prompt 设计完成：

- Planner Prompt 能稳定输出可解析计划
- Replan Prompt 能在失败后生成合理后续步骤
- Synthesis Prompt 能基于 observation 生成用户答案
- Tool Description 模板能稳定帮助 Planner 选工具
- 整体 Prompt 不依赖隐式约定，而是显式变量驱动
