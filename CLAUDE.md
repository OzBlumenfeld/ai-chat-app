# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@rules/how_to_troubleshoot.md

## Commands

```bash
uv sync                                          # install dependencies
uv run fastapi dev main.py                       # dev server (port 8000)
uv run pytest                                    # all tests
uv run pytest tests/test_query.py::test_name -s  # single test
uv run ruff check . --fix                        # lint + autofix
uv run alembic upgrade head                      # apply DB migrations
uv run alembic revision --autogenerate -m "desc" # generate migration
docker-compose up --build                        # full stack
```

## Architecture

### Request flow

A query enters `POST /query` → `AgentOrchestrationService.query()`, which decides how to answer:

1. **RAG path** — runs `amax_marginal_relevance_search` + `asimilarity_search_with_score` concurrently against the user's pgvector collection. If the best cosine distance is below `SIMILARITY_THRESHOLD`, the retrieved chunks are injected as context into the LLM prompt.
2. **Agent path** — when the active model supports tool calling (Gemini always does; Ollama is probed via `/api/show`), an `AgentExecutor` with MCP tools is used instead of a plain chain.
3. **Direct LLM path** — fallback when no relevant documents are found; same agent/chain structure but without the context injection.

Both the RAG and direct paths share two executor variants (`_rag_executor`, `_direct_executor`) built during `initialize()`.

### LLM modes (`LLM_MODE` env var)

| Value | LLM | Ollama URL |
|-------|-----|------------|
| `gemini` | `ChatGoogleGenerativeAI` | — |
| `local` | `ChatOllama` | `http://localhost:11434` |
| `docker` | `ChatOllama` | `http://ollama:11434` (service name) |

`DockerManager` starts/stops docker-compose on app lifespan only when `LLM_MODE=docker`.

### MCP integration

`MultiServerMCPClient` connects via SSE to `MCP_SERVER_URL` (default `http://127.0.0.1:9005/sse`) at startup. `patch_tools_for_ollama()` (`app/services/tool_utils.py`) rewrites tool `args_schema` fields to tolerate Ollama's malformed `{"type":"string","value":"..."}` outputs.

### Service singletons

Every service (`agent_service`, `document_service`, `auth_service`, `file_storage_service`) is instantiated as a module-level singleton via a `_create_default()` factory. They are injected into routes via `Depends()`. Tests override them by patching the singleton or overriding the `get_session` dependency.

### pgvector collections

Each user gets their own collection named `user_<uuid>`. Both `AgentOrchestrationService` and `DocumentService` share the same `settings.pgvector_connection_string`, which routes to `rag_app` schema via `search_path`. The connection string uses `psycopg` (sync driver) even though the app is otherwise async — this is required by `langchain_postgres.PGVector`.

### UUID masking

`app/common/uuid_mask.py` provides `MaskedUUID`, a Pydantic annotated type. Internal UUIDv7s are AES-ECB encrypted before serialising to JSON responses and decrypted on inbound requests. Use `MaskedUUID` instead of `uuid.UUID` on any schema field that is exposed at the API boundary.

### Settings loading

`Settings.__init__` optionally fetches remote config from `PARAMS_STORE_URL` before falling back to `.env`. Keys present in the remote response override `.env` but are themselves overridden by values passed explicitly at construction time.

## Database

- Schema: `rag_app` (set globally via `MetaData(schema="rag_app")` in `app/database.py`)
- Tables: `users`, `requests`, `documents` — Alembic migrations in `alembic/versions/`
- pgvector tables (`langchain_pg_collection`, `langchain_pg_embedding`) are managed by `langchain_postgres`, not Alembic

## Testing

Tests use an in-memory SQLite database. `tests/conftest.py` provides the `auth_client` fixture, which:
- Temporarily sets `Base.metadata.schema = None` (SQLite has no schema support)
- Patches `engine` and all rate limiters
- Mocks `agent_service.initialize` and `document_service.initialize` so AI components are skipped

Integration tests (`tests/integration/`) require a live PostgreSQL instance and are kept separate.

## Mandatory Post-Task Workflow

After **any** code change:
1. `uv run ruff check . --fix`
2. `uv run pytest` — fix failures immediately, re-run until green
3. Update `Dockerfile` and `docker-compose.yml` if new env vars or dependencies were added
