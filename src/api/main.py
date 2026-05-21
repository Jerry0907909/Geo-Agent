"""FastAPI 主应用

地质文献智能体 Web API 服务入口。
"""

from contextlib import asynccontextmanager
import logging

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.api.auth_routes import router as auth_router
from src.api.chat_routes import router as chat_router
from src.api.settings_routes import router as settings_router
from src.utils.config import get_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理
    
    在启动时执行初始化，关闭时执行清理。
    """
    # 启动时
    print("=" * 60)
    print("地质文献智能体 API 服务启动中...")
    print("=" * 60)
    
    # 可以在这里预加载模型、初始化连接池等
    try:
        # 测试配置加载
        config = get_config()
        print("✓ 配置加载成功")
        
        # 初始化MySQL数据库
        try:
            from src.database.mysql_manager import init_database, check_database_connection
            if check_database_connection():
                init_database()
                print("✓ MySQL数据库连接成功")
            else:
                print("⚠ MySQL数据库未配置或连接失败，部分功能将不可用")
        except Exception as db_error:
            print(f"⚠ MySQL数据库初始化失败: {db_error}")
            print("  用户认证和对话记录功能将不可用")
        
        # 测试向量库连接
        from src.database.chroma_manager import create_chroma_manager
        chroma = create_chroma_manager()
        print("✓ 向量库连接成功")
        
        print("=" * 60)
        print("服务启动完成！")
        print("=" * 60)
        print("API 文档: http://localhost:8000/docs")
        print("健康检查: http://localhost:8000/api/health")
        print("用户认证: http://localhost:8000/api/auth/*")
        print("智能对话: http://localhost:8000/api/chat/*")
        print("=" * 60)
    
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        print("请检查配置文件和依赖是否正确安装")
        logger.exception("服务启动失败")
    
    yield
    
    # 关闭时
    print("\n服务关闭中...")
    
    # 关闭数据库连接
    try:
        from src.database.mysql_manager import close_database
        close_database()
        print("✓ 数据库连接已关闭")
    except Exception as e:
        print(f"⚠ 关闭数据库连接时出错: {e}")


# 创建 FastAPI 应用
app = FastAPI(
    title="地质文献智能体 API",
    description="基于 RAG 和 Agent 的地质知识库检索与问答系统",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 配置 CORS
config = get_config()
server_cfg = config.get_server_config()

app.add_middleware(
    CORSMiddleware,
    allow_origins=server_cfg.get("cors_origins", ["*"]),
    allow_credentials=server_cfg.get("cors_credentials", True),
    allow_methods=server_cfg.get("cors_methods", ["*"]),
    allow_headers=server_cfg.get("cors_headers", ["*"]),
)


# 处理 Pydantic 校验错误 (422)，返回前端可读的字符串 detail
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "")
        messages.append(f"{field}: {msg}")
    detail = "；".join(messages)
    logger.warning("请求校验失败: %s", detail)
    return JSONResponse(
        status_code=422,
        content={"detail": detail},
    )


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "服务器内部错误",
            "detail": str(exc),
        },
    )


# 注册路由
app.include_router(router, prefix="/api", tags=["API"])
app.include_router(auth_router, prefix="/api", tags=["认证"])
app.include_router(chat_router, prefix="/api", tags=["聊天"])
app.include_router(settings_router, prefix="/api", tags=["设置"])


# 用于直接运行
if __name__ == "__main__":
    import uvicorn
    
    host = server_cfg.get("host", "0.0.0.0")
    port = int(server_cfg.get("port", 8000))
    debug = server_cfg.get("debug", False)
    workers = int(server_cfg.get("workers", 1))
    
    print(f"\n启动服务: http://{host}:{port}")
    
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=debug,
        workers=workers if not debug else 1,  # debug模式下只用1个worker
    )
