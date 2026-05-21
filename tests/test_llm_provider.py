import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.llm_provider import SiliconFlowChatLLMProvider


class TestSiliconFlowChatLLMProvider(unittest.TestCase):
    @patch("src.core.llm_provider.ChatOpenAI")
    def test_generate_basic(self, mock_chat_openai):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = SimpleNamespace(content="你好，世界")
        mock_chat_openai.return_value = mock_llm

        provider = SiliconFlowChatLLMProvider(
            api_key="test-key",
            api_endpoint="https://api.siliconflow.cn/v1/chat/completions",
            model_name="test-model",
            temperature=0.5,
            max_tokens=128,
            timeout=5,
        )

        output = provider.generate("hello")
        self.assertEqual(output, "你好，世界")

        mock_llm.invoke.assert_called_once()
        _, kwargs = mock_chat_openai.call_args
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(kwargs["base_url"], "https://api.siliconflow.cn/v1")
        self.assertEqual(kwargs["max_retries"], 0)
        self.assertFalse(kwargs["http_client"]._trust_env)
        self.assertFalse(kwargs["http_async_client"]._trust_env)

        kwargs["http_client"].close()
        import asyncio
        asyncio.run(kwargs["http_async_client"].aclose())

    @patch("src.core.llm_provider.ChatOpenAI")
    def test_stream_generate_uses_langchain_stream(self, mock_chat_openai):
        mock_llm = MagicMock()
        mock_llm.stream.return_value = [
            SimpleNamespace(content="stream"),
            SimpleNamespace(content=" text"),
        ]
        mock_chat_openai.return_value = mock_llm

        provider = SiliconFlowChatLLMProvider(
            api_key="test-key",
            api_endpoint="https://api.siliconflow.cn/v1/chat/completions",
            model_name="test-model",
        )

        chunks = list(provider.stream_generate("hello"))
        self.assertEqual("".join(chunks), "stream text")
        mock_llm.stream.assert_called_once()

        _, kwargs = mock_chat_openai.call_args
        kwargs["http_client"].close()
        import asyncio
        asyncio.run(kwargs["http_async_client"].aclose())

    @patch("src.core.llm_provider.ChatOpenAI")
    def test_provider_passes_extra_body(self, mock_chat_openai):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = SimpleNamespace(content="ok")
        mock_chat_openai.return_value = mock_llm

        provider = SiliconFlowChatLLMProvider(
            api_key="test-key",
            api_endpoint="https://api.siliconflow.cn/v1/chat/completions",
            model_name="test-model",
            extra_body={"enable_thinking": False},
        )

        self.assertEqual(provider.generate("hello"), "ok")

        _, kwargs = mock_chat_openai.call_args
        self.assertEqual(kwargs["extra_body"], {"enable_thinking": False})

        kwargs["http_client"].close()
        import asyncio
        asyncio.run(kwargs["http_async_client"].aclose())


if __name__ == "__main__":
    unittest.main()
