# Repository Guidelines

## Project Structure & Module Organization
`src/` contains the backend: `api/` for FastAPI routes, `agent/` for runtime and tool orchestration, `rag/` for retrieval pipelines, `core/` for providers and prompt plumbing, `database/` for MySQL/Chroma access, and `utils/` for config and parsers. `frontend/src/` contains the React app, with `components/`, `pages/`, `services/`, `store/`, and `lib/`. Operational scripts live in `scripts/`, long-form specs in `docs/`, and local vector/document data in `data/`. Treat `frontend/dist/`, `frontend/node_modules/`, `__pycache__/`, and `data/chroma_db/` as generated artifacts.

## Build, Test, and Development Commands
Backend setup:
`python -m venv venv && source venv/bin/activate`
`pip install -r requirements.txt`

Run the API locally:
`python main.py`
or
`uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`

Frontend setup and dev server:
`cd frontend && npm install`
`npm run dev`

Frontend production build:
`cd frontend && npm run build`

Useful maintenance scripts:
`python scripts/init_database.py`
`python scripts/import_documents.py`

## Coding Style & Naming Conventions
Python follows 4-space indentation, `snake_case` for functions/modules, and type hints on shared interfaces. Format with `black` and lint with `flake8` before review. Frontend code uses TypeScript, React function components, `PascalCase` for components/pages, and `camelCase` for hooks, stores, and helpers. Keep changes within existing module boundaries; prefer extending current services and stores over adding parallel abstractions.

## Testing Guidelines
Automated coverage is still light in this snapshot. Use `pytest` for backend tests and place new tests under a dedicated `tests/` tree with names like `test_auth_routes.py`. Keep script-level checks such as `scripts/test_delete_document.py` for smoke workflows only. For frontend changes, at minimum run `npm run build` and verify the affected flow against the local API.

## Commit & Pull Request Guidelines
This workspace snapshot does not include `.git`, so no local history is available to infer conventions. Use short, imperative commit subjects such as `Add agent event validation` or `Fix chat SSE parser`. PRs should describe scope, list config or schema changes, link the relevant issue, and include screenshots for UI work. Call out any changes touching `config.yaml`, auth, database initialization, or document-import behavior.

## Configuration & Data Notes
Configuration is loaded from `config.yaml` with optional `.env` overrides. Do not commit secrets, exported databases, or personal document payloads from `data/document_images/`. When editing agent or tool logic, validate behavior against the documented contracts in `docs/agent/` instead of inventing new request or event shapes.
