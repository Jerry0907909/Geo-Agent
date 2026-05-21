# Agent 前后端接口文档

## 文档目标

本文档定义 Geo-Agent 第一版单 Agent 系统的前后端接口约定，用于维护当前已经落地的统一协议：

- 后端 Agent Runtime
- 前端 `agent` 模式接入
- 流式执行过程展示

当前状态：

- `/api/agent/*` 已落地
- 前端 `agent` 模式已接入并消费 SSE 事件
- 本文档同时承担“接口定义 + 当前实现口径”双重作用

## 配套规范

- 后端实现规范：`docs/agent/backend-runtime-spec.md`
- 前端接入规范：`docs/agent/frontend-integration-spec.md`
- 工具开发规范：`docs/agent/tool-development-spec.md`
- Prompt 设计文档：`docs/agent/prompt-design-spec.md`

---

## 1. 设计目标

Agent v1 必须具备以下能力：

- 能根据用户任务自动生成执行计划
- 能按步骤调用工具
- 能输出每一步的 observation
- 能在 SSE 中持续向前端回传执行过程
- 能输出最终答案和引用来源

Agent v1 的定位是单 Agent、只读工具、面向知识检索和多步信息整合。

---

## 2. 后端接口

### 2.1 `POST /api/agent/query`

非流式执行 Agent 请求，适合调试或同步页面调用。

#### Request

```json
{
  "task": "请先检索华北克拉通的主要地质特征，再补充网络信息，总结成 5 点",
  "conversation_id": 123,
  "max_iterations": 8,
  "top_k": 5,
  "allow_web_search": true,
  "return_steps": true
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task` | `string` | 是 | 用户任务描述 |
| `conversation_id` | `number \| null` | 否 | 关联当前聊天会话 |
| `max_iterations` | `number` | 否 | 最大执行步数，默认 `8` |
| `top_k` | `number` | 否 | 文献检索返回数量，默认 `5` |
| `allow_web_search` | `boolean` | 否 | 是否允许调用网络检索工具 |
| `return_steps` | `boolean` | 否 | 是否返回详细步骤 |

#### Response

```json
{
  "run_id": "run_20260423_xxx",
  "conversation_id": 123,
  "status": "completed",
  "final_answer": "1. 华北克拉通...",
  "steps": [
    {
      "step_id": "step_1",
      "title": "检索华北克拉通相关文献",
      "tool_name": "literature_search",
      "status": "completed",
      "input": {
        "query": "华北克拉通 地质特征"
      },
      "observation": "检索到 5 篇相关文献",
      "sources": [
        {
          "type": "document",
          "source": "xxx.pdf",
          "content": "文献片段",
          "relevance_score": 0.91
        }
      ],
      "latency_ms": 432
    }
  ],
  "sources": [
    {
      "type": "document",
      "source": "xxx.pdf",
      "content": "文献片段",
      "relevance_score": 0.91
    },
    {
      "type": "web",
      "source": "中国地质调查局",
      "url": "https://example.com",
      "content": "网页摘要"
    }
  ],
  "execution_time": 3.21,
  "error": null
}
```

---

### 2.2 `POST /api/agent/stream`

流式执行 Agent 请求，供聊天页主链路使用。

#### Request

请求体与 `/api/agent/query` 保持一致：

```json
{
  "task": "对比华北克拉通和扬子克拉通，并给出差异总结",
  "conversation_id": 123,
  "max_iterations": 8,
  "top_k": 5,
  "allow_web_search": true,
  "return_steps": true
}
```

#### Response

- 类型：`text/event-stream`
- 编码：SSE

---

### 2.3 `GET /api/agent/runs/{run_id}`

用于前端断线恢复或刷新页面后重新获取 Agent 运行状态。

#### Response

```json
{
  "run_id": "run_20260423_xxx",
  "status": "running",
  "current_step_id": "step_2",
  "steps": [],
  "final_answer": null,
  "error": null
}
```

---

### 2.4 `POST /api/agent/runs/{run_id}/cancel`

取消当前运行中的 Agent 任务。

#### Response

```json
{
  "run_id": "run_20260423_xxx",
  "status": "cancelled",
  "message": "运行已取消"
}
```

---

## 3. SSE 事件协议

### 3.1 统一事件格式

每条 SSE 数据统一为：

```json
{
  "type": "step_start",
  "run_id": "run_20260423_xxx",
  "timestamp": "2026-04-23T12:00:00Z",
  "payload": {}
}
```

---

### 3.2 事件类型定义

#### `info`

运行启动信息。

```json
{
  "type": "info",
  "run_id": "run_20260423_xxx",
  "timestamp": "2026-04-23T12:00:00Z",
  "payload": {
    "conversation_id": 123,
    "status": "planning"
  }
}
```

#### `plan`

Agent 已产出计划。

```json
{
  "type": "plan",
  "run_id": "run_20260423_xxx",
  "timestamp": "2026-04-23T12:00:01Z",
  "payload": {
    "summary": "先检索文献，再做网络补充，最后综合回答",
    "steps": [
      {
        "step_id": "step_1",
        "title": "检索相关文献",
        "tool_name": "literature_search"
      },
      {
        "step_id": "step_2",
        "title": "补充网络资料",
        "tool_name": "web_search"
      }
    ]
  }
}
```

#### `step_start`

某一步正式开始执行。

```json
{
  "type": "step_start",
  "run_id": "run_20260423_xxx",
  "timestamp": "2026-04-23T12:00:02Z",
  "payload": {
    "step_id": "step_1",
    "title": "检索相关文献",
    "tool_name": "literature_search"
  }
}
```

#### `tool_call`

开始调用某个工具。

```json
{
  "type": "tool_call",
  "run_id": "run_20260423_xxx",
  "timestamp": "2026-04-23T12:00:02Z",
  "payload": {
    "step_id": "step_1",
    "tool_name": "literature_search",
    "input": {
      "query": "华北克拉通 地质特征",
      "top_k": 5
    }
  }
}
```

#### `tool_result`

工具执行完成。

```json
{
  "type": "tool_result",
  "run_id": "run_20260423_xxx",
  "timestamp": "2026-04-23T12:00:03Z",
  "payload": {
    "step_id": "step_1",
    "tool_name": "literature_search",
    "status": "completed",
    "observation": "检索到 5 条高相关文献片段",
    "sources": [
      {
        "type": "document",
        "source": "xxx.pdf",
        "content": "文献片段",
        "relevance_score": 0.91
      }
    ],
    "latency_ms": 432
  }
}
```

#### `replan`

执行中途重新规划。

```json
{
  "type": "replan",
  "run_id": "run_20260423_xxx",
  "timestamp": "2026-04-23T12:00:04Z",
  "payload": {
    "reason": "文献结果不足，补充网络检索",
    "steps": [
      {
        "step_id": "step_2",
        "title": "补充网络资料",
        "tool_name": "web_search"
      }
    ]
  }
}
```

#### `final`

最终完成结果。

```json
{
  "type": "final",
  "run_id": "run_20260423_xxx",
  "timestamp": "2026-04-23T12:00:06Z",
  "payload": {
    "status": "completed",
    "final_answer": "总结如下：...",
    "sources": [],
    "execution_time": 3.21
  }
}
```

#### `error`

运行失败。

```json
{
  "type": "error",
  "run_id": "run_20260423_xxx",
  "timestamp": "2026-04-23T12:00:06Z",
  "payload": {
    "status": "failed",
    "code": "TOOL_TIMEOUT",
    "message": "web_search 执行超时"
  }
}
```

---

## 4. 后端数据结构约定

### 4.1 AgentQueryRequest

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

### 4.2 AgentStep

```ts
type AgentStep = {
  step_id: string
  title: string
  tool_name: string
  status: "pending" | "running" | "completed" | "failed" | "skipped"
  input?: Record<string, unknown>
  observation?: string
  sources?: Source[]
  latency_ms?: number
}
```

### 4.3 Source

```ts
type Source = {
  type: "document" | "web"
  source: string
  content: string
  relevance_score?: number
  url?: string
  source_type?: string
  metadata?: Record<string, unknown>
}
```

### 4.4 AgentQueryResponse

```ts
type AgentQueryResponse = {
  run_id: string
  conversation_id?: number | null
  status: "queued" | "planning" | "running" | "completed" | "failed" | "cancelled"
  final_answer: string | null
  steps: AgentStep[]
  sources: Source[]
  execution_time?: number
  error?: {
    code: string
    message: string
  } | null
}
```

---

## 5. 前端接口约定

### 5.1 `frontend/src/services/api.ts`

当前已落地类型与服务：

```ts
export type AgentRunStatus =
  | "queued"
  | "planning"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"

export interface AgentStep {
  step_id: string
  title: string
  tool_name: string
  status: "pending" | "running" | "completed" | "failed" | "skipped"
  input?: Record<string, unknown>
  observation?: string
  sources?: Source[]
  latency_ms?: number
}

export interface AgentResponse {
  run_id: string
  conversation_id?: number | null
  status: AgentRunStatus
  final_answer: string | null
  steps: AgentStep[]
  sources: Source[]
  execution_time?: number
  error?: {
    code: string
    message: string
  } | null
}
```

当前已落地服务方法：

```ts
agentService.query(data)
agentService.stream(data, onEvent)
agentService.getRun(runId)
agentService.cancel(runId)
```

---

### 5.2 ChatPage 最小交互要求

前端 `agent` 模式最少需要展示：

- 当前运行状态
- 当前步骤
- 已完成步骤列表
- 当前工具调用摘要
- 最终答案
- sources

首期不要求：

- 流程图
- 拖拽工作台
- 多 Agent 面板
- 复杂调试控制台

---

## 6. 与现有接口的兼容关系

### 6.1 现有 `chat` / `rag`

- `chat`：保留，用于普通问答
- `rag`：保留，用于显式文献问答
- `agent`：升级为正式模式，走独立 Agent Runtime

### 6.2 现有 `/api/chat/stream`

当前兼容方案：

- 当前聊天页仍可通过 `mode=agent` 调用
- 服务层内部已优先转调 `/api/agent/stream`
- `/api/chat/stream` 中的 `mode=agent` 仍作为兼容入口保留

---

## 7. 错误处理约定

后端必须返回结构化错误，而不是仅返回字符串。

统一错误结构：

```json
{
  "error": {
    "code": "TOOL_TIMEOUT",
    "message": "web_search 执行超时"
  }
}
```

建议错误码：

- `INVALID_TASK`
- `PLAN_GENERATION_FAILED`
- `INVALID_PLAN`
- `UNKNOWN_TOOL`
- `TOOL_TIMEOUT`
- `TOOL_EXECUTION_FAILED`
- `MAX_ITERATIONS_EXCEEDED`
- `RUN_CANCELLED`
- `INTERNAL_ERROR`

---

## 8. 当前落地结论

当前已经完成：

1. 后端 `AgentRuntime + Planner + Executor + Tool Registry`
2. 正式 `/api/agent/query` 与 `/api/agent/stream`
3. `/api/chat/stream` 的 `mode=agent` 兼容接入
4. 前端 `agent` 模式展示、取消运行、run 恢复与来源展示

当前剩余工作：

1. 继续精修前端展示密度与交互噪音
2. 继续完善可靠性与日志策略
3. 统一 README、TODO、Notion 的状态口径

---

## 9. 对应开发清单

详细任务见项目根目录：

- `TODO.md`
