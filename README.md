# RAG Model API

An API to query documents using a Retrieval-Augmented Generation (RAG) model with FastAPI, LangChain, and Ollama.

## Prerequisites

- **Python 3.12-3.13** (required)
- **uv** - Python package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Docker & Docker Compose** - For running ChromaDB and PostgreSQL
- **Ollama** - For running local LLMs ([install guide](https://ollama.ai))
- **Node.js 18+** - For the frontend (optional)

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Start Docker Services

Start ChromaDB (vector store) and PostgreSQL (user database):

```bash
docker-compose up -d
```

This starts:
- **ChromaDB** at `http://localhost:8000`
- **ChromaDB Admin UI** at `http://localhost:3001`
- **PostgreSQL** at `localhost:5432`

### 3. Install and Run Ollama

Install Ollama from [ollama.ai](https://ollama.ai), then pull the required model:

```bash
ollama pull llama3.2
```

Make sure Ollama is running:

```bash
ollama serve
```

### 4. Run Database Migrations

Apply Alembic migrations to set up the PostgreSQL database:

```bash
uv run alembic upgrade head
```

### 5. Ingest Documents

Place your PDF files in the `docs/` directory, then run:

```bash
uv run python ingest.py
```

### 6. Run the API

```bash
uv run python main.py
```

The API runs at `http://localhost:8080`. API docs available at `/docs`.

**Alternative (with auto-reload for development):**

```bash
uv run fastapi dev main.py --port 8080
```

### 7. Run the Frontend (Optional)

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`.

## Environment Variables

The app uses these environment variables (with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/rag_app` | PostgreSQL connection URL |
| `JWT_SECRET` | `dev-secret-change-in-production` | Secret key for JWT tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRY_HOURS` | `24` | JWT token expiry time |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | Allowed CORS origin |

Create a `.env` file in the project root to override these values.

## API Usage

### Query the RAG Model

Send a POST request to `/query` with a JSON body containing your question.

**Example with curl:**

```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who is Oz Blumenfeld?"}'
```

**Example response:**

```json
{"answer": "Oz Blumenfeld is a Senior Backend Engineer."}
```

### Authentication Endpoints

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and receive JWT token

## Testing

Run tests with pytest:

```bash
uv run pytest test_query.py -v
```

**Note:** Tests require ChromaDB and Ollama to be running, and documents to be ingested.

## Development Commands

```bash
# Install dependencies
uv sync

# Add a new package
uv add <package>

# Run linting
uv run ruff check . --fix

# Run tests
uv run pytest

# Start all Docker services
docker-compose up -d

# Stop Docker services
docker-compose down

# View Docker logs
docker-compose logs -f
```

## Project Structure

```
.
├── app/
│   ├── auth.py           # JWT authentication utilities
│   ├── config.py         # Application settings
│   ├── database.py       # Database connection
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   └── routes/
│       ├── auth_routes.py    # Authentication endpoints
│       └── query_routes.py   # RAG query endpoints
├── alembic/              # Database migrations
├── docs/                 # PDF documents for ingestion
├── frontend/             # React frontend
├── main.py              # FastAPI application
├── ingest.py            # Document ingestion script
├── docker-compose.yml   # Docker services configuration
└── pyproject.toml       # Python dependencies
```

## Troubleshooting

### ChromaDB connection error
Make sure Docker is running and services are started:
```bash
docker-compose up -d
docker-compose ps
```

### Ollama model not found
Pull the required model:
```bash
ollama pull llama3.2
```

### Database migration errors
Ensure PostgreSQL is running and apply migrations:
```bash
docker-compose up -d postgres
uv run alembic upgrade head
```
