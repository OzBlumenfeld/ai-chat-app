# AI Agent Platform

A production-quality AI assistant platform built with FastAPI and LangChain. Users upload documents, ask questions, and get answers grounded in their personal document library — or invoke an MCP-connected agent that can reason through complex tasks and use tools. Supports both local (Ollama) and cloud (Google Gemini) LLMs.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Frontend                          │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP / JWT
┌───────────────────────────────▼─────────────────────────────────┐
│                      FastAPI Application                        │
│                                                                 │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────────┐ │
│  │     Auth     │  │   Documents   │  │        Query          │ │
│  │  JWT + bcrypt│  │ Upload / Index│  │  RAG + Agent + Tools  │ │
│  └──────────────┘  └───────┬───────┘  └──────────┬────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                             │                      │
              ┌──────────────▼──────────┐  ┌───────▼───────────────┐
              │  PostgreSQL + pgvector  │  │      MCP Server       │
              │   (vectors + app data)  │  │   (tools: math, email)│
              └─────────────────────────┘  └───────────────────────┘
                                                    │
                              ┌─────────────────────▼─────────────┐
                              │        LLM Backend (choose one)   │
                              │  • Ollama (local / Docker)        │
                              │  • Google Gemini API              │
                              └───────────────────────────────────┘
```

### Query Pipeline

Every incoming query goes through an intelligent routing pipeline:

1. **Vector search** — dual async search (MMR + scored similarity) against the user's pgvector collection
2. **RAG path** — if relevant documents are found, inject them as context into the LLM prompt
3. **Agent path** — if the active model supports tool calling, an `AgentExecutor` is used; the agent can invoke MCP tools (calculator, email, etc.) to complete the request
4. **Direct LLM fallback** — if no relevant documents exist, the query goes straight to the LLM without forcing irrelevant context

## Features

| Feature | Details |
|---|---|
| **Retrieval-Augmented Generation** | User-scoped pgvector collections; MMR search for diverse, high-quality chunks |
| **Agentic tool use** | LangChain `AgentExecutor` + MCP tools; automatically enabled when the LLM supports it |
| **Multi-LLM support** | Ollama (local or Dockerized) or Google Gemini; runtime-switchable via `LLM_MODE` |
| **Document management** | Upload PDF/TXT files; per-user isolated vector collections; delete by ID or bulk |
| **Query history** | Every query and answer is persisted; browsable by date grouped by month |
| **JWT authentication** | Stateless auth with bcrypt password hashing |
| **Rate limiting** | Sliding-window in-memory rate limiting on query, upload, login, and register endpoints |
| **UUID masking** | AES-256 obfuscation of internal IDs in API responses |
| **Structured logging** | JSON-structured logs with request tracing throughout the stack |
| **Centralized config** | Optional remote Params Store for runtime configuration management |

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Orchestration | LangChain (LCEL, AgentExecutor) |
| Vector store | PostgreSQL 16 + pgvector |
| Embeddings | HuggingFace `sentence-transformers` |
| LLM (local) | Ollama (`gemma3:4b` default) |
| LLM (cloud) | Google Gemini |
| Agent tools | MCP server (SSE transport) via `langchain-mcp-adapters` |
| Database | PostgreSQL 16 (asyncpg + SQLAlchemy async) |
| Migrations | Alembic |
| Auth | PyJWT + bcrypt |
| Frontend | React |
| Containerization | Docker Compose |
| Package manager | uv |

> **Removed:** ChromaDB (replaced by pgvector) · Redis (replaced by in-memory rate limiting)

## API Reference

All endpoints except `/auth/register` and `/auth/login` require a `Bearer` token in the `Authorization` header.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new account |
| `POST` | `/auth/login` | Authenticate and receive a JWT |
| `GET` | `/auth/me` | Get the current user profile |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/documents/upload` | Upload one or more PDF/TXT files |
| `GET` | `/documents` | List all uploaded documents |
| `GET` | `/documents/{id}` | Get document metadata |
| `DELETE` | `/documents/{id}` | Delete a document and its vectors |
| `DELETE` | `/documents` | Delete all documents for the user |

### Query

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/query` | Submit a question; returns answer, source mode (`rag`/`llm`), and citations |

**Request body:**
```json
{
  "question": "What are the key findings in the Q3 report?",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

**Response:**
```json
{
  "answer": "The Q3 report highlights...",
  "source": "rag",
  "sources": [
    {
      "filename": "q3-report.pdf",
      "doc_id": "abc123",
      "excerpt": "Key findings include...",
      "page": 4
    }
  ]
}
```

### History

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/history` | List all query history (newest first) |
| `GET` | `/history/grouped` | History grouped by calendar month |
| `GET` | `/history/{id}` | Full detail for a single entry |

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection URL (asyncpg driver) |
| `JWT_SECRET` | Yes | Secret key for signing JWT tokens |
| `JWT_ALGORITHM` | Yes | JWT algorithm (e.g. `HS256`) |
| `JWT_EXPIRY_HOURS` | Yes | Token lifetime in hours |
| `LLM_MODE` | Yes | `local`, `docker`, or `gemini` |
| `LLM_MODEL_NAME` | Yes | Ollama model name (e.g. `gemma3:4b`) |
| `EMBEDDING_MODEL_NAME` | Yes | HuggingFace sentence-transformer model |
| `SIMILARITY_THRESHOLD` | Yes | Vector distance cutoff for RAG routing |
| `FILE_STORAGE_ROOT` | Yes | Local path for uploaded file storage |
| `UUID_MASK_KEY` | Yes | 64-char hex key for AES-256 UUID masking |
| `FRONTEND_ORIGIN` | Yes | Allowed CORS origin |
| `GEMINI_API_KEY` | Gemini only | Google Gemini API key |
| `GEMINI_MODEL` | Gemini only | Gemini model name (e.g. `gemini-2.0-flash`) |
| `OLLAMA_BASE_URL` | Ollama only | Defaults based on `LLM_MODE` |
| `MCP_SERVER_URL` | No | MCP server SSE endpoint (default: `http://127.0.0.1:9005/sse`) |
| `PARAMS_STORE_URL` | No | Remote config service URL |
| `LOG_LEVEL` | Yes | Logging level (e.g. `INFO`, `DEBUG`) |
| `MAX_UPLOAD_SIZE` | Yes | Max file size in bytes |
| `MAX_FILES_PER_UPLOAD` | Yes | Max files per upload request |
| `ALLOWED_EXTENSIONS` | Yes | Allowed file extensions (e.g. `["pdf", "txt"]`) |

## Project Structure

```
.
├── app/
│   ├── common/               # Shared utilities (UUID masking)
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── document.py
│   │   ├── request.py
│   │   └── user.py
│   ├── routes/               # FastAPI route handlers
│   │   ├── auth_routes.py
│   │   ├── document_routes.py
│   │   ├── query_routes.py
│   │   └── request_history_routes.py
│   ├── services/             # Business logic
│   │   ├── rag_service.py         # Agent orchestration (RAG + tools + LLM)
│   │   ├── document_service.py    # Document processing and indexing
│   │   ├── file_storage_service.py
│   │   ├── docker_manager.py      # Ollama Docker lifecycle management
│   │   ├── interfaces.py          # Abstract base classes
│   │   └── tool_utils.py          # MCP tool patching for Ollama compatibility
│   ├── auth.py               # JWT middleware
│   ├── config.py             # Settings (pydantic-settings + remote Params Store)
│   ├── database.py           # Async SQLAlchemy engine
│   ├── logging_config.py     # Structured logging setup
│   ├── rate_limit.py         # In-memory sliding-window rate limiters
│   └── schemas.py            # Pydantic request/response models
├── alembic/                  # Database migrations
├── frontend/                 # React frontend
├── tests/                    # Pytest test suite
├── docker-compose.yml        # Ollama + PostgreSQL services
├── main.py                   # Application entrypoint
└── pyproject.toml
```

## Development

```bash
# Install dependencies
uv sync

# Run the API (with hot reload)
uv run fastapi dev main.py --port 8080

# Run tests
uv run pytest

# Lint and autofix
uv run ruff check . --fix

# Apply database migrations
uv run alembic upgrade head

# Generate a new migration
uv run alembic revision --autogenerate -m "description"

# Start infrastructure (PostgreSQL + Ollama)
docker-compose up -d

# Rebuild and start all services
docker-compose up --build
```
