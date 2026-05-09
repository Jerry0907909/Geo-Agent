"""LLM Provider - 基于 LangChain 的大语言模型接口

使用 LangChain ChatOpenAI 实现，支持 OpenAI 兼容 API。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator, List, Optional, AsyncIterator

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models import BaseChatModel

from src.utils.config import get_config


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
    ) -> None:
        self.api_key = api_key
        self.api_endpoint = api_endpoint.rstrip("/")
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # 提取 base_url
        base_url = self._get_base_url()
        
        # 创建 LangChain ChatOpenAI 实例
        self._llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=float(timeout),
            streaming=True,
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


def create_llm_provider(temperature: float = None) -> LLMProvider:
    """根据全局配置创建默认的 LLMProvider 实例
    
    Args:
        temperature: 可选的温度参数，覆盖配置文件中的默认值
    """

    config = get_config()
    llm_cfg = config.get_llm_config()

    provider = llm_cfg.get("provider")
    if provider == "siliconflow":
        api_key = llm_cfg.get("api_key")
        api_endpoint = llm_cfg.get("api_endpoint")
        model_name = llm_cfg.get("model_name")
        temp = temperature if temperature is not None else llm_cfg.get("temperature", 0.7)
        max_tokens = llm_cfg.get("max_tokens", 2048)
        timeout = llm_cfg.get("request_timeout", 60)

        if not api_key or not api_endpoint or not model_name:
            raise ValueError("SiliconFlow LLM 配置不完整")

        return SiliconFlowChatLLMProvider(
            api_key=api_key,
            api_endpoint=api_endpoint,
            model_name=model_name,
            temperature=temp,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    raise ValueError(f"不支持的 LLM provider: {provider}")

