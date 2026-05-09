# Agent 前端接入规范

## 文档目标

本文档定义 Geo-Agent 单 Agent v1 在前端的最小接入方式，并记录当前已落地的实现口径，保证后续迭代时：

- 不重做页面结构决策
- 不重复设计事件消费协议
- 能直接把后端 Agent 流展示出来

相关文档：

- 总接口文档：`docs/api/agent-frontend-backend.md`
- 后端实现规范：`docs/agent/backend-runtime-spec.md`
- 开发总清单：`TODO.md`

---

## 1. 接入目标

前端首期目标不是做复杂工作台，而是让聊天页中的 `agent` 模式真实可用。

前端必须支持：

- 发起 Agent 请求
- 流式接收 Agent 事件
- 展示执行状态
- 展示步骤列表
- 展示最终答案与来源

前端首期不做：

- 多 Agent 面板
- DAG 流程图
- 可编辑计划界面
- 高级调试器

---

## 2. 页面接入位置

首期只接入现有聊天页：

- 页面：`frontend/src/pages/ChatPage.tsx`
- 服务层：`frontend/src/services/api.ts`

要求：

- `agent` 成为正式模式
- 与 `chat`、`rag` 并列
- 保留现有消息流式体验

---

## 3. 前端状态模型

当前已采用以下状态：

```ts
type AgentRunStatus =
  | "queued"
  | "planning"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"

type AgentStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
```

当前已采用对象：

```ts
type AgentStep = {
  step_id: string
  title: string
  tool_name: string
  status: AgentStepStatus
  observation?: string
  latency_ms?: number
  sources?: Source[]
}

type AgentRunState = {
  run_id?: string
  status: AgentRunStatus
  plan_summary?: string
  steps: AgentStep[]
  final_answer?: string
  error?: {
    code: string
    message: string
  } | null
}
```

---

## 4. 服务层规范

### 4.1 `api.ts` 服务

当前已提供 `agentService`：

```ts
agentService.query(data)
agentService.stream(data, onEvent)
agentService.getRun(runId)
agentService.cancel(runId)
```

### 4.2 请求参数

前端提交的字段与后端保持一致：

```ts
type AgentQueryRequest = {
  task: string
  conversation_id?: number | null
  max_iterations?: number
  top_k?: number
  allow_web_search?: boolean
  return_steps?: boolean
}
```

### 4.3 与聊天页兼容

首期兼容方案：

- 聊天页仍可以通过 `mode=agent` 发起请求
- 服务层内部转调 `/api/agent/stream`
- 不要求页面层直接感知新接口路径

---

## 5. SSE 事件消费规范

前端必须识别以下事件：

- `info`
- `plan`
- `step_start`
- `tool_call`
- `tool_result`
- `replan`
- `final`
- `error`

### 5.1 `info`

更新 run 基本信息：

- `run_id`
- `status`

### 5.2 `plan`

更新：

- `plan_summary`
- 初始化 `steps`

### 5.3 `step_start`

更新某一步为 `running`。

### 5.4 `tool_call`

可选展示“正在调用某工具”，但首期可以只更新状态文案。

### 5.5 `tool_result`

更新：

- 对应 step 的 `status`
- `observation`
- `sources`
- `latency_ms`

### 5.6 `replan`

更新计划摘要或追加新的步骤列表。

### 5.7 `final`

更新：

- `status=completed`
- `final_answer`
- `sources`
- `execution_time`

### 5.8 `error`

更新：

- `status=failed`
- `error`

---

## 6. 页面展示要求

### 6.1 最小展示区块

`agent` 模式下必须显示：

- 当前状态条
- 当前步骤
- 已执行步骤列表
- 最终答案
- 来源列表

### 6.2 文案要求

建议使用用户可读文案：

- `planning` -> `正在规划任务`
- `running` -> `正在执行步骤`
- `completed` -> `执行完成`
- `failed` -> `执行失败`
- `cancelled` -> `已取消`

### 6.3 步骤展示要求

每个 step 至少展示：

- 步骤标题
- 工具名称
- 状态
- observation 摘要

首期不要求展示：

- 完整工具入参 JSON
- 详细 trace
- prompt 内容

---

## 7. 错误与恢复

### 7.1 错误展示

前端收到 `error` 事件后：

- 停止 loading
- 显示结构化错误文案
- 保留已完成步骤，便于用户定位

### 7.2 页面刷新恢复

若已拿到 `run_id`，页面刷新后允许调用：

- `GET /api/agent/runs/{run_id}`

恢复：

- 当前状态
- 已有步骤
- 最终答案或错误

---

## 8. 当前落地状态

当前已经完成：

1. `api.ts` 已补 Agent 类型和服务
2. `ChatPage` 已接收 `agent` 模式并消费 SSE 事件
3. 已补状态条、步骤列表、最终答案与来源栏
4. 已补 run 恢复和取消按钮

当前仍建议继续优化：

1. 收紧空状态和输入区的留白比例
2. 继续精修 Agent 面板与来源栏的信息密度
3. 校准深色模式对比度和大屏布局

---

## 9. 完成标准

以下条件当前已经满足，可视为前端最小接入完成：

- 用户能在聊天页选择 `agent`
- 页面能看到规划中、执行中、完成/失败状态
- 页面能看到步骤列表
- 页面能展示最终答案和 sources
- 页面不会把 Agent 过程退化成普通文本流
