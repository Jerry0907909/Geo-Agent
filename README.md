# Geo-Agent - 地质文献智能问答系统

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.124.0-009688.svg)
![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg)
![LangChain](https://img.shields.io/badge/LangChain-1.1.3-00A67E.svg)

基于 RAG（检索增强生成）技术的地质文献智能问答系统，支持文献检索、智能对话、多模态分析等功能。

[功能特性](#功能特性) • [快速开始](#快速开始) • [系统架构](#系统架构) • [API 文档](#api-文档) • [部署指南](#部署指南)

</div>

---

## 📋 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 文档](#api-文档)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [部署指南](#部署指南)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## ✨ 功能特性

### 核心功能

- **🤖 智能对话**
  - 支持普通对话模式，基于大语言模型进行自然语言交互
  - 上下文记忆，支持多轮对话
  - 流式输出，实时显示 AI 回复

- **📚 文献检索（RAG）**
  - 基于向量数据库的语义检索
  - 混合检索（向量检索 + BM25 关键词检索）
  - Reranker 重排序，提升检索精度
  - 支持多种文档格式（PDF、Word、TXT、Markdown）
  - 文档分块与向量化存储

- **🌐 网络搜索增强**
  - 集成网络搜索功能，获取实时信息
  - 搜索结果与知识库结合，提供更全面的答案

- **🖼️ 多模态分析**
  - 支持图像上传与分析
  - 图文结合的智能问答
  - PDF 文档图片提取与分析

- **👤 用户系统**
  - 用户注册、登录、认证
  - JWT Token 安全认证
  - 会话管理与历史记录
  - 用户偏好设置

- **📊 文献管理**
  - 文档上传与管理
  - 文档内容查看与编辑
  - 文档删除与批量操作
  - 文件类型统计与分类

### 高级特性

- **🔄 流式响应**：实时流式输出 AI 回复，提升用户体验
- **💾 会话持久化**：自动保存对话历史，支持会话恢复
- **🎨 主题切换**：支持亮色/暗色主题
- **📱 响应式设计**：适配桌面端和移动端
- **🔍 高级检索**：可调节检索参数（top_k、相关度阈值等）
- **📈 消息反馈**：支持对 AI 回复进行点赞/点踩反馈

---

## 🛠️ 技术栈

### 后端技术

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 编程语言 |
| FastAPI | 0.124.0 | Web 框架 |
| LangChain | 1.1.3 | LLM 应用框架 |
| ChromaDB | 1.3.5 | 向量数据库 |
| SQLAlchemy | 2.0.44 | ORM 框架 |
| MySQL | 8.0+ | 关系型数据库 |
| PyMuPDF | 1.25.1 | PDF 解析 |
| Sentence-Transformers | 2.7.0 | 文本嵌入与重排序 |

### 前端技术

| 技术 | 版本 | 说明 |
|------|------|------|
| React | 18.2.0 | UI 框架 |
| TypeScript | 5.3.3 | 类型安全 |
| Vite | 5.1.4 | 构建工具 |
| TailwindCSS | 3.4.1 | CSS 框架 |
| Zustand | 4.5.1 | 状态管理 |
| React Router | 6.22.3 | 路由管理 |
| Framer Motion | 12.23.26 | 动画库 |
| Axios | 1.6.7 | HTTP 客户端 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端层 (React)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 智能问答 │  │ 文献管理 │  │ 用户中心 │  │ 主题设置 │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                      API 层 (FastAPI)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 认证路由 │  │ 聊天路由 │  │ 文档路由 │  │ RAG路由  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                       业务逻辑层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ LLM提供商│  │ RAG链    │  │ 文本分割 │  │ 文档加载 │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                        数据层                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  MySQL   │  │ ChromaDB │  │  Redis   │  │ 文件存储 │   │
│  │(用户数据)│  │(向量数据)│  │  (缓存)  │  │ (文档)   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

1. **LLM 提供商**：封装大语言模型 API 调用
2. **Embedding 提供商**：文本向量化
3. **RAG 链**：检索增强生成流程
4. **ChromaDB 管理器**：向量数据库操作
5. **文档加载器**：多格式文档解析
6. **文本分割器**：智能文本分块

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Redis 6.0+（可选）

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/geo-agent.git
cd geo-agent
```

### 2. 后端设置

#### 2.1 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

#### 2.2 安装依赖

```bash
pip install -r requirements.txt
```

#### 2.3 配置环境变量

创建 `.env` 文件：

```bash
# API 配置
API_KEY=your_api_key_here
EMBEDDING_API_ENDPOINT=https://api.siliconflow.cn/v1/embeddings
EMBEDDING_MODEL_NAME=BAAI/bge-large-zh-v1.5
LLM_API_ENDPOINT=https://api.siliconflow.cn/v1/chat/completions
LLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct

# 数据库配置
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=geo_agent

# JWT 配置
JWT_SECRET_KEY=your_secret_key_here

# ChromaDB 配置
CHROMA_PERSIST_DIR=./data/chroma_db
CHROMA_COLLECTION_NAME=geology_documents

# 服务器配置
SERVER_HOST=0.0.0.0
```

#### 2.4 初始化数据库

```bash
python scripts/init_database.py
```

#### 2.5 启动后端服务

```bash
python main.py
```

后端服务将在 `http://localhost:8000` 启动。

### 3. 前端设置

#### 3.1 安装依赖

```bash
cd frontend
npm install
```

#### 3.2 启动开发服务器

```bash
npm run dev
```

前端服务将在 `http://localhost:5173` 启动。

### 4. 访问应用

打开浏览器访问 `http://localhost:5173`

默认管理员账号：
- 用户名：`admin`
- 密码：`admin123`

---

## ⚙️ 配置说明

### config.yaml 配置文件

系统配置文件位于项目根目录的 `config.yaml`，主要配置项包括：

#### 模型配置

```yaml
embedding:
  provider: "siliconflow"
  model_name: "BAAI/bge-large-zh-v1.5"
  embedding_dim: 1024

llm:
  provider: "siliconflow"
  model_name: "Qwen/Qwen2.5-7B-Instruct"
  temperature: 0.7
  max_tokens: 2048
```

#### RAG 配置

```yaml
rag:
  top_k: 5
  chunk_size: 1024
  chunk_overlap: 128
  retrieval_mode: "hybrid"  # vector_only, bm25_only, hybrid
  use_reranker: true
  reranker_model: "BAAI/bge-reranker-v2-m3"
```

#### 数据库配置

```yaml
database:
  mysql_host: "${MYSQL_HOST}"
  mysql_port: 3306
  mysql_user: "${MYSQL_USER}"
  mysql_password: "${MYSQL_PASSWORD}"
  mysql_database: "${MYSQL_DATABASE}"
```

更多配置项请参考 `config.yaml` 文件中的注释。

---

## 📖 API 文档

### 在线文档

启动后端服务后，访问以下地址查看 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 主要 API 端点

#### 认证相关

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息
- `POST /api/auth/change-password` - 修改密码

#### 聊天相关

- `POST /api/chat/send` - 发送消息（非流式）
- `POST /api/chat/stream` - 发送消息（流式）
- `GET /api/chat/conversations` - 获取会话列表
- `POST /api/chat/conversations` - 创建新会话
- `DELETE /api/chat/conversations/{id}` - 删除会话

#### 文档管理

- `POST /api/documents/upload-file` - 上传文档
- `GET /api/documents/list` - 获取文档列表
- `GET /api/documents/content/{source}` - 获取文档内容
- `DELETE /api/documents/by-source/{source}` - 删除文档

#### RAG 检索

- `POST /api/rag/query` - RAG 检索查询

---

## 📁 项目结构

```
geo-agent/
├── frontend/                 # 前端项目
│   ├── src/
│   │   ├── components/      # React 组件
│   │   ├── pages/           # 页面组件
│   │   ├── services/        # API 服务
│   │   ├── store/           # 状态管理
│   │   └── lib/             # 工具函数
│   ├── public/              # 静态资源
│   └── package.json
│
├── src/                     # 后端源码
│   ├── api/                 # API 路由
│   │   ├── main.py         # FastAPI 应用入口
│   │   ├── routes.py       # 文档管理路由
│   │   ├── chat_routes.py  # 聊天路由
│   │   └── auth_routes.py  # 认证路由
│   │
│   ├── auth/                # 认证模块
│   │   ├── deps.py         # 依赖注入
│   │   └── jwt.py          # JWT 处理
│   │
│   ├── core/                # 核心模块
│   │   ├── llm_provider.py      # LLM 提供商
│   │   ├── embedding_provider.py # Embedding 提供商
│   │   ├── text_splitter.py     # 文本分割
│   │   ├── document_loader.py   # 文档加载
│   │   └── prompts.py           # 提示词模板
│   │
│   ├── database/            # 数据库模块
│   │   ├── models.py       # 数据模型
│   │   ├── chroma_manager.py    # ChromaDB 管理
│   │   └── mysql_manager.py     # MySQL 管理
│   │
│   ├── rag/                 # RAG 模块
│   │   ├── chain.py        # RAG 链
│   │   ├── retriever.py    # 检索器
│   │   └── web_enhanced_retriever.py  # 网络增强检索
│   │
│   ├── tools/               # 工具模块
│   │   └── web_search.py   # 网络搜索
│   │
│   └── utils/               # 工具函数
│       ├── config.py       # 配置管理
│       └── pdf_parser.py   # PDF 解析
│
├── scripts/                 # 脚本文件
│   ├── init_database.py    # 数据库初始化
│   └── import_documents.py # 文档导入
│
├── data/                    # 数据目录
│   ├── chroma_db/          # 向量数据库
│   └── document_images/    # 文档图片
│
├── tests/                   # 测试文件
├── docs/                    # 文档
├── config.yaml             # 配置文件
├── requirements.txt        # Python 依赖
├── main.py                 # 启动入口
└── README.md               # 项目说明
```

---

## 💻 开发指南

### 后端开发

#### 添加新的 API 端点

1. 在 `src/api/` 目录下创建或编辑路由文件
2. 定义请求和响应模型（使用 Pydantic）
3. 实现路由处理函数
4. 在 `src/api/main.py` 中注册路由

示例：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/api/example", tags=["示例"])

class ExampleRequest(BaseModel):
    message: str

class ExampleResponse(BaseModel):
    result: str

@router.post("/test", response_model=ExampleResponse)
async def test_endpoint(request: ExampleRequest):
    return ExampleResponse(result=f"收到消息: {request.message}")
```

#### 添加新的数据模型

在 `src/database/models.py` 中定义 SQLAlchemy 模型：

```python
from sqlalchemy import Column, Integer, String
from src.database.database import Base

class NewModel(Base):
    __tablename__ = "new_table"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
```

### 前端开发

#### 添加新页面

1. 在 `frontend/src/pages/` 创建页面组件
2. 在 `frontend/src/App.tsx` 中添加路由
3. 在 `frontend/src/components/Layout.tsx` 中添加导航（如需要）

#### 调用后端 API

使用 `frontend/src/services/api.ts` 中的服务：

```typescript
import { chatService } from '@/services/api'

// 发送消息
const response = await chatService.send({
  message: "你好",
  mode: "chat"
})
```

### 代码规范

#### 后端

- 使用 Black 格式化代码：`black .`
- 使用 Flake8 检查代码：`flake8 .`
- 类型注解：使用 Python 类型提示

#### 前端

- 使用 ESLint 检查代码：`npm run lint`
- 使用 TypeScript 严格模式
- 组件命名：PascalCase
- 函数命名：camelCase

---

## 🚢 部署指南

### Docker 部署（推荐）

#### 1. 构建镜像

```bash
# 构建后端镜像
docker build -t geo-agent-backend .

# 构建前端镜像
cd frontend
docker build -t geo-agent-frontend .
```

#### 2. 使用 Docker Compose

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: your_password
      MYSQL_DATABASE: geo_agent
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

  redis:
    image: redis:6.0
    ports:
      - "6379:6379"

  backend:
    image: geo-agent-backend
    depends_on:
      - mysql
      - redis
    environment:
      - MYSQL_HOST=mysql
      - REDIS_HOST=redis
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data

  frontend:
    image: geo-agent-frontend
    depends_on:
      - backend
    ports:
      - "80:80"

volumes:
  mysql_data:
```

启动服务：

```bash
docker-compose up -d
```

### 传统部署

#### 后端部署

1. 安装 Python 依赖
2. 配置环境变量
3. 使用 Gunicorn 或 Uvicorn 启动：

```bash
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

#### 前端部署

1. 构建生产版本：

```bash
cd frontend
npm run build
```

2. 使用 Nginx 部署：

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## ❓ 常见问题

### Q1: 如何更换 LLM 模型？

修改 `.env` 文件中的 `LLM_MODEL_NAME` 和 `LLM_API_ENDPOINT`。

### Q2: 如何导入已有文档？

使用导入脚本：

```bash
python scripts/import_documents.py --dir /path/to/documents
```

### Q3: ChromaDB 数据存储在哪里？

默认存储在 `./data/chroma_db/` 目录，可在 `.env` 中修改 `CHROMA_PERSIST_DIR`。

### Q4: 如何启用网络搜索功能？

在聊天界面中，点击"网络搜索"开关即可启用。

### Q5: 支持哪些文档格式？

目前支持：PDF、Word（.docx）、TXT、Markdown（.md）。

### Q6: 如何调整检索精度？

在 RAG 模式下，可以调整以下参数：
- `top_k`：检索文档数量
- `min_relevance_score`：最小相关度阈值
- 在 `config.yaml` 中启用 Reranker

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

### 贡献类型

- 🐛 Bug 修复
- ✨ 新功能
- 📝 文档改进
- 🎨 UI/UX 优化
- ⚡ 性能优化
- ✅ 测试用例

### 代码审查

所有 PR 都需要经过代码审查才能合并。请确保：

- 代码符合项目规范
- 添加必要的测试
- 更新相关文档
- 通过所有 CI 检查

---

## 🙏 致谢

感谢以下开源项目：

- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [FastAPI](https://github.com/tiangolo/fastapi) - 现代 Web 框架
- [React](https://github.com/facebook/react) - UI 框架
- [ChromaDB](https://github.com/chroma-core/chroma) - 向量数据库
- [TailwindCSS](https://github.com/tailwindlabs/tailwindcss) - CSS 框架

---

<div align="center">
**⭐ 如果这个项目对你有帮助，请给我们一个 Star！⭐**

</div>
