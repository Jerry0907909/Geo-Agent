"""WebSearch 增强的 RAG Retriever

整合网络搜索和本地文献检索，提供更全面的信息
"""

import logging
from typing import List, Iterator, Any, Optional
from src.rag.retriever import RAGRetriever
from src.tools.web_search import WebSearchTool, SearchResult

logger = logging.getLogger(__name__)


class WebEnhancedRAGRetriever(RAGRetriever):
    """WebSearch 增强的 RAG 检索器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.web_search_tool = WebSearchTool(max_results=3)
    
    async def astream_with_web(
        self, 
        question: str, 
        top_k: Optional[int] = None,
        min_relevance_score: float = 0.0,
        enable_web_search: bool = False,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> tuple[List[Any], List[SearchResult], Any]:
        """异步流式 RAG + WebSearch
        
        Args:
            question: 用户问题
            top_k: 检索文档数量
            min_relevance_score: 最小相关度阈值
            enable_web_search: 是否启用网络搜索
            system_prompt: 自定义系统提示词（用于自定义助手）
            temperature: 自定义温度参数
        
        Returns:
            (文档列表, 网络搜索结果列表, 答案异步流式迭代器)
        """
        # 1. 检索本地文档
        docs = self.retrieve(question, top_k=top_k, min_relevance_score=min_relevance_score)
        
        # 2. 网络搜索（如果启用）
        web_results = []
        web_context = ""
        if enable_web_search:
            try:
                web_results = self.web_search_tool.search(question, max_results=3)
                web_context = self.web_search_tool.format_for_llm(web_results)
                logger.info(f"WebSearch: 获取到 {len(web_results)} 条网络信息")
            except Exception as e:
                logger.error(f"WebSearch 失败: {e}")
        
        # 3. 整合上下文
        doc_context = self._format_docs(docs) if docs else ""
        
        if web_context and doc_context:
            combined_context = f"""## 本地文献资料：
{doc_context}

## 网络实时信息：
{web_context}"""
        elif web_context:
            combined_context = f"""## 网络实时信息：
{web_context}"""
        elif doc_context:
            combined_context = doc_context
        else:
            combined_context = "(未检索到相关信息)"
        
        # 4. 生成增强的提示词
        enhanced_prompt = self._create_enhanced_prompt(enable_web_search, system_prompt)
        
        # 5. 如果有自定义温度，创建新的 LLM
        llm = self.llm
        if temperature is not None:
            from src.core.llm_provider import create_llm_provider
            llm_provider = create_llm_provider(temperature=temperature)
            llm = llm_provider.get_langchain_llm()
        
        # 6. 创建异步流式生成器
        async def answer_generator():
            chain = enhanced_prompt | llm | self.output_parser
            async for chunk in chain.astream({
                "context": combined_context,
                "question": question,
            }):
                yield chunk
        
        return docs, web_results, answer_generator()
    
    def _create_enhanced_prompt(self, has_web_search: bool, custom_system_prompt: Optional[str] = None):
        """创建增强的提示词模板
        
        Args:
            has_web_search: 是否启用了网络搜索
            custom_system_prompt: 自定义系统提示词（用于自定义助手）
        """
        from langchain_core.prompts import ChatPromptTemplate
        
        # 如果有自定义提示词，使用自定义的
        if custom_system_prompt:
            system_prompt = f"""{custom_system_prompt}

请基于以下参考信息回答用户问题：

{{context}}"""
        elif has_web_search:
            system_prompt = """你是一名专业的地质学文献分析助手。请基于提供的本地文献和网络实时信息，为用户提供全面、准确的解答。

回答原则：
1. **综合多源信息**：结合本地文献的专业深度和网络信息的时效性
2. **明确标注来源**：
   - 引用本地文献时用【文献X】标记
   - 引用网络信息时用【来源X】标记
3. **信息整合**：将不同来源的信息有机整合，提供完整答案
4. **权威优先**：优先使用学术文献和官方信息
5. **时效性**：网络信息可以补充最新动态和数据

回答风格：
- 结构清晰，先总后分
- 标注信息来源，便于溯源
- 语言专业但易懂

{context}"""
        else:
            system_prompt = """你是一名专业的地质学文献分析助手。请基于提供的参考文献，结合你的专业知识，为用户提供全面、准确的解答。

回答原则：
1. **优先使用参考文献**：以提供的文献内容为主，确保信息准确性
2. **灵活整合信息**：当文献提供了相关信息时，可以进行合理的总结和解释
3. **补充专业知识**：如果文献信息不完整，可以适当补充相关的地质学背景知识
4. **明确标注来源**：在引用文献内容时，用【文献1】【文献2】等标记
5. **诚实回答**：如果文献完全不相关或无法回答，请明确说明

回答风格：
- 使用中文，语言清晰易懂
- 结构分明，分点阐述复杂内容
- 先给出直接答案，再补充详细解释

{context}"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "用户问题：{question}\n\n请基于上述参考信息回答问题：")
        ])


def create_web_enhanced_rag_retriever(collection_name: Optional[str] = None) -> WebEnhancedRAGRetriever:
    """创建 WebSearch 增强的 RAG 检索器
    
    Args:
        collection_name: 可选的知识库集合名称（用于自定义助手的专属知识库）
    """
    from src.database.chroma_manager import create_chroma_manager
    from src.core.llm_provider import create_llm_provider
    
    vector_store = create_chroma_manager(collection_name=collection_name)
    llm_provider = create_llm_provider()
    return WebEnhancedRAGRetriever(vector_store=vector_store, llm_provider=llm_provider)
