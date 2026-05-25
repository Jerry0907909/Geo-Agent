"""API 服务启动入口"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True, # 修改代码自动重启服务器
    )