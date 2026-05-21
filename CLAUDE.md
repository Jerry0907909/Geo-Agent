# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Geo-Agent is a RAG-based geological literature Q&A system. Backend: FastAPI + LangChain. Frontend: React + TypeScript + Vite + TailwindCSS + Zustand.

## Commands

### Backend

```bash
python main.py                          # Start dev server (port 8000, auto-reload)
python scripts/init_database.py         # Initialize MySQL tables
python scripts/import_documents.py --dir /path/to/docs  # Batch import documents
pytest tests/                           # Run all tests
black . && flake8 .                     # Format + lint
```

### Frontend

```bash
cd frontend && npm run dev              # Start dev server (port 5173)
cd frontend && npm run build            # Production build
cd frontend && npm run lint             # ESLint
```

### API docs

Start the backend, then visit `http://localhost:8000/docs` (Swagger) or `/redoc`.

## Architecture

### Configuration flow

`config.yaml` uses `${ENV_VAR}` placeholders. `.env` provides values. `src/utils/config.py:Config` loads both, substitutes env vars, and exposes typed accessors (`get_llm_config()`, `get_rag_config()`, etc.). The config is a singleton accessed via `get_config()`.

### Provider pattern

`create_llm_provider()`, `create_embedding_provider()`, `create_chroma_manager()`, `create_rag_chain()`, `create_rag_retriever()` — each reads global config and returns a configured instance. LLM and embedding providers wrap LangChain's `ChatOpenAI`/`OpenAIEmbeddings` targeting OpenAI-compatible APIs (SiliconFlow by default). `src/core/http_client_factory.py` creates custom HTTP clients with optional proxy support.

### RAG pipeline

1. **Retrieval** (`src/rag/retriever.py`): `RAGRetriever.retrieve()` uses MultiQuery (LLM generates query variants) → searches all ChromaDB collections → deduplicates by content hash + per-source limit. Wraps `ChromaManager.similarity_search()`.
2. **Hybrid search** (`src/rag/hybrid_retriever.py`): Vector + BM25 (with jieba tokenization for Chinese), fused via Reciprocal Rank Fusion.
3. **Reranker** (`src/rag/reranker.py`): Cross-encoder (`BAAI/bge-reranker-v2-m3`) re-ranks candidates. `RerankerRetriever` wraps a base retriever with reranking.
4. **Generation** (`src/rag/chain.py`): LCEL chain (`prompt | llm | StrOutputParser`) with `{context}` and `{question}` placeholders.

### ChromaDB layer (`src/database/chroma_manager.py`)

`ChromaManager` wraps LangChain's `Chroma` with a shared `PersistentClient` singleton. Supports:
- `add_documents()` with batch processing (32 docs/batch to respect embedding API limits)
- `similarity_search()` returning cosine similarity scores
- `similarity_search_with_diversity()` using MMR
- `search_all_collections()` for cross-collection queries
- `delete_by_filter()` and `reset_collection()`

### Chat API (`src/api/chat_routes.py`)

`POST /api/chat/stream` is the primary endpoint. SSE streaming with typed events: `info`, `status`, `content`, `sources`, `error`, `done`. Supports three modes:
- **chat**: Plain LLM conversation with optional web search and image analysis. Uses `compact_chat_history()` to keep context within token budget (6 messages, 4000 chars total, 1200 char/item).
- **rag**: Retrieves documents, streams LLM answer, includes document images when available (falls back to vision model for image-rich results).
- Vision mode automatically triggers when `image_base64` is present or when RAG finds document images.

### Data models (`src/database/models.py`)

SQLAlchemy models: `User`, `Conversation`, `Message` (with JSON `message_metadata`), `UserPreference`, `SearchHistory`, `DocumentAccess`, `CustomAgent` (user-defined AI assistants with custom prompts and dedicated knowledge bases). Conversations use soft delete (`is_active=False`).

### Auth (`src/auth/`)

JWT-based (access + refresh tokens). `deps.py` provides FastAPI dependency callables: `get_current_user`, `get_current_active_user`, `get_optional_user` (allows unauthenticated access), `get_superuser`.

### Frontend state (`frontend/src/store/`)

Zustand stores: `useAuthStore` (user, token), `useChatStore` (conversations, messages, streaming), `useThemeStore` (light/dark), `useRouteStore`.

### `frontend-distill/`

A separate Node.js tool for distilling/processing a frontend UI from another project. This is an independent utility, not part of the main application.

## Key conventions

- All `create_*` factory functions read from the global config singleton. To change behavior, modify `config.yaml` or `.env` — not the factory functions.
- The `SiliconFlow*` class names are aliases kept for backward compatibility; the actual implementations are `LangChainLLMProvider` and `LangChainEmbeddingProvider`.
- Messages persist to MySQL inside the streaming generator using a fresh `SessionLocal()` session to avoid cross-request session conflicts.
- `frontend/src/services/api.ts` is the single HTTP client layer — all API calls go through it.
