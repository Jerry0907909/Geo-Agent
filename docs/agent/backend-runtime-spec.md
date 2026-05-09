# Agent 后端实现规范

## 文档目标

本文档定义 Geo-Agent 单 Agent v1 的后端实现边界、模块职责、运行状态和接口落地要求。  
目标不是讨论产品，而是让后端实现和后续维护时不再重新做架构决策。

当前状态：

- `src/agent/` 已落地
- `AgentRuntime / Planner / Executor / ToolRegistry` 已接通
- 本文档仍保留规范视角，但不再是纯设计草案

相关文档：

- 总接口文档：`docs/api/agent-frontend-backend.md`
- 工具开发规范：`docs/agent/tool-development-spec.md`
- 开发总清单：`TODO.md`

---

## 1. 实现目标

后端 Agent v1 必须满足：

- 输入一个用户任务后，先生成结构化计划
- 按步骤串行调用工具
- 在执行过程中持续产出标准事件
- 最终输出结构化结果
- 可以被聊天接口复用

v1 默认只做单 Agent、只读工具、单任务串行执行。

---

## 2. 模块结构

当前 `src/agent/` 模块按以下职责拆分：

### `schemas.py`

定义所有 Agent 输入输出对象：

- `AgentQueryRequest`
- `AgentQueryResponse`
- `AgentStep`
- `AgentRunStatus`
- `AgentError`

### `events.py`

定义所有 SSE 事件对象和序列化逻辑：

- `info`
- `plan`
- `step_start`
- `tool_call`
- `tool_result`
- `replan`
- `final`
- `error`

### `planner.py`

负责将用户任务转换为结构化计划：

- 调用 LLM 生成计划
- 解析计划结果
- 校验计划合法性
- 返回 `Plan`

### `registry.py`

负责工具注册和发现：

- 注册工具
- 按名称查找工具
- 暴露工具列表

### `executor.py`

负责按计划执行：

- 逐步执行 step
- 记录 observation
- 检测失败与循环
- 必要时触发 replanning

### `runtime.py`

负责总调度：

- 初始化 run state
- 调用 planner
- 调用 executor
- 汇总最终答案
- 输出同步结果和流式结果

---

## 3. 运行状态模型

### 3.1 Run Status

统一状态枚举：

- `queued`
- `planning`
- `running`
- `completed`
- `failed`
- `cancelled`

### 3.2 AgentSessionState

至少包含以下字段：

```ts
type AgentSessionState = {
  run_id: string
  conversation_id?: number | null
  status: "queued" | "planning" | "running" | "completed" | "failed" | "cancelled"
  task: string
  plan_summary?: string
  steps: AgentStep[]
  sources: Source[]
  final_answer?: string | null
  error?: {
    code: string
    message: string
  } | null
  started_at: string
  updated_at: string
}
```

v1 不要求长期记忆，但要求 run 内短期状态完整可追踪。

---

## 4. Planner 规范

### 4.1 输入

Planner 输入至少包含：

- 用户 task
- 允许使用的工具列表
- 最大步数
- 当前系统约束

### 4.2 输出

Planner 输出必须是结构化 JSON，可映射为：

```ts
type Plan = {
  summary: string
  steps: Array<{
    step_id: string
    title: string
    tool_name: string
    tool_input: Record<string, unknown>
    expected_output: string
  }>
}
```

### 4.3 校验规则

生成计划后必须执行后处理校验：

- `steps` 不能为空
- `step_id` 不可重复
- `tool_name` 必须存在于 registry
- `tool_input` 不可缺失
- 步数不可超过 `max_iterations`

如果计划不合法，直接返回 `PLAN_GENERATION_FAILED` 或 `INVALID_PLAN`。

### 4.4 规划边界

Planner 只负责“怎么做”，不负责直接拼最终答案。  
最终答案必须由独立的 synthesis 阶段完成。

---

## 5. Executor 规范

### 5.1 执行策略

v1 使用串行执行：

- 从 `step_1` 开始逐步执行
- 不做并发工具调用
- 不做多分支并行计划

### 5.2 每步产物

每一步执行后都必须写入：

- step status
- tool input
- observation
- sources
- latency_ms

### 5.3 失败处理

工具失败后，执行器允许三种结果：

- 重试当前 step
- 触发 replanning
- 终止整个 run

v1 默认策略：

- 可恢复错误：最多重试 1 次
- 不可恢复错误：直接失败
- 空结果但非异常：允许 replanning 1 次

### 5.4 循环检测

若出现以下情况则中止执行：

- 同一工具重复调用且输入相同
- observation 连续两次无有效变化
- 已达到最大迭代次数

错误码使用：

- `MAX_ITERATIONS_EXCEEDED`
- `LOOP_DETECTED`

---

## 6. Synthesis 规范

当执行器完成后，由单独阶段生成最终答案。

输入：

- 用户原始 task
- 执行步骤摘要
- 汇总 sources

输出：

- `final_answer`
- `sources`

要求：

- 区分工具观察与模型综合
- 不得伪造工具结果
- 引用来源尽量保留

---

## 7. API 落地要求

### 7.1 必须新增

- `POST /api/agent/query`
- `POST /api/agent/stream`
- `GET /api/agent/runs/{run_id}`
- `POST /api/agent/runs/{run_id}/cancel`

### 7.2 兼容接入

现有 `POST /api/chat/stream` 在 `mode=agent` 时：

- 不再自己处理 Agent 逻辑
- 只负责转发到 Agent Runtime

### 7.3 响应一致性

非流式响应和流式最终事件都必须复用同一数据模型：

- `run_id`
- `status`
- `steps`
- `sources`
- `final_answer`
- `error`
- `execution_time`

---

## 8. 日志与错误规范

### 8.1 日志字段

至少统一记录：

- `run_id`
- `conversation_id`
- `task_type`
- `planner_latency_ms`
- `tool_name`
- `tool_latency_ms`
- `step_id`
- `status`
- `error_code`

### 8.2 错误码

后端统一错误码：

- `INVALID_TASK`
- `PLAN_GENERATION_FAILED`
- `INVALID_PLAN`
- `UNKNOWN_TOOL`
- `TOOL_TIMEOUT`
- `TOOL_EXECUTION_FAILED`
- `MAX_ITERATIONS_EXCEEDED`
- `LOOP_DETECTED`
- `RUN_CANCELLED`
- `INTERNAL_ERROR`

---

## 9. 实施顺序

1. 先完成 `schemas / events / registry`
2. 再完成 `planner`
3. 再完成 `executor`
4. 再完成 `runtime`
5. 最后接入 API route

---

## 10. 完成标准

满足以下条件即视为后端主链路完成：

- `mode=agent` 不再是占位模式
- 能对一个复杂任务生成至少两步计划
- 能通过工具完成执行并产出 observation
- 能通过 SSE 回传完整执行过程
- 能在失败时返回结构化错误
