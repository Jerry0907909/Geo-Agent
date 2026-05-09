"""API 请求/响应数据模式定义。"""

from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


# ==================== RAG 相关模式 ====================


class RAGQueryRequest(BaseModel):
    """RAG 查询请求"""

    query: str = Field(..., description="查询问题", min_length=1, max_length=1000)
    top_k: int = Field(5, description="返回的文档数量", ge=1, le=20)
    temperature: float = Field(0.7, description="LLM 温度参数", ge=0.0, le=2.0)


class DocumentSource(BaseModel):
    """文献来源信息"""

    content: str = Field(..., description="文档内容片段")
    source: str = Field(..., description="来源文件或标题")
    relevance_score: Optional[float] = Field(None, description="相关性分数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="其他元数据")


class RAGQueryResponse(BaseModel):
    """RAG 查询响应"""

    query: str = Field(..., description="原始查询")
    answer: str = Field(..., description="生成的答案")
    sources: List[DocumentSource] = Field(default_factory=list, description="参考文献来源")
    retrieval_time: Optional[float] = Field(None, description="检索耗时（秒）")
    generation_time: Optional[float] = Field(None, description="生成耗时（秒）")


# ==================== Agent 相关模式 ====================


class AgentQueryRequest(BaseModel):
    """Agent 查询请求。

    兼容旧字段 `query`，但以 `task` 为主。
    """

    task: str = Field(
        ...,
        validation_alias=AliasChoices("task", "query"),
        description="用户任务描述",
        min_length=1,
        max_length=2000,
    )
    conversation_id: Optional[int] = Field(None, description="关联会话ID")
    max_iterations: int = Field(8, description="最大执行步数", ge=1, le=20)
    top_k: int = Field(5, description="文献检索返回数量", ge=1, le=20)
    allow_web_search: bool = Field(True, description="是否允许调用网络检索工具")
    return_steps: bool = Field(True, description="是否返回详细步骤")


class AgentStepResponse(BaseModel):
    """Agent 结构化步骤响应。"""

    step_id: str = Field(..., description="步骤ID")
    title: str = Field(..., description="步骤标题")
    goal: str = Field(..., description="步骤目标")
    tool_name: str = Field(..., description="工具名称")
    status: str = Field(..., description="步骤状态")
    tool_input: Dict[str, Any] = Field(default_factory=dict, description="工具输入")
    expected_output: str = Field(..., description="预期输出")
    observation: Optional[str] = Field(None, description="观察结果")
    sources: List[DocumentSource] = Field(default_factory=list, description="来源列表")
    latency_ms: Optional[int] = Field(None, description="步骤耗时")

    model_config = ConfigDict(populate_by_name=True)


class AgentQueryResponse(BaseModel):
    """Agent 查询响应。"""

    run_id: str = Field(..., description="运行ID")
    conversation_id: Optional[int] = Field(None, description="关联会话ID")
    status: str = Field(..., description="运行状态")
    plan_summary: Optional[str] = Field(None, description="计划摘要")
    final_answer: Optional[str] = Field(None, description="最终答案")
    steps: List[AgentStepResponse] = Field(default_factory=list, description="结构化步骤")
    sources: List[DocumentSource] = Field(default_factory=list, description="参考来源")
    execution_time: Optional[float] = Field(None, description="总执行耗时（秒）")
    error: Optional[Dict[str, str]] = Field(None, description="结构化错误")


# ==================== 文献管理相关模式 ====================


class DocumentUploadRequest(BaseModel):
    """文档上传请求"""

    content: str = Field(..., description="文档内容", min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="文档元数据")
    filename: Optional[str] = Field(None, description="文件名")


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    document_id: Optional[str] = Field(None, description="文档ID")
    num_chunks: Optional[int] = Field(None, description="分割后的片段数")


class DocumentListResponse(BaseModel):
    """文档列表响应"""

    total: int = Field(..., description="文档总数")
    documents: List[Dict[str, Any]] = Field(default_factory=list, description="文档列表")


class DocumentUpdateRequest(BaseModel):
    """文档更新请求"""

    content: str = Field(..., description="新的文档内容", min_length=1)
    collection: Optional[str] = Field(None, description="指定集合名称")


class IndexRebuildRequest(BaseModel):
    """索引重建请求"""

    rebuild: bool = Field(True, description="是否完全重建（否则增量更新）")


class IndexRebuildResponse(BaseModel):
    """索引重建响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    num_documents: Optional[int] = Field(None, description="处理的文档数")
    num_chunks: Optional[int] = Field(None, description="索引的片段数")


# ==================== 系统相关模式 ====================


class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本号")
    components: Dict[str, str] = Field(default_factory=dict, description="组件状态")


class ErrorResponse(BaseModel):
    """错误响应"""

    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细信息")
