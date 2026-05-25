"""Vision Provider - 多模态视觉模型接口

支持图像理解和视觉问答功能。
"""

from __future__ import annotations

import base64
import logging
from typing import Any, AsyncIterator, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.utils.config import get_config
from src.core.http_client_factory import create_http_clients

logger = logging.getLogger(__name__)


class VisionProvider:
    """多模态视觉模型提供者
    
    支持图像理解、视觉问答等功能。
    使用 OpenAI 兼容的 Vision API。
    """

    def __init__(
        self,
        api_key: str,
        api_endpoint: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 120,
        use_env_proxy: bool = False,
        proxy_url: Optional[str] = None,
        max_retries: int = 0,
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
        
        base_url = self._get_base_url()
        http_client, http_async_client = create_http_clients(
            timeout=float(timeout),
            use_env_proxy=use_env_proxy,
            proxy_url=proxy_url,
        )
        
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
        )
    
    def _get_base_url(self) -> str:
        """从完整 endpoint 提取 base_url"""
        endpoint = self.api_endpoint
        for suffix in ["/chat/completions", "/v1/chat/completions"]:
            if endpoint.endswith(suffix):
                endpoint = endpoint[:-len(suffix)]
                break
        if not endpoint.endswith("/v1"):
            endpoint = endpoint.rstrip("/") + "/v1"
        return endpoint

    def _encode_image(self, image_data: bytes) -> str:
        """将图像数据编码为base64"""
        return base64.b64encode(image_data).decode("utf-8")

    def _get_image_media_type(self, image_data: bytes) -> str:
        """检测图像类型"""
        if image_data[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        elif image_data[:2] == b'\xff\xd8':
            return "image/jpeg"
        elif image_data[:6] in (b'GIF87a', b'GIF89a'):
            return "image/gif"
        elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
            return "image/webp"
        return "image/jpeg"  # 默认

    def analyze_image(
        self,
        image_data: bytes,
        question: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """分析图像并回答问题
        
        Args:
            image_data: 图像二进制数据
            question: 用户问题
            system_prompt: 系统提示词
            
        Returns:
            AI回答
        """
        base64_image = self._encode_image(image_data)
        media_type = self._get_image_media_type(image_data)
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        messages.append(HumanMessage(content=[
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{base64_image}"
                }
            },
            {
                "type": "text",
                "text": question
            }
        ]))
        
        response = self._llm.invoke(messages)
        return response.content

    async def astream_analyze_image(
        self,
        image_data: bytes,
        question: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[dict]] = None,
    ) -> AsyncIterator[str]:
        """异步流式分析图像
        
        Args:
            image_data: 图像二进制数据
            question: 用户问题
            system_prompt: 系统提示词
            history: 历史对话
            
        Yields:
            AI回答的文本片段
        """
        base64_image = self._encode_image(image_data)
        media_type = self._get_image_media_type(image_data)
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        # 添加历史对话
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    from langchain_core.messages import AIMessage
                    messages.append(AIMessage(content=content))
        
        # 添加带图像的用户消息
        messages.append(HumanMessage(content=[
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{base64_image}"
                }
            },
            {
                "type": "text",
                "text": question
            }
        ]))
        
        async for chunk in self._llm.astream(messages):
            if chunk.content:
                yield chunk.content

    async def astream_chat_with_image(
        self,
        image_data: Optional[bytes],
        question: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[dict]] = None,
    ) -> AsyncIterator[str]:
        """异步流式对话（可选图像）
        
        支持纯文本对话或带图像的对话。
        
        Args:
            image_data: 图像二进制数据（可选）
            question: 用户问题
            system_prompt: 系统提示词
            history: 历史对话
            
        Yields:
            AI回答的文本片段
        """
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        # 添加历史对话
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    from langchain_core.messages import AIMessage
                    messages.append(AIMessage(content=content))
        
        # 构建用户消息
        if image_data:
            base64_image = self._encode_image(image_data)
            media_type = self._get_image_media_type(image_data)
            messages.append(HumanMessage(content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{base64_image}"
                    }
                },
                {
                    "type": "text",
                    "text": question
                }
            ]))
        else:
            messages.append(HumanMessage(content=question))
        
        async for chunk in self._llm.astream(messages):
            if chunk.content:
                yield chunk.content


def create_vision_provider() -> VisionProvider:
    """创建视觉模型提供者实例（使用 config.yaml 全局配置）"""
    config = get_config()
    llm_cfg = config.get_llm_config()

    api_key = llm_cfg.get("api_key")
    api_endpoint = llm_cfg.get("api_endpoint")
    model_name = llm_cfg.get("vision_model_name") or llm_cfg.get("model_name")
    temperature = llm_cfg.get("temperature", 0.7)
    max_tokens = llm_cfg.get("max_tokens", 2048)

    timeout = llm_cfg.get("request_timeout", 120)
    use_env_proxy = llm_cfg.get("use_env_proxy", False)
    proxy_url = llm_cfg.get("proxy_url")
    max_retries = llm_cfg.get("max_retries", 0)

    if not api_key or not api_endpoint or not model_name:
        raise ValueError("Vision LLM 配置不完整")
    
    return VisionProvider(
        api_key=api_key,
        api_endpoint=api_endpoint,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        use_env_proxy=use_env_proxy,
        proxy_url=proxy_url,
        max_retries=max_retries,
    )
