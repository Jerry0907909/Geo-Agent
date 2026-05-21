"""API 请求/响应数据模式定义

使用 Pydantic 定义数据模型，确保类型安全和自动验证。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
    """Agent 查询请求"""

    query: str = Field(..., description="查询问题", min_length=1, max_length=2000)
    max_iterations: int = Field(10, description="最大迭代次数", ge=1, le=20)
    temperature: float = Field(0.7, description="LLM 温度参数", ge=0.0, le=2.0)
    return_intermediate_steps: bool = Field(True, description="是否返回中间推理步骤")


class ReasoningStep(BaseModel):
    """推理步骤"""

    step: int = Field(..., description="步骤序号")
    action: str = Field(..., description="执行的动作/工具")
    action_input: str = Field(..., description="动作输入")
    observation: str = Field(..., description="观察结果")


class AgentQueryResponse(BaseModel):
    """Agent 查询响应"""

    query: str = Field(..., description="原始查询")
    answer: str = Field(..., description="最终答案")
    reasoning_steps: List[ReasoningStep] = Field(
        default_factory=list, description="推理步骤"
    )
    sources: List[DocumentSource] = Field(default_factory=list, description="参考文献来源")
    execution_time: Optional[float] = Field(None, description="总执行耗时（秒）")


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
