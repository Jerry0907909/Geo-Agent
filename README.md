# 🗺️ Geo-Agent

> AI-powered geological literature Q&A system with RAG + Deep Search

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.124-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18.2-61DAFB?style=flat-square&logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/LangChain-0.3-1C3C3C?style=flat-square&logo=langchain&logoColor=white" alt="LangChain">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
</p>

<p align="center">
  <b>English</b> &nbsp;|&nbsp; <a href="#chinese">中文</a>
</p>

---

## ✨ Features

- **🤖 Intelligent Chat** — Multi-turn LLM conversation with SSE streaming and real-time Markdown rendering
- **📚 Knowledge Base RAG** — Hybrid retrieval (vector + BM25) with reranker re-ranking and per-user KB isolation
- **🔍 Deep Search** — Perplexity-style pipeline: query planning → multi-query execution → content extraction → embedding recall → re-ranking → context compression → citation tracing
- **🖼️ Multimodal Analysis** — Image upload + PDF image extraction with Vision model analysis
- **👤 User System** — JWT auth, email verification, password management
- **🌐 i18n** — Chinese/English dynamic switching via Zustand, lazy-loaded locale bundles
- **🌙 Dark Mode** — CSS variable-driven, instant global toggle

---

## 🏗️ Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11+ · FastAPI · LangChain · ChromaDB · SQLAlchemy · MySQL · Redis · httpx · PyMuPDF |
| **Frontend** | React 18 · TypeScript · Vite · TailwindCSS · Zustand · Framer Motion · react-markdown |
| **AI / Search** | SiliconFlow API · Tavily Search API · BAAI/bge-reranker-v2-m3 · trafilatura |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ · Node.js 18+ · MySQL 8.0+ · Redis 6.0+ (optional)

### Backend

```bash
# Create conda env and install dependencies
conda create -n RAG python=3.11 -y && conda activate RAG
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database credentials

# Initialize database and start server
python scripts/init_database.py
python main.py                    # → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                       # → http://localhost:5173
```

### Required Config

| Variable | Description |
|----------|------------|
| `API_KEY` | SiliconFlow API key (LLM + Embedding + Rerank) |
| `TAVILY_API_KEY` | Tavily search API key (required for web search) |
| `MYSQL_HOST` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` | MySQL connection |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | QQ SMTP (email verification) |

<details>
<summary>Optional Config</summary>

| Variable | Description |
|----------|------------|
| `LLM_ENABLE_THINKING` | Set `false` to disable DeepSeek thinking mode |
| `REDIS_HOST` | Redis cache (falls back to in-memory if empty) |

</details>

---

## 📁 Project Structure

```
Geo-Agent/
├── src/                            # Backend
│   ├── api/                        # FastAPI routes
│   │   ├── chat_routes.py          # Chat SSE streaming endpoint
│   │   ├── auth_routes.py          # Auth (register/login/verification)
│   │   ├── routes.py               # Document management + RAG
│   │   ├── settings_routes.py      # LLM config + presets
│   │   └── search_routes.py        # Deep search endpoint
│   ├── search/                     # Deep search module (Perplexity-style)
│   │   ├── planner.py              # LLM query decomposition
│   │   ├── tavily_engine.py        # Native httpx async search
│   │   ├── extractor.py            # trafilatura content extraction
│   │   ├── chunker.py              # Chinese-aware text chunking
│   │   ├── retriever.py            # Embedding similarity recall
│   │   ├── reranker.py             # SiliconFlow rerank API
│   │   ├── compressor.py           # Token budget compression
│   │   ├── citation.py             # [1][2] citation tracing
│   │   └── pipeline.py             # Full async pipeline orchestration
│   ├── rag/                        # RAG module
│   │   ├── retriever.py            # Hybrid retrieval (MultiQuery optional)
│   │   ├── reranker.py             # Reranker provider
│   │   └── chain.py                # LCEL generation chain
│   ├── core/                       # LLM / Embedding providers
│   ├── database/                   # ChromaDB + MySQL management
│   ├── tools/                      # Web search tools
│   ├── auth/                       # JWT authentication
│   └── utils/                      # Config, URL normalization, email
├── frontend/                       # React frontend
│   └── src/
│       ├── pages/                  # ChatPage / DocumentsPage / Login / Register
│       ├── components/             # Layout / StreamingMessage / ThinkingWave
│       ├── store/                  # Zustand stores (auth, chat, theme)
│       ├── i18n/                   # i18n (Zustand + lazy loading)
│       └── services/               # API client layer
├── tests/                          # pytest test suite
├── data/                           # Document images and static data
├── scripts/                        # init_database, import_documents
├── config.yaml                     # Global configuration
├── requirements.txt
├── LICENSE                         # MIT License
└── main.py                         # Application entry point
```

---

## 📡 API Overview

| Category | Endpoint | Description |
|----------|----------|-------------|
| Auth | `POST /api/auth/register` | Register with email verification |
| Auth | `POST /api/auth/login` | Login (password or verification code) |
| Auth | `POST /api/auth/send-verification-code` | Send verification email |
| Chat | `POST /api/chat/stream` | SSE streaming conversation |
| Deep Search | `POST /api/search/deep` | Deep search (plan → retrieve → rerank → generate) |
| Documents | `POST /api/documents/upload-file` | Upload document (PDF/Word/MD/TXT) |
| Documents | `POST /api/documents/upload-batch` | Batch upload |
| Documents | `GET /api/documents/list` | Document list (user-isolated) |
| Settings | `GET/PUT /api/settings/llm-config` | LLM configuration |
| Settings | `POST /api/settings/llm-config/test` | Connection test |

> Full Swagger docs available at `http://localhost:8000/docs` after starting the backend.

---

## 🧑‍💻 Development

```bash
# Backend
python main.py                         # Dev server at :8000
PYTHONPATH=. pytest tests/ -q          # Run tests
black . && flake8 .                    # Format + Lint

# Frontend
cd frontend && npm run dev             # Dev server at :5173
cd frontend && npx tsc --noEmit        # TypeScript type-check
cd frontend && npm run build           # Production build
```

---

## 🧠 Architecture Decisions

- **Provider Pattern** — `create_*()` factory functions read from `config.yaml` + `.env`; override via `user_llm_config` param for per-user LLM settings
- **User KB Isolation** — ChromaDB collection naming: `user_{id}_{name}`; all queries filter by `user_id`
- **Reranker** — Prefers SiliconFlow `/v1/rerank` API (zero local GPU); fallback to local CrossEncoder
- **i18n** — Zustand store with dynamic `import()` lazy loading; type-safe `TranslationDict`; components reactively subscribe to `language` state
- **Streaming** — ChatPage uses RAF-batched SSE events → `StreamingMessage` for real-time Markdown rendering
- **Web Search** — Tavily dual-pass: Chinese-preferred domains → full internet; smart time-range detection; recency boosting

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues and pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center" id="chinese">
  <sub>Built with ❤️ for geological literature research</sub>
</p>