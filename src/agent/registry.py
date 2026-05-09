"""Agent 工具注册中心。"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.agent.schemas import AgentError, AgentToolResult
from src.agent.tools import AgentTool, create_default_runtime_tools
from src.utils.config import get_config

class AgentToolSpec(BaseModel):
    """供 Planner 使用的工具描述。"""

    name: str = Field(..., description="工具唯一名称")
    description: str = Field(..., description="面向 Planner 的结构化说明")
    input_schema: Dict[str, object] = Field(default_factory=dict, description="输入结构")
    output_schema: Dict[str, object] = Field(default_factory=dict, description="输出结构")
    timeout_s: int = Field(10, ge=1, description="默认超时时间")
    read_only: bool = Field(default=True, description="是否只读")


class ToolRegistry:
    """工具注册中心。"""

    def __init__(self, tools: Optional[List[AgentToolSpec]] = None) -> None:
        self._tools: Dict[str, AgentToolSpec] = {}
        self._runtime_tools: Dict[str, AgentTool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: AgentToolSpec) -> None:
        """注册工具。"""
        self._tools[tool.name] = tool

    def register_runtime_tool(self, tool: AgentTool) -> None:
        """注册可执行工具。"""
        self._runtime_tools[tool.name] = tool

    def get(self, name: str) -> Optional[AgentToolSpec]:
        """获取单个工具。"""
        return self._tools.get(name)

    def require(self, name: str) -> AgentToolSpec:
        """获取工具，不存在时抛错。"""
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"未知工具: {name}")
        return tool

    def list_tools(self) -> List[AgentToolSpec]:
        """列出所有工具。"""
        return list(self._tools.values())

    def execute(self, name: str, tool_input: Dict[str, object]) -> AgentToolResult:
        """执行已注册工具。"""
        spec = self.require(name)
        runtime_tool = self._runtime_tools.get(name)
        if runtime_tool is None:
            return AgentToolResult(
                ok=False,
                error=AgentError(code="TOOL_NOT_IMPLEMENTED", message=f"工具 {name} 尚未实现执行层"),
                observation=f"工具 {name} 尚未实现执行层",
            )

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(runtime_tool.execute, dict(tool_input))
        try:
            return future.result(timeout=spec.timeout_s)
        except FutureTimeoutError:
            future.cancel()
            return AgentToolResult(
                ok=False,
                error=AgentError(code="TOOL_TIMEOUT", message=f"工具 {name} 执行超时"),
                observation=f"工具 {name} 执行超时",
            )
        except Exception as exc:
            logging.getLogger(__name__).exception("工具执行失败: %s", name)
            return AgentToolResult(
                ok=False,
                error=AgentError(code="TOOL_EXECUTION_FAILED", message=str(exc)),
                observation=str(exc),
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def format_for_planner(self) -> str:
        """格式化为 Planner 可消费的工具清单。"""
        lines: List[str] = []
        for tool in self.list_tools():
            lines.append(tool.description.strip())
        return "\n\n".join(lines)


def create_default_tool_registry() -> ToolRegistry:
    """创建默认只读工具注册中心。"""
    config = get_config()
    llm_timeout = int(config.get_llm_config().get("request_timeout", 60))
    agent_timeout = int(config.get_agent_config().get("timeout", 300))
    literature_timeout = min(max(llm_timeout, 45), agent_timeout)
    knowledge_timeout = min(max(llm_timeout + 30, 90), agent_timeout)
    web_timeout = min(max(llm_timeout, 45), agent_timeout)
    metadata_timeout = min(max(15, llm_timeout // 2), agent_timeout)
    direct_answer_timeout = min(max(llm_timeout, 30), agent_timeout)
    document_read_timeout = min(max(30, llm_timeout), agent_timeout)

    tools = [
        AgentToolSpec(
            name="clarify",
            description=(
                "工具名：clarify\n"
                "用途：当用户任务缺少关键对象、范围或输出要求时，生成一个澄清问题。\n"
                "适用场景：任务模糊、上下文不足、无法安全执行时使用。\n"
                "输入：task(string)\n"
                "输出：一个简洁明确的追问问题。\n"
                "限制：只用于澄清，不执行检索、不生成最终专业结论。\n"
                "不要用于：任务已经明确、只差执行的场景。"
            ),
            input_schema={"task": "string"},
            output_schema={"question": "string"},
            timeout_s=5,
        ),
        AgentToolSpec(
            name="direct_answer",
            description=(
                "工具名：direct_answer\n"
                "用途：直接基于通用模型能力回答用户问题，不强制依赖知识库或网页检索。\n"
                "适用场景：普通问答、解释、定义、对比、建议类任务，且不要求强证据链时使用。\n"
                "输入：question(string)\n"
                "输出：直接答案文本。\n"
                "限制：若问题明显需要证据、文档正文或实时信息，则不应优先使用。\n"
                "不要用于：时效性问题、必须引用知识库依据的问题、指定文档阅读任务。"
            ),
            input_schema={"question": "string"},
            output_schema={"answer": "string"},
            timeout_s=direct_answer_timeout,
        ),
        AgentToolSpec(
            name="document_catalog",
            description=(
                "工具名：document_catalog\n"
                "用途：查看知识库的目录结构，包括文档列表、集合列表、文件类型统计。\n"
                "适用场景：用户询问知识库里有什么、有哪些集合、有哪些文件类型时使用。\n"
                "输入：action(string, 可选值 list_documents/list_collections/file_types), collection_name(string,可选)\n"
                "输出：结构化目录、集合或统计信息。\n"
                "限制：只看目录和统计，不读取正文，不生成最终专业结论。\n"
                "不要用于：需要文档正文内容、需要实时网络资料、需要数值计算的场景。"
            ),
            input_schema={"action": "string", "collection_name": "string?"},
            output_schema={"documents|collections|file_types": "list"},
            timeout_s=metadata_timeout,
        ),
        AgentToolSpec(
            name="document_read",
            description=(
                "工具名：document_read\n"
                "用途：读取指定文档的正文、元数据与关键摘录。\n"
                "适用场景：用户明确提到某个文档名，或需要直接查看某篇本地文档内容时使用。\n"
                "输入：source(string), collection_name(string,可选), max_chars(number,可选)\n"
                "输出：文档摘录、元数据与来源片段。\n"
                "限制：必须知道目标文档名；不做全文检索发现。\n"
                "不要用于：只想知道知识库目录、需要实时网页资料、没有明确文档对象的场景。"
            ),
            input_schema={"source": "string", "collection_name": "string?", "max_chars": "number?"},
            output_schema={"content": "string", "metadata": "object", "chunk_count": "number"},
            timeout_s=document_read_timeout,
        ),
        AgentToolSpec(
            name="literature_search",
            description=(
                "工具名：literature_search\n"
                "用途：检索本地文献知识库中的相关片段。\n"
                "适用场景：当问题需要引用已有文献内容、查找地质学资料、获取本地知识库依据时使用。\n"
                "输入：query(string), top_k(number)\n"
                "输出：文献片段列表，每条包含 source、content、relevance_score。\n"
                "限制：只检索本地知识库，不生成最终答案。\n"
                "不要用于：需要实时网络信息、需要做数学计算、需要直接输出完整最终结论的场景。"
            ),
            input_schema={"query": "string", "top_k": "number"},
            output_schema={"documents": "list"},
            timeout_s=literature_timeout,
        ),
        AgentToolSpec(
            name="knowledge_query",
            description=(
                "工具名：knowledge_query\n"
                "用途：基于已有知识库上下文生成归纳型回答。\n"
                "适用场景：当已经有足够上下文，需要对知识库内容做概括、对比或总结时使用。\n"
                "输入：query(string), top_k(number)\n"
                "输出：基于知识库的答案摘要和引用来源。\n"
                "限制：依赖本地知识库，不获取网络实时信息。\n"
                "不要用于：普通闲聊、只需要原始片段检索、需要数学计算、需要集合元数据的场景。"
            ),
            input_schema={"query": "string", "top_k": "number"},
            output_schema={"answer": "string", "sources": "list"},
            timeout_s=knowledge_timeout,
        ),
        AgentToolSpec(
            name="web_search",
            description=(
                "工具名：web_search\n"
                "用途：检索网络实时信息并返回摘要与来源。\n"
                "适用场景：当本地知识不足、任务需要最新资料、需要网络补充信息时使用。\n"
                "输入：query(string), max_results(number)\n"
                "输出：网页结果列表，每条包含 source、url、content、source_type。\n"
                "限制：结果质量依赖搜索返回，不生成最终答案。\n"
                "不要用于：只需要本地文献依据、只需要数学计算、只需要集合元数据的场景。"
            ),
            input_schema={"query": "string", "max_results": "number"},
            output_schema={"results": "list"},
            timeout_s=web_timeout,
        ),
        AgentToolSpec(
            name="document_metadata",
            description=(
                "工具名：document_metadata\n"
                "用途：查询文档数量、集合信息、文件类型统计等元数据。\n"
                "适用场景：当任务需要知识库规模、集合信息、文档统计时使用。\n"
                "输入：action(string)\n"
                "输出：元数据统计结果。\n"
                "限制：只返回元数据，不返回文献正文，不生成最终答案。\n"
                "不要用于：检索文献内容、搜索网络资料、进行数学推导的场景。"
            ),
            input_schema={"action": "string"},
            output_schema={"metadata": "object"},
            timeout_s=metadata_timeout,
        ),
        AgentToolSpec(
            name="calculator",
            description=(
                "工具名：calculator\n"
                "用途：执行安全的数学表达式计算。\n"
                "适用场景：当任务需要数值换算、基础计算、简单公式求值时使用。\n"
                "输入：expression(string)\n"
                "输出：计算结果。\n"
                "限制：仅适用于安全的数学表达式，不执行任意代码。\n"
                "不要用于：检索知识库、获取网络资料、生成长文本结论的场景。"
            ),
            input_schema={"expression": "string"},
            output_schema={"result": "number|string"},
            timeout_s=2,
        ),
    ]
    registry = ToolRegistry(tools)
    for runtime_tool in create_default_runtime_tools().values():
        registry.register_runtime_tool(runtime_tool)
    return registry
