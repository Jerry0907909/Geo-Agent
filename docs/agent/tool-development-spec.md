# Agent 工具开发规范

## 文档目标

本文档定义 Geo-Agent 单 Agent v1 的工具开发规范，确保所有工具：

- 可被统一注册
- 可被 Planner 理解
- 可被 Executor 稳定调用
- 返回结构一致

相关文档：

- 总接口文档：`docs/api/agent-frontend-backend.md`
- 后端实现规范：`docs/agent/backend-runtime-spec.md`
- 开发总清单：`TODO.md`

---

## 1. v1 工具边界

Agent v1 只允许只读工具。

允许的工具类型：

- 文献检索
- 知识库问答
- 网络搜索
- 元数据查询
- 计算类工具

不允许的工具类型：

- 写数据库
- 改配置
- 调用高风险外部系统
- 上传或删除业务数据

---

## 2. 工具统一接口

每个工具都必须实现统一抽象：

```ts
type AgentTool = {
  name: string
  description: string
  input_schema: Record<string, unknown>
  output_schema: Record<string, unknown>
  timeout_s: number
  execute(input: Record<string, unknown>): Promise<ToolResult>
}
```

### 字段要求

- `name`
  - 全局唯一
  - 仅使用小写字母、数字、下划线
- `description`
  - 给 Planner 使用
  - 必须说明用途、适用场景和限制
- `input_schema`
  - 必须显式声明输入字段
- `output_schema`
  - 必须显式声明输出形态
- `timeout_s`
  - 必须有默认超时

---

## 3. 工具返回结构

所有工具统一返回：

```ts
type ToolResult = {
  ok: boolean
  data?: Record<string, unknown> | null
  error?: {
    code: string
    message: string
  } | null
  sources?: Source[]
  latency_ms: number
}
```

要求：

- 工具出错时返回 `ok=false`
- 不得抛裸异常给上层
- `latency_ms` 必须始终返回
- 有引用来源时必须放在 `sources`

---

## 4. 首期标准工具

### 4.1 `literature_search`

用途：

- 根据 query 检索本地文献片段

输入建议：

```json
{
  "query": "华北克拉通 地质特征",
  "top_k": 5
}
```

输出建议：

- 命中文献列表
- 每条文献的 source、content、relevance_score

### 4.2 `knowledge_query`

用途：

- 对已有知识库上下文进行归纳型回答

定位：

- 与 `literature_search` 不同，它输出的是“基于知识库的答案”

### 4.3 `web_search`

用途：

- 获取网络补充信息

要求：

- 返回标准化来源信息
- 明确 `source_type`
- 工具本身不负责最终答案撰写

### 4.4 `document_metadata`

用途：

- 查询文档数量、集合信息、文件类型统计等

### 4.5 `calculator`

用途：

- 执行安全的数学表达式计算

要求：

- 必须限制可执行表达式范围
- 禁止任意代码执行

---

## 5. 工具描述规范

Planner 主要依赖工具描述来选工具，因此每个工具的 `description` 必须包含：

- 这个工具做什么
- 什么时候应该使用
- 输入是什么
- 输出是什么
- 什么时候不应该使用

错误示例：

- “查询工具”
- “搜索内容”

正确风格：

- “检索本地文献知识库中的相关片段，适用于需要引用已有文献内容的问题。输入为 query 和 top_k，输出为文献片段列表及相关度，不直接生成最终答案。”

---

## 6. 参数校验规范

所有工具在执行前都必须校验输入：

- 必填字段是否存在
- 字段类型是否正确
- 数值范围是否合法
- 字符串是否为空

参数错误统一返回：

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_TOOL_INPUT",
    "message": "top_k 必须在 1 到 20 之间"
  },
  "latency_ms": 1
}
```

---

## 7. 超时与错误处理规范

### 7.1 超时

每个工具都必须声明默认超时：

- 检索类工具：建议 5-10 秒
- 网络搜索工具：建议 8-15 秒
- 计算工具：建议 1-2 秒

### 7.2 错误映射

工具内部异常必须被包装为结构化错误：

- `INVALID_TOOL_INPUT`
- `TOOL_TIMEOUT`
- `TOOL_EXECUTION_FAILED`
- `EMPTY_RESULT`

### 7.3 空结果

空结果不一定是错误。

建议：

- 无数据但执行成功：`ok=true`，`data` 为空，`sources=[]`
- 参数或运行失败：`ok=false`

---

## 8. Source 规范

工具若返回来源，必须使用统一结构：

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

要求：

- 文献工具使用 `type=document`
- 网络工具使用 `type=web`
- `source` 必须是用户可理解名称
- `content` 必须是可展示摘要，不要直接塞超长原文

---

## 9. 注册规范

所有工具必须通过统一 registry 注册，不允许 runtime 里硬编码创建。

要求：

- 启动时集中注册
- 按 `name` 查找
- 支持获取可用工具清单

Planner 只能使用 registry 中声明过的工具。

---

## 10. 开发顺序建议

1. 先定义工具抽象与 `ToolResult`
2. 再注册 `literature_search`
3. 再注册 `web_search`
4. 再注册 `document_metadata`
5. 最后注册 `calculator`

---

## 11. 完成标准

满足以下条件即视为工具体系可用：

- 所有工具有统一接口
- 所有工具可通过 registry 被发现
- 所有工具返回统一 `ToolResult`
- Planner 能依据 `description` 选择工具
- Executor 能稳定调用并拿到 observation
