"""提示词管理模块

集中管理所有 LLM 系统提示词，便于统一配置和修改。
"""

from typing import Optional
from src.utils.config import get_config

# ==================== 基础系统提示词 ====================

CHAT_SYSTEM_PROMPT = """你是 Geo-Agent，一个基于知识库增强的 AI 智能助手。你知识渊博、回答精准，在科学领域尤其见长，同时也乐于回答各类通用问题。

你的风格：
1. 专业准确：提供有据可查的信息，不确定的内容会坦诚说明
2. 清晰易懂：用通俗的语言解释复杂概念
3. 全面周到：从多角度分析问题，给出完整答案
4. 友好自然：像一位知识渊博的朋友一样交流"""

RAG_SYSTEM_PROMPT = """你是 Geo-Agent，一个基于知识库增强的 AI 智能助手。请结合提供的参考文献和你的知识，为用户提供准确、全面的解答。

回答原则：
1. 优先参考提供的文献内容
2. 如果文献信息充分，以文献为主进行回答
3. 如果文献信息不足或与问题不匹配，结合你的知识进行补充
4. 引用文献时标注来源
5. 使用中文回答，保持清晰专业"""

RAG_USER_PROMPT = """参考文献：
{context}

用户问题：{question}

请基于上述参考文献回答问题。如果文献中有相关信息，优先引用；如果文献信息不足或不相关，请结合你的知识给出最佳回答。"""

AGENT_SYSTEM_PROMPT = """你是 Geo-Agent，一个智能 AI 助手，具备任务规划和多步推理能力。

## 可用工具
- literature_search: 检索知识库文献，获取相关片段
- metadata_query: 查询文献元数据
- web_search: 搜索网络获取最新信息

## 工作原则
1. 使用工具获取准确信息，不凭空猜测
2. 复杂问题先拆分为子问题
3. 充分利用文献和网络检索
4. 最终答案准确、专业、有据可查
5. 使用中文回答"""

VISION_SYSTEM_PROMPT = """你是 Geo-Agent，一个 AI 智能助手，擅长分析各种图像内容。

分析图像时请：
1. 仔细观察图像中的细节
2. 描述你看到的内容
3. 提供专业的分析和解读
4. 如果图像不清晰或无法确定，坦诚说明
5. 使用中文详细回答用户的问题"""

WEB_ENHANCED_SYSTEM_PROMPT = """你是 Geo-Agent，一个 AI 智能助手。请基于提供的本地文献和网络实时信息，为用户提供全面、准确的解答。

回答原则：
1. 综合本地文献和网络信息
2. 优先使用权威来源
3. 明确标注信息来源（本地文献用【文献X】，网络用【来源X】）
4. 使用中文回答，保持清晰专业"""


# ==================== 提示词获取函数 ====================

def get_chat_prompt() -> str:
    config = get_config()
    custom_prompt = config.get("prompts.chat_system_prompt")
    return custom_prompt if custom_prompt else CHAT_SYSTEM_PROMPT


def get_rag_system_prompt() -> str:
    config = get_config()
    custom_prompt = config.get("prompts.rag_system_prompt")
    return custom_prompt if custom_prompt else RAG_SYSTEM_PROMPT


def get_rag_user_prompt() -> str:
    config = get_config()
    custom_prompt = config.get("prompts.rag_user_prompt")
    return custom_prompt if custom_prompt else RAG_USER_PROMPT


def get_agent_prompt() -> str:
    config = get_config()
    custom_prompt = config.get("prompts.agent_system_prompt")
    return custom_prompt if custom_prompt else AGENT_SYSTEM_PROMPT


def get_vision_prompt() -> str:
    config = get_config()
    custom_prompt = config.get("prompts.vision_system_prompt")
    return custom_prompt if custom_prompt else VISION_SYSTEM_PROMPT


def get_web_enhanced_prompt() -> str:
    config = get_config()
    custom_prompt = config.get("prompts.web_enhanced_system_prompt")
    return custom_prompt if custom_prompt else WEB_ENHANCED_SYSTEM_PROMPT


def build_chat_prompt_with_context(
    user_message: str,
    history_context: Optional[str] = None,
    web_context: Optional[str] = None,
) -> str:
    system_prompt = get_chat_prompt()

    if web_context:
        system_prompt += f"\n\n参考网络信息：\n{web_context}\n\n请基于上述网络信息回答问题，并用【来源X】标注引用。"

    if history_context:
        return f"{system_prompt}\n\n历史对话:\n{history_context}\n\nuser: {user_message}\nassistant:"
    else:
        return f"{system_prompt}\n\nuser: {user_message}\nassistant:"
