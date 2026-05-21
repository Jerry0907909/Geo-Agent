"""设置管理 API 路由

提供 LLM 配置、用户偏好等设置的 CRUD 接口。
"""

import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth_schemas import LLMConfigRequest, LLMConfigResponse
from src.auth.deps import get_current_active_user, get_db
from src.auth.security import get_password_hash, verify_password
from src.database.models import User, UserPreference
from src.utils.user_llm import merge_llm_api_key, resolve_user_llm_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["设置"])

DEFAULT_LLM_CONFIGS = {
    "硅基流动 (SiliconFlow)": {
        "provider": "硅基流动 (SiliconFlow)",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "",
        "model_name": "Qwen/Qwen3.5-9B",
        "temperature": 0.7,
        "max_tokens": 2048,
    },
    "DeepSeek": {
        "provider": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "model_name": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 4096,
    },
    "OpenAI": {
        "provider": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model_name": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4096,
    },
    "阿里百炼 (Alibaba Bailian)": {
        "provider": "阿里百炼 (Alibaba Bailian)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "",
        "model_name": "qwen-plus",
        "temperature": 0.7,
        "max_tokens": 2048,
    },
    "ParaTera (超算互联网)": {
        "provider": "ParaTera (超算互联网)",
        "base_url": "https://ai.paratera.com/v1",
        "api_key": "",
        "model_name": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 4096,
    },
}


def _get_settings_json(preference: Optional[UserPreference]) -> dict:
    if preference and preference.settings:
        return preference.settings if isinstance(preference.settings, dict) else {}
    return {}


def _save_settings_json(db: Session, user_id: int, preference: Optional[UserPreference], data: dict) -> None:
    if preference:
        preference.settings = data
    else:
        preference = UserPreference(user_id=user_id, settings=data)
        db.add(preference)
    db.commit()


@router.get("/llm-config")
async def get_llm_config(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的 LLM 配置（与 chat 路由共用 resolve_user_llm_config）"""
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()

    resolved = resolve_user_llm_config(preference, require_api_key=False)

    if resolved:
        settings = _get_settings_json(preference)
        has_saved = bool(settings.get("llm_config"))
        has_key = bool(resolved.get("api_key"))
        if has_saved and has_key:
            source = "saved"
        elif has_saved:
            source = "saved_no_key"
        else:
            source = "tested_fallback"
        return {**LLMConfigResponse(**resolved).model_dump(), "source": source}

    # 回退默认
    default = DEFAULT_LLM_CONFIGS["硅基流动 (SiliconFlow)"]
    return {**LLMConfigResponse(**default).model_dump(), "source": "default"}


@router.put("/llm-config", response_model=LLMConfigResponse)
async def update_llm_config(
    request: LLMConfigRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """更新当前用户的 LLM 配置"""
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()
    data = _get_settings_json(preference)
    incoming = request.model_dump()
    existing = data.get("llm_config") if isinstance(data.get("llm_config"), dict) else {}
    # 避免前端选择预设时用空 api_key 覆盖已保存的密钥
    if not incoming.get("api_key"):
        if existing.get("api_key"):
            incoming["api_key"] = existing["api_key"]
        else:
            merged = merge_llm_api_key(incoming, data)
            if merged.get("api_key"):
                incoming["api_key"] = merged["api_key"]
    data["llm_config"] = incoming
    _save_settings_json(db, current_user.id, preference, data)

    logger.info("用户 %s 更新了 LLM 配置: provider=%s, model=%s",
                current_user.username, incoming.get("provider"), incoming.get("model_name"))
    return {**LLMConfigResponse(**incoming).model_dump(), "source": "saved"}


@router.post("/llm-config/test")
async def test_llm_connection(
    request: LLMConfigRequest,
    current_user: User = Depends(get_current_active_user),
):
    """测试 LLM 连接 — 优先使用 chat.completions（与实际对话路径一致）"""
    from openai import OpenAI
    from src.utils.llm_url import normalize_openai_base_url

    # OpenAI client 会在 base_url 后自动追加 /chat/completions，这里只传 /v1 级别
    base = normalize_openai_base_url(request.base_url)
    client = OpenAI(
        api_key=request.api_key,
        base_url=base,
        timeout=15.0,
    )

    # 优先：轻量 completion 验证（与真实 chat 路径一致）
    method = "completion"
    try:
        start = time.time()
        client.chat.completions.create(
            model=request.model_name,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "success": True,
            "message": f"连接成功 ({elapsed_ms}ms)",
            "elapsed_ms": elapsed_ms,
            "method": method,
            "requested_model_available": True,
        }
    except Exception as e:
        error_msg = str(e)
        # completion 失败时，尝试 models.list 辅助诊断
        if "model" in error_msg.lower() and ("not found" in error_msg.lower() or "exist" in error_msg.lower()):
            method = "models_list"
            try:
                models = client.models.list(timeout=10)
                model_ids = [m.id for m in models.data[:10]] if models.data else []
                return {
                    "success": True,
                    "message": f"模型 {request.model_name} 未在列表中，但 API 连接正常",
                    "method": method,
                    "available_models": model_ids[:5],
                    "requested_model_available": False,
                }
            except Exception as e2:
                error_msg = str(e2)

        hint = _classify_llm_error(error_msg)
        logger.warning("LLM 连接测试失败: %s", error_msg[:120])
        return {
            "success": False,
            "message": "连接失败",
            "hint": hint,
            "method": method,
        }


def _classify_llm_error(error_msg: str) -> str:
    if "Connection refused" in error_msg or "Name or service not known" in error_msg:
        return "无法连接到服务器，请检查 Base URL 是否正确"
    if "401" in error_msg or "Unauthorized" in error_msg or "invalid" in error_msg.lower():
        return "API Key 无效，请检查密钥是否正确"
    if "404" in error_msg or "Not Found" in error_msg:
        return "端点不存在，请检查 Base URL 路径"
    if "timeout" in error_msg.lower():
        return "连接超时，请检查网络或服务器状态"
    return error_msg[:200]


@router.get("/llm-presets")
async def get_llm_presets(
    current_user: User = Depends(get_current_active_user),
):
    """获取预设的 LLM 提供商配置模板"""
    presets = []
    for name, cfg in DEFAULT_LLM_CONFIGS.items():
        presets.append({
            "name": name,
            "base_url": cfg["base_url"],
            "model_name": cfg["model_name"],
        })
    return {"presets": presets}


@router.put("/llm-config/reset")
async def reset_llm_config(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """重置 LLM 配置为默认值（同时清空 tested_models）"""
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()
    data = _get_settings_json(preference)
    data.pop("llm_config", None)
    data.pop("tested_models", None)
    _save_settings_json(db, current_user.id, preference, data)

    default = DEFAULT_LLM_CONFIGS["硅基流动 (SiliconFlow)"]
    return {**LLMConfigResponse(**default).model_dump(), "source": "default"}


@router.get("/tested-models")
async def get_tested_models(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取已通过连接测试的模型列表（供 ChatPage 模型选择器使用）"""
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()
    data = _get_settings_json(preference)
    tested = data.get("tested_models", [])
    if isinstance(tested, list):
        return {"models": tested}
    return {"models": []}


@router.post("/tested-models")
async def save_tested_model(
    request: LLMConfigRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """将测试成功的模型配置保存到已测试列表"""
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()
    data = _get_settings_json(preference)
    tested: list = data.get("tested_models", [])
    if not isinstance(tested, list):
        tested = []

    cfg = request.model_dump()
    existing_llm = data.get("llm_config") if isinstance(data.get("llm_config"), dict) else {}
    if not cfg.get("api_key") and existing_llm.get("api_key") and existing_llm.get("provider") == cfg.get("provider"):
        cfg["api_key"] = existing_llm["api_key"]
    # 去重（provider + model_name 唯一，避免不同模型互相覆盖）
    def _key(m): return f"{m.get('provider', '')}::{m.get('model_name', '')}"
    tested = [m for m in tested if _key(m) != _key(cfg)]
    cfg["tested_at"] = int(time.time())
    cfg["connected"] = True
    tested.append(cfg)
    # 只保留最近 10 条
    tested = tested[-10:]

    data["tested_models"] = tested
    _save_settings_json(db, current_user.id, preference, data)
    return {"models": tested}


@router.delete("/tested-models/{provider_name:path}")
async def remove_tested_model(
    provider_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """从已测试列表中移除指定模型"""
    preference = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()
    data = _get_settings_json(preference)
    tested: list = data.get("tested_models", [])
    data["tested_models"] = [m for m in tested if m.get("provider") != provider_name]
    _save_settings_json(db, current_user.id, preference, data)
    return {"models": data["tested_models"]}
