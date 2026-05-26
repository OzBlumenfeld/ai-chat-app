"""
Integration test fixtures.

Requires:
  - PostgreSQL + pgvector running (the docker-compose stack)
  - HuggingFace embeddings (downloaded automatically on first run)
  - LLM configured via env vars (Gemini API key or Ollama)

Run integration tests with:
    uv run pytest tests/integration/ -m integration -v
"""
from collections.abc import Generator
from pathlib import Path

import pytest
from starlette.testclient import TestClient

TEST_USER_EMAIL = "integration_test@test.local"
TEST_USER_PASSWORD = "TestPass123"

_DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """TestClient backed by real services — no mocks, no SQLite override.

    Using TestClient as a context manager triggers the FastAPI lifespan, which
    initialises agent_service and document_service against real PostgreSQL.
    """
    from main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_header(client: TestClient) -> Generator[dict[str, str], None, None]:
    """Register the integration test user (idempotent), log in, yield the JWT header.

    Deletes all documents owned by the test user after the whole module finishes
    so the vector collection is clean for subsequent runs.
    """
    client.post(
        "/auth/register",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    resp = client.post(
        "/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"

    header = {"Authorization": f"Bearer {resp.json()['token']}"}
    yield header

    client.delete("/documents", headers=header)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _upload_docs(client: TestClient, header: dict[str, str], filenames: list[str]) -> None:
    """Upload the named files from tests/data/ via the /documents/upload endpoint."""
    files = [
        ("files", (name, (_DATA_DIR / name).read_bytes(), "text/plain"))
        for name in filenames
    ]
    resp = client.post("/documents/upload", headers=header, files=files)
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    assert resp.json()["uploaded"], "No documents were uploaded"


# ---------------------------------------------------------------------------
# Document-set fixtures (function scope → fresh state per test)
# ---------------------------------------------------------------------------

@pytest.fixture()
def auth_doc_only(client: TestClient, auth_header: dict[str, str]) -> Generator[None, None, None]:
    """Only tech_doc1.txt (DataSync authentication) is present."""
    client.delete("/documents", headers=auth_header)
    _upload_docs(client, auth_header, ["tech_doc1.txt"])
    yield
    client.delete("/documents", headers=auth_header)


@pytest.fixture()
def webhooks_doc_only(client: TestClient, auth_header: dict[str, str]) -> Generator[None, None, None]:
    """Only tech_doc2.txt (DataSync webhooks) is present."""
    client.delete("/documents", headers=auth_header)
    _upload_docs(client, auth_header, ["tech_doc2.txt"])
    yield
    client.delete("/documents", headers=auth_header)


@pytest.fixture()
def errors_doc_only(client: TestClient, auth_header: dict[str, str]) -> Generator[None, None, None]:
    """Only tech_doc3.txt (DataSync error codes) is present."""
    client.delete("/documents", headers=auth_header)
    _upload_docs(client, auth_header, ["tech_doc3.txt"])
    yield
    client.delete("/documents", headers=auth_header)


@pytest.fixture()
def datasync_only(client: TestClient, auth_header: dict[str, str]) -> Generator[None, None, None]:
    """All three DataSync docs (auth, webhooks, errors) but NOT go.txt."""
    client.delete("/documents", headers=auth_header)
    _upload_docs(client, auth_header, ["tech_doc1.txt", "tech_doc2.txt", "tech_doc3.txt"])
    yield
    client.delete("/documents", headers=auth_header)


@pytest.fixture()
def all_docs(client: TestClient, auth_header: dict[str, str]) -> Generator[None, None, None]:
    """All four test documents, including the unrelated go.txt."""
    client.delete("/documents", headers=auth_header)
    _upload_docs(client, auth_header, ["tech_doc1.txt", "tech_doc2.txt", "tech_doc3.txt", "go.txt"])
    yield
    client.delete("/documents", headers=auth_header)
