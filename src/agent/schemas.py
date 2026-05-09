"""Agent 领域对象定义。

用于统一 P0-P2 阶段的 Agent 术语与状态模型。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentRunStatus(str, Enum):
    """Agent 运行状态。"""

    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStepStatus(str, Enum):
    """步骤状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentError(BaseModel):
    """结构化错误信息。"""

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误信息")


class AgentConstraints(BaseModel):
    """Planner/Runtime 的统一约束。"""

    max_iterations: int = Field(8, ge=1, le=20, description="最大步数")
    max_failures: int = Field(2, ge=0, le=10, description="允许的失败次数")
    timeout_seconds: int = Field(300, ge=1, le=3600, description="总超时预算")
    top_k: int = Field(5, ge=1, le=20, description="默认检索返回数量")
    allow_web_search: bool = Field(True, description="是否允许网络检索")
    read_only_tools: bool = Field(True, description="当前阶段仅允许只读工具")


class AgentStep(BaseModel):
    """结构化计划步骤。"""

    step_id: str = Field(..., description="步骤唯一标识")
    title: str = Field(..., description="步骤标题")
    goal: str = Field(..., description="步骤目标")
    tool_name: str = Field(..., description="工具名称")
    tool_input: Dict[str, Any] = Field(default_factory=dict, description="工具输入")
    expected_output: str = Field(..., description="预期输出")
    status: AgentStepStatus = Field(default=AgentStepStatus.PENDING, description="步骤状态")
    observation: Optional[str] = Field(None, description="执行观察结果")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="步骤来源")
    latency_ms: Optional[int] = Field(None, description="步骤耗时")


class AgentPlan(BaseModel):
    """结构化计划。"""

    summary: str = Field(..., description="计划摘要")
    steps: List[AgentStep] = Field(default_factory=list, description="步骤列表")


class AgentSessionState(BaseModel):
    """运行期状态。"""

    model_config = ConfigDict(use_enum_values=True)

    run_id: str = Field(..., description="运行ID")
    conversation_id: Optional[int] = Field(None, description="关联会话ID")
    status: AgentRunStatus = Field(default=AgentRunStatus.QUEUED, description="运行状态")
    task: str = Field(..., description="原始任务")
    constraints: AgentConstraints = Field(default_factory=AgentConstraints, description="运行约束")
    plan_summary: Optional[str] = Field(None, description="计划摘要")
    steps: List[AgentStep] = Field(default_factory=list, description="结构化步骤")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="累计来源")
    final_answer: Optional[str] = Field(None, description="最终答案")
    error: Optional[AgentError] = Field(None, description="错误信息")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="启动时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")


class AgentPlanResult(BaseModel):
    """Planner 输出与 Runtime 回写之间的桥接对象。"""

    state: AgentSessionState = Field(..., description="运行状态")
    plan: AgentPlan = Field(..., description="结构化计划")


class AgentToolResult(BaseModel):
    """统一工具执行返回。"""

    ok: bool = Field(..., description="工具是否执行成功")
    data: Optional[Dict[str, Any]] = Field(None, description="结构化输出数据")
    error: Optional[AgentError] = Field(None, description="工具错误")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="来源列表")
    latency_ms: int = Field(0, ge=0, description="工具耗时")
    observation: Optional[str] = Field(None, description="供 Runtime/Synthesis 使用的观察结果")
