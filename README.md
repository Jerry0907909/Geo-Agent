# Geo-Agent — AI 地质文献智能问答系统

基于 RAG + Deep Search 技术的 AI 问答系统。支持知识库检索、联网深度搜索、多模态分析、多语言切换。

[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.124.0-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg)](https://react.dev)

---

## 功能特性

- **智能对话** — LLM 多轮对话，SSE 流式输出，实时 Markdown 渲染
- **知识库 RAG** — 向量语义检索 + BM25 关键词混合检索 + Reranker 重排序 + 用户级知识库隔离
- **联网深度搜索** — 查询规划 → 多查询并发 → 正文抽取 → Embedding 召回 → 重排序 → 上下文压缩 → 引用溯源（类 Perplexity）
- **多模态分析** — 图像上传与 PDF 图片提取，Vision 模型多图分析
- **用户系统** — JWT 认证、邮箱验证码注册/登录、密码修改
- **国际化** — 中英双语 UI，Zustand 驱动的动态切换，懒加载语言包
- **暗色模式** — CSS 变量驱动，全局即时切换

---

## 技术栈

**后端**：Python 3.11+ · FastAPI · LangChain · ChromaDB · SQLAlchemy · MySQL · Redis · httpx · PyMuPDF  
**前端**：React 18 · TypeScript · Vite · TailwindCSS · Zustand · Framer Motion · react-markdown  
**AI/搜索**：SiliconFlow API · Tavily Search API · BAAI/bge-reranker-v2-m3 · trafilatura

---

## 快速开始

### 环境要求

- Python 3.11+ · Node.js 18+ · MySQL 8.0+ · Redis 6.0+（可选）

### 1. 后端

```bash
conda create -n RAG python=3.11 && conda activate RAG
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填入 API Key 和数据库配置
python scripts/init_database.py
python main.py          # 启动 http://localhost:8000
```

### 2. 前端

```bash
cd frontend && npm install && npm run dev   # 启动 http://localhost:5173
```

### 3. 配置要点

`.env` 中必须配置：

| 变量 | 说明 |
|------|------|
| `API_KEY` | 硅基流动 API Key（LLM + Embedding + Rerank 共用） |
| `TAVILY_API_KEY` | Tavily 搜索 API Key（联网搜索必需） |
| `MYSQL_HOST/USER/PASSWORD/DATABASE` | MySQL 数据库连接 |
| `SMTP_HOST/USER/PASSWORD` | QQ 邮箱 SMTP（邮箱验证码） |

`.env` 可选配置：

| 变量 | 说明 |
|------|------|
| `LLM_ENABLE_THINKING` | `false` 关闭 DeepSeek 深度思考模式 |
| `REDIS_HOST` | Redis 缓存（留空则仅用内存缓存） |

---

## 项目结构

```
├── src/                         # 后端
│   ├── api/                     # FastAPI 路由
│   │   ├── chat_routes.py       # 聊天 SSE 流式端点
│   │   ├── auth_routes.py       # 认证（注册/登录/验证码）
│   │   ├── routes.py            # 文档管理 + RAG
│   │   ├── settings_routes.py   # LLM 配置 + 预设
│   │   └── search_routes.py     # 深度搜索端点
│   ├── search/                  # 深度搜索模块（类 Perplexity）
│   │   ├── planner.py           # LLM 查询拆解
│   │   ├── tavily_engine.py     # 原生 httpx 异步搜索
│   │   ├── extractor.py         # trafilatura 正文抽取
│   │   ├── chunker.py           # 中文友好文本分块
│   │   ├── retriever.py         # Embedding 相似度召回
│   │   ├── reranker.py          # 硅基流动 Rerank API
│   │   ├── compressor.py        # token budget 压缩
│   │   ├── citation.py          # [1][2] 引用溯源
│   │   └── pipeline.py          # 全异步流水线编排
│   ├── rag/                     # RAG 模块
│   ├── core/                    # LLM/Embedding 提供者
│   ├── database/                # ChromaDB + MySQL 管理
│   ├── tools/                   # Web 搜索工具
│   ├── auth/                    # JWT 认证
│   └── utils/                   # 配置、URL 规范化、邮件
├── frontend/                    # React 前端
│   └── src/
│       ├── pages/               # ChatPage / DocumentsPage / Login / Register
│       ├── components/          # Layout / StreamingMessage / ThinkingWave
│       ├── store/               # Zustand stores
│       ├── i18n/                # 国际化（Zustand + 懒加载）
│       └── services/            # API 客户端
├── tests/                       # pytest 测试
├── config.yaml                  # 全局配置
├── requirements.txt
└── main.py                      # 启动入口
```

---

## API 端点速览

| 类别 | 端点 | 说明 |
|------|------|------|
| 认证 | `POST /api/auth/register` | 邮箱验证码注册 |
| 认证 | `POST /api/auth/login` | 密码/验证码登录 |
| 认证 | `POST /api/auth/send-verification-code` | 发送邮箱验证码 |
| 聊天 | `POST /api/chat/stream` | SSE 流式对话 |
| 深度搜索 | `POST /api/search/deep` | 深度搜索（规划→检索→重排→生成） |
| 文档 | `POST /api/documents/upload-file` | 上传文档（PDF/Word/MD/TXT） |
| 文档 | `POST /api/documents/upload-batch` | 批量上传 |
| 文档 | `GET /api/documents/list` | 文档列表（用户隔离） |
| 设置 | `GET/PUT /api/settings/llm-config` | LLM 配置管理 |
| 设置 | `POST /api/settings/llm-config/test` | 连接测试 |

完整 API 文档：启动后端后访问 `http://localhost:8000/docs`

---

## 开发命令

```bash
# 后端
python main.py                              # 开发服务器 :8000
PYTHONPATH=. pytest tests/ -q               # 运行测试
black . && flake8 .                         # 格式化 + Lint

# 前端
cd frontend && npm run dev                  # 开发服务器 :5173
cd frontend && npx tsc --noEmit             # TypeScript 类型检查
cd frontend && npm run build                # 生产构建
```

---

## 关键架构决策

- **LLM/Embedding 提供者** — `create_*()` 工厂函数从 `config.yaml` + `.env` 读取配置，支持 `user_llm_config` 参数覆盖
- **用户知识库隔离** — ChromaDB 集合名格式 `user_{id}_{name}`，所有查询过滤 `user_id`
- **Reranker** — 优先使用硅基流动 `/v1/rerank` API（零本地 GPU），`rag.reranker_api: true`
- **i18n** — Zustand store + 动态 `import()` 懒加载语言包，类型安全 `TranslationDict`，组件订阅 `language` state
- **流式输出** — ChatPage 使用 RAF 批量化 SSE 事件 → `StreamingMessage` 实时 Markdown 渲染
- **搜索** — Tavily 双轮策略（中文优先域名 → 全互联网）、智能时间窗检测、时效性加权、中文内容过滤
