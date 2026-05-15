# Repository Guidelines

## Project Structure & Module Organization
`src/` holds the backend. Use `api/` for FastAPI routes, `agent/` for runtime, planner, executor, and event flow, `rag/` for retrieval pipelines, `core/` for LLM and document plumbing, `database/` for MySQL/Chroma access, and `utils/` for config and parsing helpers. The React frontend lives in `frontend/src/` with `components/`, `pages/`, `services/`, `store/`, and `lib/`. Operational scripts are in `scripts/`; runtime data and vector stores live under `data/`. Treat `__pycache__/`, `frontend/dist/`, and local database artifacts as generated output.

## Build, Test, and Development Commands
Backend setup:
`python -m venv venv && source venv/bin/activate`
`pip install -r requirements.txt`

Run the API:
`python main.py`
or
`uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`

Frontend setup:
`cd frontend && npm install`

Frontend dev/build:
`npm run dev` starts Vite, `npm run build` runs `tsc` then creates the production bundle, and `npm run preview` serves the built app locally.

Useful maintenance scripts:
`python scripts/init_database.py`
`python scripts/import_documents.py`

## Coding Style & Naming Conventions
Python uses 4-space indentation, `snake_case` for modules and functions, and type hints for shared interfaces. Format with `black` and lint with `flake8` before review. Frontend code uses TypeScript function components, `PascalCase` for components/pages, and `camelCase` for helpers, stores, and service functions. Keep edits inside existing module boundaries; do not introduce parallel abstractions for one-off changes.

## Frontend UI Notes
The current frontend direction is intentionally restrained and should not drift back toward generic dashboard cards. `frontend/src/pages/ChatPage.tsx` is split into two clear interaction styles: normal/RAG chat should read like a lightweight DeepSeek-style answer surface with minimal chrome, while Agent mode should behave more like a Codex workspace with a primary answer column and a collapsible right-side progress panel. In active conversation views, do not reintroduce the top mode-switch bar; mode switching is reserved for the welcome state. System settings in `frontend/src/components/Layout.tsx` should stay aligned with the existing DeepSeek-inspired modal structure rather than being redesigned into a different settings pattern. For document management, prefer calm layout hierarchy over heavy card treatment, and reduce panel chrome before adding new decorative containers.

## Testing Guidelines
Backend tests should use `pytest` under a top-level `tests/` tree with names like `test_agent_routes.py`. Existing script checks such as `scripts/test_delete_document.py` are smoke tests, not a substitute for focused unit coverage. For frontend work, run `cd frontend && npm run build` and verify the affected flow against the local API.

## Commit & Pull Request Guidelines
Recent history is sparse (`Initial commit`, merge from `origin/main`), so keep commit subjects short and imperative, for example `Add agent event validation` or `Fix chat SSE parsing`. PRs should state scope, list config or schema changes, link the issue, and include screenshots for UI work.

## Configuration & Data Notes
Configuration is centered on `config.yaml`; keep secrets out of git and do not commit local document payloads or vector-store data. When changing agent behavior or SSE payloads, align with the contracts already implemented in `src/agent/` and `src/api/` rather than inventing new shapes.
