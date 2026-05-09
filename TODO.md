# Geo-Agent Agent 化开发 TODO

> 当前状态：`P0-P10` 的核心文档与主链路已完成，当前工作重心转为持续性的 UI/UX 与可靠性细节打磨。
>
> 本文档不再描述“准备做什么”，而是用于维护：已经落地了什么、还差什么、下一步该收口哪里。

## 当前判断

- 当前项目已经具备：
  - 聊天主链路
  - RAG 检索主链路
  - 文档上传与管理
  - 用户/会话体系
  - SSE 流式输出基础
  - 真正的 Agent Runtime
  - Planner / Executor / Tool Registry
  - 标准 Agent SSE 事件流
  - `mode=agent` 的真实前后端闭环
  - 面向聊天页的最小 Agent UI 闭环
- 当前主要剩余项：
  - 前端视觉与深色模式继续精修
  - 日志、超时、重试、并发限制的策略继续细化，而非从零实现
  - README、TODO、Notion 与代码状态在后续迭代中持续同步

## 开发原则

- 第一阶段只做单 Agent，不做多 Agent。
- 第一阶段只做只读工具，不做外部业务写操作。
- 第一阶段优先打通后端 Agent 主链路，再做最小前端接入。
- 暂不处理数据库体系重构和测评体系。
- 不把 Agent 逻辑继续堆在 `chat_routes.py` 中，必须独立出 `src/agent/` 模块。

## P0. 目标与边界冻结

- [x] 明确 Agent v1 的任务范围：
  - 文献检索
  - 网络补充检索
  - 简单计算
  - 多步信息整合
  - 最终答案综合生成
- [x] 明确 Agent v1 不支持：
  - 多 Agent 协作
  - 长期记忆
  - 外部业务写操作
  - 高风险自动执行
- [x] 统一领域对象：
  - task
  - plan
  - step
  - tool_call
  - observation
  - final_answer
  - run_status

## P1. 建立 Agent Runtime 主骨架

- [x] 新增 `src/agent/` 模块，拆分职责：
  - `runtime.py`
  - `planner.py`
  - `executor.py`
  - `registry.py`
  - `schemas.py`
  - `events.py`
- [x] 定义 `AgentRuntime` 统一入口：
  - 接收 task
  - 生成 plan
  - 顺序执行 step
  - 汇总最终答案
  - 支持流式事件输出
- [x] 定义 `AgentSessionState`：
  - run_id
  - conversation_id
  - current_plan
  - executed_steps
  - collected_sources
  - final_status
- [x] 增加统一约束：
  - 最大步数
  - 最大失败次数
  - 总超时预算

## P2. 实现 Planner

- [x] 为 Planner 单独设计 prompt，而不是混在聊天 prompt 中。
- [x] Planner 输出必须结构化，不能是自由文本。
- [x] 每个 step 至少包含：
  - `step_id`
  - `goal`
  - `tool_name`
  - `tool_input`
  - `expected_output`
- [x] 增加任务分类：
  - 直接回答
  - 文献检索
  - 网络检索
  - 多步综合
  - 需要澄清
- [x] 增加计划校验：
  - 空计划拦截
  - 非法工具拦截
  - 缺失输入拦截
  - 重复步骤拦截

## P3. 建立 Tool Runtime 与 Tool Registry

- [x] 定义统一 Tool 接口：
  - `name`
  - `description`
  - `input_schema`
  - `output_schema`
  - `timeout_s`
  - `execute()`
- [x] 建立 Tool Registry，统一注册和发现工具。
- [x] 将现有能力收敛为正式工具：
  - [x] `literature_search`
  - [x] `knowledge_query`
  - [x] `web_search`
  - [x] `calculator`
  - [x] `document_metadata`
- [x] 所有工具必须统一返回：
  - `ok`
  - `data`
  - `error`
  - `sources`
  - `latency_ms`
- [x] 增加工具级能力：
  - 参数校验
  - 超时
  - 异常包装
  - 日志记录

## P4. 实现 Executor

- [x] Executor 按计划逐步执行，不允许跳步。
- [x] 每一步都生成标准 observation。
- [x] 失败时支持有限度 replanning。
- [x] 增加循环检测，防止重复空转。
- [x] 增加 early stop 条件，避免无意义继续执行。
- [x] 将最终答案生成从工具执行中独立出来，作为单独 synthesis 阶段。

## P5. 接入现有 RAG / Chat 能力

- [x] 把现有 RAG 链改造成 Agent 可调用工具，而不是仅作为 `mode=rag` 分支存在。
- [x] 把现有 web search 改造成正式工具，而不是仅作为 chat 增强选项。
- [x] 保留 `chat` / `rag` 模式，但 `agent` 变成正式链路。
- [x] `mode=agent` 时，后端必须真正经过 Planner + Executor，而不是套壳聊天接口。

## P6. 补齐后端接口

- [x] 新增正式 Agent API：
  - [x] `POST /api/agent/query`
  - [x] `POST /api/agent/stream`
  - [x] `GET /api/agent/runs/{run_id}`
  - [x] `POST /api/agent/runs/{run_id}/cancel`
- [x] `POST /api/chat/stream` 中保留 `mode=agent` 路由兼容，但不内嵌 Agent 逻辑。
- [x] 统一返回结构：
  - `run_id`
  - `status`
  - `final_answer`
  - `steps`
  - `sources`
  - `error`
  - `execution_time`

## P7. 定义 Agent SSE 事件流

- [x] 统一事件类型：
  - `info`
  - `plan`
  - `step_start`
  - `tool_call`
  - `tool_result`
  - `replan`
  - `final`
  - `error`
- [x] 每个事件都带：
  - `run_id`
  - `type`
  - `timestamp`
  - `payload`
- [x] 保持与当前前端 SSE 消费方式兼容，避免重新设计整套流协议。

## P8. 最小前端接入

- [x] 在前端正式开放 `agent` 模式入口。
- [x] 聊天页支持显示：
  - 规划中
  - 执行中
  - 当前步骤
  - 工具调用摘要
  - 最终答案
- [x] 展示步骤列表和 source 列表。
- [x] 错误和澄清请求要有明确 UI，而不是直接显示异常字符串。
- [x] 前端先做最小可用，不做复杂工作台。

## P9. 可观测性与可靠性最小闭环

- [x] 为每次 Agent 运行生成 `run_id`。
- [x] 日志统一记录：
  - planning 耗时
  - tool 耗时
  - synthesis 耗时
  - total 耗时
  - 错误类型
- [x] 增加超时、重试、失败中止策略。
- [x] 增加单用户并发运行限制。

## P10. 文档同步

- [x] 更新 README，对 `chat / rag / agent` 三条链路重新定义。
- [x] 补充 Agent 架构文档。
- [x] 补充 Agent 前后端接口文档。
- [x] 补充工具开发规范文档。
- [x] 统一本地 Markdown 与 Notion 的阶段口径。

## 验收标准

- [x] 用户可在前端选择 `agent` 模式发起请求。
- [x] 后端能够先规划，再逐步调用工具，再生成最终答案。
- [x] 前端能流式看到规划、步骤、工具结果和最终答案。
- [x] 多步任务不再由单一 prompt 直接“脑补完成”。
- [x] 工具失败时系统能给出结构化失败信息，而不是直接崩溃。

## 参考文档

- Agent 前后端接口文档：`docs/api/agent-frontend-backend.md`
- Agent 架构图文档：`docs/agent/architecture-overview.md`
- Agent Prompt 设计文档：`docs/agent/prompt-design-spec.md`
- Agent 后端实现规范：`docs/agent/backend-runtime-spec.md`
- Agent 前端接入规范：`docs/agent/frontend-integration-spec.md`
- Agent 工具开发规范：`docs/agent/tool-development-spec.md`
