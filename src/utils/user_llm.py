"""用户 LLM 配置解析 — 供 settings API 与 chat 路由共用"""

import logging
from typing import Optional, Dict, Any, List

from src.database.models import UserPreference

logger = logging.getLogger(__name__)


def _settings_dict(preference: Optional[UserPreference]) -> Dict[str, Any]:
    if preference and preference.settings and isinstance(preference.settings, dict):
        return preference.settings
    return {}


def _find_api_key_in_tested(
    settings: Dict[str, Any],
    provider: Optional[str] = None,
) -> Optional[str]:
    """从 tested_models 中查找 api_key（优先匹配 provider）"""
    tested = settings.get("tested_models")
    if not isinstance(tested, list):
        return None

    connected = [
        t for t in tested
        if isinstance(t, dict) and t.get("connected") and t.get("api_key") and t.get("base_url")
    ]
    connected.sort(key=lambda t: t.get("tested_at", 0), reverse=True)

    if provider:
        for t in connected:
            if t.get("provider") == provider:
                return t["api_key"]
        return None

    if connected:
        return connected[0]["api_key"]
    return None


def merge_llm_api_key(cfg: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    """合并 api_key：保留 cfg 中的 key，否则从 tested_models 补齐"""
    out = dict(cfg)
    if out.get("api_key"):
        return out
    key = _find_api_key_in_tested(settings, out.get("provider"))
    if key:
        out["api_key"] = key
    return out


def resolve_user_llm_config(
    preference: Optional[UserPreference],
    *,
    require_api_key: bool = True,
) -> Optional[Dict[str, Any]]:
    """统一的用户 LLM 配置解析逻辑

    优先级：
    1. settings.llm_config（含 base_url）— 若 require_api_key，必须能解析出 api_key
       （自身或同 provider 的 tested_models），否则视为无效并继续回退
    2. tested_models 中 connected=True、按 tested_at 降序、首个含 api_key 的项
    3. None

    Args:
        require_api_key: True 时供 chat/推理使用；False 时供 GET 展示（可返回无 key 的配置）
    """
    settings = _settings_dict(preference)
    if not settings:
        return None

    cfg = settings.get("llm_config")
    if isinstance(cfg, dict) and cfg.get("base_url"):
        merged = merge_llm_api_key(cfg, settings)
        if merged.get("api_key"):
            return merged
        if not require_api_key:
            logger.debug(
                "llm_config 缺少 api_key (provider=%s model=%s)，require_api_key=False，返回无 key 配置",
                cfg.get("provider"), cfg.get("model_name"),
            )
            return merged
        # require_api_key=True 但 llm_config 解析不出 api_key → 回退
        logger.warning(
            "llm_config 缺少 api_key (provider=%s model=%s)，require_api_key=True，回退到 tested_models",
            cfg.get("provider"), cfg.get("model_name"),
        )

    tested = settings.get("tested_models")
    if isinstance(tested, list):
        connected = [
            t for t in tested
            if isinstance(t, dict) and t.get("connected") and t.get("api_key") and t.get("base_url")
        ]
        connected.sort(key=lambda t: t.get("tested_at", 0), reverse=True)
        if connected:
            fallback = connected[0]
            logger.warning(
                "使用 tested_models 回退: provider=%s model=%s (tested_at=%s)",
                fallback.get("provider"), fallback.get("model_name"), fallback.get("tested_at"),
            )
            return dict(fallback)

    logger.warning("未找到任何可用的 LLM 配置 (user preference 为空或缺失必要字段)")
    return None


def load_user_llm_config(db, user_id: int) -> Optional[Dict[str, Any]]:
    """从数据库加载并解析用户 LLM 配置（供 chat 路由使用，必须有 api_key）"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        pref = db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()
        return resolve_user_llm_config(pref, require_api_key=True)
    except Exception:
        logger.exception("加载用户 %s LLM 配置失败", user_id)
        return None


def _is_valid_llm_config(cfg: Any) -> bool:
    """配置格式有效（允许 api_key 为空，仅用于展示校验）"""
    return (
        isinstance(cfg, dict)
        and bool(cfg.get("base_url"))
        and bool(cfg.get("model_name"))
    )
