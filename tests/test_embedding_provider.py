import os
import sys
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.embedding_provider import SiliconFlowEmbeddingProvider


class TestSiliconFlowEmbeddingProvider(unittest.TestCase):
    @patch("src.core.embedding_provider.OpenAIEmbeddings")
    def test_embed_text_single(self, mock_openai_embeddings):
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_openai_embeddings.return_value = mock_embeddings

        provider = SiliconFlowEmbeddingProvider(
            api_key="test-key",
            api_endpoint="https://api.siliconflow.cn/v1/embeddings",
            model_name="test-model",
            timeout=5,
        )

        vec = provider.embed_text("hello")
        self.assertEqual(vec, [0.1, 0.2, 0.3])
        mock_embeddings.embed_query.assert_called_once_with("hello")

        _, kwargs = mock_openai_embeddings.call_args
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(kwargs["base_url"], "https://api.siliconflow.cn/v1")
        self.assertEqual(kwargs["max_retries"], 0)
        self.assertFalse(kwargs["http_client"]._trust_env)
        self.assertFalse(kwargs["http_async_client"]._trust_env)

        kwargs["http_client"].close()
        import asyncio
        asyncio.run(kwargs["http_async_client"].aclose())

    @patch("src.core.embedding_provider.OpenAIEmbeddings")
    def test_embed_batch_multiple(self, mock_openai_embeddings):
        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1], [0.2]]
        mock_openai_embeddings.return_value = mock_embeddings

        provider = SiliconFlowEmbeddingProvider(
            api_key="test-key",
            api_endpoint="https://api.siliconflow.cn/v1/embeddings",
            model_name="test-model",
            timeout=5,
        )

        vecs = provider.embed_batch(["a", "b"])
        self.assertEqual(vecs, [[0.1], [0.2]])
        mock_embeddings.embed_documents.assert_called_once_with(["a", "b"])

        _, kwargs = mock_openai_embeddings.call_args
        kwargs["http_client"].close()
        import asyncio
        asyncio.run(kwargs["http_async_client"].aclose())


if __name__ == "__main__":
    unittest.main()
