"""LLM Provider - 基于 LangChain 的大语言模型接口

使用 LangChain ChatOpenAI 实现，支持 OpenAI 兼容 API。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional, AsyncIterator

logger = logging.getLogger(__name__)

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models import BaseChatModel

from src.utils.config import get_config
from src.core.http_client_factory import create_http_clients


class LLMProvider(ABC):
    """大语言模型接口基类"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """同步生成文本"""
        raise NotImplementedError

    @abstractmethod
    def stream_generate(self, prompt: str, **kwargs: Any) -> Iterator[str]:
        """流式生成文本"""
        raise NotImplementedError
    
    @abstractmethod
    async def astream_generate(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """异步流式生成文本"""
        raise NotImplementedError
    
    @abstractmethod
    def get_langchain_llm(self) -> BaseChatModel:
        """获取底层 LangChain LLM 实例"""
        raise NotImplementedError


class LangChainLLMProvider(LLMProvider):
    """基于 LangChain ChatOpenAI 的 LLM 实现
    
    支持 OpenAI 兼容的 API（如 SiliconFlow、DeepSeek 等）
    使用 LangChain 原生流式输出
    """

    def __init__(
        self,
        api_key: str,
        api_endpoint: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60,
        use_env_proxy: bool = False,
        proxy_url: Optional[str] = None,
        max_retries: int = 0,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.api_key = api_key
        self.api_endpoint = api_endpoint.rstrip("/")
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.use_env_proxy = use_env_proxy
        self.proxy_url = proxy_url
        self.max_retries = max_retries
        self.extra_body = extra_body
        
        # 提取 base_url
        base_url = self._get_base_url()
        http_client, http_async_client = create_http_clients(
            timeout=float(timeout),
            use_env_proxy=use_env_proxy,
            proxy_url=proxy_url,
        )
        
        # 创建 LangChain ChatOpenAI 实例
        self._llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=float(timeout),
            max_retries=max_retries,
            streaming=True,
            http_client=http_client,
            http_async_client=http_async_client,
            extra_body=extra_body,
        )
    
    def _get_base_url(self) -> str:
        """从完整 endpoint 提取 base_url"""
        endpoint = self.api_endpoint
        # 移除 /chat/completions 后缀
        for suffix in ["/chat/completions", "/v1/chat/completions"]:
            if endpoint.endswith(suffix):
                endpoint = endpoint[:-len(suffix)]
                break
        # 确保以 /v1 结尾
        if not endpoint.endswith("/v1"):
            endpoint = endpoint.rstrip("/") + "/v1"
        return endpoint
    
    def get_langchain_llm(self) -> BaseChatModel:
        """获取底层 LangChain LLM 实例"""
        return self._llm

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """同步生成文本"""
        messages = [HumanMessage(content=prompt)]
        response = self._llm.invoke(messages)
        return response.content

    def stream_generate(self, prompt: str, **kwargs: Any) -> Iterator[str]:
        """流式生成文本"""
        messages = [HumanMessage(content=prompt)]
        for chunk in self._llm.stream(messages):
            if chunk.content:
                yield chunk.content

    async def astream_generate(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """异步流式生成文本"""
        messages = [HumanMessage(content=prompt)]
        async for chunk in self._llm.astream(messages):
            if chunk.content:
                yield chunk.content
    
    def chat(self, messages: List[dict], **kwargs: Any) -> str:
        """多轮对话"""
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        
        response = self._llm.invoke(langchain_messages)
        return response.content
    
    def stream_chat(self, messages: List[dict], **kwargs: Any) -> Iterator[str]:
        """流式多轮对话"""
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        
        for chunk in self._llm.stream(langchain_messages):
            if chunk.content:
                yield chunk.content

    async def astream_chat(self, messages: List[dict], **kwargs: Any) -> AsyncIterator[str]:
        """异步流式多轮对话"""
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        
        async for chunk in self._llm.astream(langchain_messages):
            if chunk.content:
                yield chunk.content


# 保留旧类名作为别名
SiliconFlowChatLLMProvider = LangChainLLMProvider


def create_llm_provider(
    temperature: float = None,
    *,
    enable_thinking: Optional[bool] = None,
    user_llm_config: Optional[Dict[str, Any]] = None,
) -> LLMProvider:
    """创建 LLMProvider 实例

    优先使用用户的个人 LLM 配置（user_llm_config），
    未配置时回退到 config.yaml 全局配置。

    Args:
        temperature: 可选的温度参数，覆盖默认值
        enable_thinking: 可选，启用思考链
        user_llm_config: 用户保存的 LLM 配置字典，包含:
            provider, base_url, api_key, model_name, temperature, max_tokens
    """
    config = get_config()
    llm_cfg = config.get_llm_config()

    # 用户配置优先
    if user_llm_config and user_llm_config.get("api_key") and user_llm_config.get("base_url"):
        from src.utils.llm_url import normalize_openai_base_url
        api_key = user_llm_config["api_key"]
        # 直接规范化为 /v1 级别，跳过 _ensure_chat_endpoint → _get_base_url 的往返
        base_url = normalize_openai_base_url(user_llm_config["base_url"])
        api_endpoint = base_url  # ChatOpenAI 内部会追加 /chat/completions
        model_name = user_llm_config.get("model_name", llm_cfg.get("model_name", ""))
        temp = temperature if temperature is not None else user_llm_config.get("temperature", 0.7)
        max_tokens = user_llm_config.get("max_tokens", 2048)
        timeout = llm_cfg.get("request_timeout", 60)
        use_env_proxy = llm_cfg.get("use_env_proxy", False)
        proxy_url = llm_cfg.get("proxy_url")
        max_retries = llm_cfg.get("max_retries", 0)
        logger.info(
            "[LLM] 使用用户配置: provider=%s model=%s base_url=%s",
            user_llm_config.get("provider"), model_name, base_url,
        )
    else:
        # 回退到全局配置（常见于 llm_config 无 api_key 或未保存）
        logger.warning(
            "用户 LLM 配置未生效，回退全局配置 (user_llm=%s)",
            "present" if user_llm_config else "none",
        )
        provider = llm_cfg.get("provider")
        if provider != "siliconflow":
            raise ValueError(f"不支持的 LLM provider: {provider}")
        api_key = llm_cfg.get("api_key")
        api_endpoint = llm_cfg.get("api_endpoint")
        model_name = llm_cfg.get("model_name")
        temp = temperature if temperature is not None else llm_cfg.get("temperature", 0.7)
        max_tokens = llm_cfg.get("max_tokens", 2048)
        timeout = llm_cfg.get("request_timeout", 60)
        use_env_proxy = llm_cfg.get("use_env_proxy", False)
        proxy_url = llm_cfg.get("proxy_url")
        max_retries = llm_cfg.get("max_retries", 0)

    if not api_key or not api_endpoint or not model_name:
        raise ValueError("LLM 配置不完整：缺少 api_key / api_endpoint / model_name")

    extra_body = (
        {"enable_thinking": enable_thinking}
        if enable_thinking is not None
        else None
    )

    return SiliconFlowChatLLMProvider(
        api_key=api_key,
        api_endpoint=api_endpoint,
        model_name=model_name,
        temperature=temp,
        max_tokens=max_tokens,
        timeout=timeout,
        use_env_proxy=use_env_proxy,
        proxy_url=proxy_url,
        max_retries=max_retries,
        extra_body=extra_body,
    )


def _ensure_chat_endpoint(base_url: str) -> str:
    """确保 base_url 包含 /chat/completions 路径"""
    from src.utils.llm_url import normalize_chat_endpoint
    return normalize_chat_endpoint(base_url)
