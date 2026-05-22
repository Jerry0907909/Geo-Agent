# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Geo-Agent is a RAG-based AI Q&A system. Backend: FastAPI + LangChain. Frontend: React + TypeScript + Vite + TailwindCSS + Zustand. Conda env: `conda activate RAG`.

## Commands

### Backend

```bash
python main.py                          # Start dev server (port 8000, auto-reload)
python scripts/init_database.py         # Initialize MySQL tables
python scripts/import_documents.py --dir /path/to/docs  # Batch import documents
PYTHONPATH=. pytest tests/ -q           # Run all tests
black . && flake8 .                     # Format + lint
```

### Frontend

```bash
cd frontend && npm run dev              # Start dev server (port 5173)
cd frontend && npm run build            # Production build
cd frontend && npx tsc --noEmit        # TypeScript type-check
```

### API docs

Start the backend, then visit `http://localhost:8000/docs` (Swagger) or `/redoc`.

## Architecture

### Configuration flow

`config.yaml` uses `${ENV_VAR}` placeholders. `.env` provides values. `src/utils/config.py:Config` loads both, substitutes env vars, and exposes typed accessors. Singleton via `get_config()`. New sections added: `web_search` (Tavily), `smtp` (QQ mail), reranker API config.

### Provider pattern

`create_llm_provider()`, `create_embedding_provider()`, `create_chroma_manager()`, `create_rag_chain()` — each reads global config and returns a configured instance. LLM/embedding providers wrap LangChain's `ChatOpenAI`/`OpenAIEmbeddings` targeting OpenAI-compatible APIs (SiliconFlow by default). `tiktoken_enabled=False` on embeddings to avoid network-dependent encoding downloads.

### User LLM config (`src/utils/user_llm.py`)

Users can configure their own LLM provider (base_url, api_key, model_name) via system settings. `resolve_user_llm_config(preference)` provides unified resolution: `llm_config` (priority) → `tested_models` (fallback) → `None`. `create_llm_provider` accepts `user_llm_config` param to override config.yaml. User configs stored in `UserPreference.settings` JSON column.

### RAG pipeline

1. **Retrieval** (`src/rag/retriever.py`): `RAGRetriever.retrieve()` with MultiQuery disabled by default to avoid extra LLM calls. ChromaDB searches filtered by `user_id` for user-level KB isolation.
2. **Reranker** (`src/rag/reranker.py`): `SiliconFlowReranker` calls `POST /v1/rerank` API (BAAI/bge-reranker-v2-m3) — zero local GPU. Falls back to local CrossEncoder only when API key unavailable. Config: `rag.reranker_api: true` in config.yaml.
3. **Generation** (`src/rag/chain.py`): LCEL chain (`prompt | llm | StrOutputParser`).

### ChromaDB layer (`src/database/chroma_manager.py`)

Per-user collections named `user_{id}_{collection_name}`. `_display_collection_name()` recursively strips all `user_N_` prefix layers for frontend display. `_user_collection()` strips old prefixes before re-adding current user's to prevent double-prefixing.

### Chat API (`src/api/chat_routes.py`)

`POST /api/chat/stream` is the primary endpoint. SSE streaming with typed events: `info`, `status`, `content`, `sources`, `error`, `done`. WEB_SEARCH in chat mode uses 5 results max to avoid content filter triggers. RAG mode optionally uses `SearchOrchestrator` for parallel KB+web retrieval. Document images loaded from `data/document_images/{file}.json` and included in sources events for frontend display.

### Deep Search module (`src/search/`)

Independent module for Perplexity-style deep search: `planner.py` (LLM query decomposition) → `tavily_engine.py` (native httpx async) → `extractor.py` (trafilatura) → `chunker.py` (Chinese-aware split) → `retriever.py` (cosine embedding) → `reranker.py` (SiliconFlow API) → `compressor.py` (token budget) → `citation.py` ([1][2] refs) → `pipeline.py` (async orchestrator). REST endpoint: `POST /api/search/deep`.

### Web Search (`src/tools/web_search.py`)

Dual-pass strategy: Round 1 on Chinese preferred domains (xinhuanet, people.com.cn, baidu, zhihu, etc.) → if <5 quality results, Round 2 on full internet. Smart `time_range` detection from query keywords (今天/最新 → week, 进展/趋势 → month). Recency boost: this year +0.12, 5+ years -0.15 penalty. Chinese content filter via `_has_chinese()`. Tavily called via native `httpx.Client` (not tavily-python SDK) to avoid SSL issues.

### Data models (`src/database/models.py`)

SQLAlchemy models: `User`, `Conversation`, `Message` (with JSON `message_metadata`), `UserPreference` (stores LLM config and tested_models in JSON `settings`), `SearchHistory`, `DocumentAccess`, `CustomAgent`.

### Auth (`src/auth/`)

JWT-based access + refresh tokens. `deps.py` provides `get_current_user`, `get_current_active_user`, `get_optional_user`, `get_superuser`. Email verification via SMTP (QQ mail), codes stored in Redis with 5-min TTL (fallback to in-memory dict).

### Frontend state (`frontend/src/store/`)

Zustand stores: `useAuthStore`, `useChatStore` (conversations, messages, streaming with RAF-based content batching), `useThemeStore`.

### i18n (`frontend/src/i18n/`)

Zustand-based language switching (zh-CN / en). Lazy-loaded locale modules via dynamic `import()`. Type-safe `TranslationDict` interface. `useI18nStore` hook with `t()` and `fmtDate()`/`fmtNumber()` (Intl APIs). Language persisted to localStorage, auto-detected from `navigator.language`. Components subscribe to `language` state for reactive re-render.

### Streaming output (`frontend/src/components/StreamingMessage.tsx`)

Real-time Markdown rendering during SSE streaming via `react-markdown`. AI-style breathing cursor animation (CSS keyframes, GPU composited). Content managed by RAF-based frame batching in ChatPage — chunks merge to ~60fps then `setStreamingContent()` triggers single-pass Markdown render.

## Key conventions

- All `create_*` factory functions read from global config singleton. Modify `config.yaml` or `.env` to change behavior — not the factories.
- The `SiliconFlow*` class names are legacy aliases for `LangChainLLMProvider` / `LangChainEmbeddingProvider`.
- Messages persist to MySQL inside the streaming generator using a fresh `SessionLocal()` to avoid cross-request conflicts.
- `frontend/src/services/api.ts` is the single HTTP client layer.
- ChromaDB collection names use `user_{id}_{collection}` pattern for user isolation. Always use `_display_collection_name()` for frontend and `_user_collection()` for internal ops.
- Embedding provider init must pass `tiktoken_enabled=False` to avoid network-dependent encoding downloads.
