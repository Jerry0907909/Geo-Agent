"""测试 LLM 配置相关逻辑"""
import pytest
from unittest.mock import MagicMock, patch

from src.utils.user_llm import resolve_user_llm_config, load_user_llm_config, _is_valid_llm_config
from src.api.settings_routes import _classify_llm_error


class TestResolveUserLlmConfig:
    def test_returns_none_for_none_preference(self):
        assert resolve_user_llm_config(None) is None

    def test_returns_none_for_empty_settings(self):
        pref = MagicMock()
        pref.settings = None
        assert resolve_user_llm_config(pref) is None

        pref.settings = {}
        assert resolve_user_llm_config(pref) is None

    def test_returns_llm_config_when_valid(self):
        pref = MagicMock()
        pref.settings = {
            "llm_config": {
                "api_key": "sk-test",
                "base_url": "https://api.test.com/v1",
                "provider": "Test",
                "model_name": "test-model",
            }
        }
        result = resolve_user_llm_config(pref)
        assert result is not None
        assert result["api_key"] == "sk-test"

    def test_display_mode_returns_config_without_api_key(self):
        """GET 展示：允许无 api_key"""
        pref = MagicMock()
        pref.settings = {
            "llm_config": {
                "api_key": "",
                "base_url": "https://api.test.com/v1",
                "provider": "Test",
                "model_name": "test-model",
            }
        }
        result = resolve_user_llm_config(pref, require_api_key=False)
        assert result is not None
        assert result["provider"] == "Test"

    def test_chat_mode_falls_back_when_llm_config_has_no_api_key(self):
        """对话：llm_config 无 key 时应回退 tested，而不是返回无效配置"""
        pref = MagicMock()
        pref.settings = {
            "llm_config": {
                "api_key": "",
                "base_url": "https://api.stale.com/v1",
                "provider": "Stale",
                "model_name": "stale-model",
            },
            "tested_models": [
                {
                    "provider": "DeepSeek",
                    "api_key": "sk-ds",
                    "base_url": "https://api.deepseek.com/v1",
                    "model_name": "deepseek-chat",
                    "connected": True,
                    "tested_at": 1000,
                },
            ],
        }
        result = resolve_user_llm_config(pref, require_api_key=True)
        assert result is not None
        assert result["provider"] == "DeepSeek"
        assert result["api_key"] == "sk-ds"

    def test_merge_api_key_from_tested_same_provider(self):
        pref = MagicMock()
        pref.settings = {
            "llm_config": {
                "api_key": "",
                "base_url": "https://api.deepseek.com/v1",
                "provider": "DeepSeek",
                "model_name": "deepseek-v4",
            },
            "tested_models": [
                {
                    "provider": "DeepSeek",
                    "api_key": "sk-ds",
                    "base_url": "https://api.deepseek.com/v1",
                    "model_name": "deepseek-chat",
                    "connected": True,
                    "tested_at": 1000,
                },
            ],
        }
        result = resolve_user_llm_config(pref, require_api_key=True)
        assert result["api_key"] == "sk-ds"
        assert result["model_name"] == "deepseek-v4"

    def test_falls_back_to_tested_models(self):
        pref = MagicMock()
        pref.settings = {
            "llm_config": None,
            "tested_models": [
                {
                    "provider": "DeepSeek",
                    "api_key": "sk-ds",
                    "base_url": "https://api.deepseek.com/v1",
                    "model_name": "deepseek-chat",
                    "connected": True,
                    "tested_at": 1000,
                },
                {
                    "provider": "OpenAI",
                    "api_key": "sk-oai",
                    "base_url": "https://api.openai.com/v1",
                    "model_name": "gpt-4o",
                    "connected": True,
                    "tested_at": 2000,
                },
            ]
        }
        result = resolve_user_llm_config(pref)
        assert result is not None
        # Should return most recent tested
        assert result["provider"] == "OpenAI"
        assert result["tested_at"] == 2000

    def test_llm_config_priority_over_tested(self):
        pref = MagicMock()
        pref.settings = {
            "llm_config": {
                "api_key": "sk-priority",
                "base_url": "https://api.priority.com/v1",
                "provider": "Priority",
                "model_name": "priority-model",
            },
            "tested_models": [
                {
                    "provider": "Tested",
                    "api_key": "sk-tested",
                    "base_url": "https://api.tested.com/v1",
                    "model_name": "tested-model",
                    "connected": True,
                    "tested_at": 9999,
                }
            ]
        }
        result = resolve_user_llm_config(pref)
        assert result["api_key"] == "sk-priority"
        assert result["provider"] == "Priority"


class TestClassifyLlmError:
    def test_classify_connection_refused(self):
        hint = _classify_llm_error("Connection refused")
        assert "Base URL" in hint

    def test_classify_401(self):
        hint = _classify_llm_error("401 Unauthorized")
        assert "API Key" in hint

    def test_classify_404(self):
        hint = _classify_llm_error("404 Not Found")
        assert "Base URL" in hint

    def test_classify_timeout(self):
        hint = _classify_llm_error("timeout error occurred")
        assert "超时" in hint

    def test_classify_unknown(self):
        hint = _classify_llm_error("Some unknown error")
        assert "Some unknown error" in hint


class TestIsValidLlmConfig:
    def test_valid_with_api_key(self):
        assert _is_valid_llm_config({"api_key": "sk", "base_url": "https://test.com/v1", "model_name": "gpt-4o"})

    def test_valid_without_api_key(self):
        """api_key 为空仍视为有效（ModelSelector 需要展示）"""
        assert _is_valid_llm_config({"api_key": "", "base_url": "https://test.com/v1", "model_name": "gpt-4o"})

    def test_missing_base_url(self):
        assert not _is_valid_llm_config({"api_key": "sk", "base_url": "", "model_name": "gpt-4o"})

    def test_missing_model_name(self):
        assert not _is_valid_llm_config({"api_key": "sk", "base_url": "https://test.com/v1"})

    def test_not_dict(self):
        assert not _is_valid_llm_config("not a dict")
        assert not _is_valid_llm_config(None)
