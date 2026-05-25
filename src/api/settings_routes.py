"""设置管理 API 路由

提供用户偏好等设置的 CRUD 接口。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.auth.deps import get_current_active_user, get_db
from src.database.models import User, UserPreference

router = APIRouter(prefix="/settings", tags=["设置"])


def _get_settings_json(preference) -> dict:
    if preference and preference.settings:
        return preference.settings if isinstance(preference.settings, dict) else {}
    return {}


def _save_settings_json(db: Session, user_id: int, preference, data: dict) -> None:
    if preference:
        preference.settings = data
    else:
        preference = UserPreference(user_id=user_id, settings=data)
        db.add(preference)
    db.commit()


# LLM 配置相关端点已废弃——前端已移除用户自定义 LLM 功能，
# 系统统一使用 config.yaml 中的全局配置。
# 保留 /tested-models 作为兼容接口（返回空列表）。


@router.get("/tested-models")
async def get_tested_models(current_user: User = Depends(get_current_active_user)):
    """获取已通过连接测试的模型列表（已废弃，返回空列表）"""
    return {"models": []}


@router.post("/tested-models")
async def save_tested_model(current_user: User = Depends(get_current_active_user)):
    """保存测试成功的模型配置（已废弃，无操作）"""
    return {"models": []}


@router.delete("/tested-models/{provider_name:path}")
async def remove_tested_model(current_user: User = Depends(get_current_active_user)):
    """从已测试列表中移除指定模型（已废弃，无操作）"""
    return {"models": []}
