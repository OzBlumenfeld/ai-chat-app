"""
End-to-end integration tests for the RAG pipeline.

These tests define EXPECTED behaviour. They will fail until the known
relevance-filtering bug is fixed (see agent_service.py — SIMILARITY_THRESHOLD
is currently too permissive, causing off-topic queries to route to RAG and
irrelevant documents to appear as citations).

Test documents (tests/data/):
  tech_doc1.txt — DataSync API: Bearer token auth, 3600 s expiry, rate limits
  tech_doc2.txt — DataSync API: Webhooks, HMAC-SHA256 signature, 3-attempt retry
  tech_doc3.txt — DataSync API: Error codes DS-001 → DS-100
  go.txt        — Medieval sigils/heraldry (completely unrelated to DataSync)
"""
import pytest
from starlette.testclient import TestClient


# ---------------------------------------------------------------------------
# RAG vs LLM routing
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRAGRouting:
    """The pipeline must route to RAG for on-topic queries and to the LLM for
    queries that have no relevant documents in the collection."""

    def test_datasync_auth_question_routes_to_rag(
        self, client: TestClient, auth_header: dict[str, str], auth_doc_only: None
    ) -> None:
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "How long does a DataSync API access token last before expiring?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "rag", f"Expected RAG routing, got: {data['source']}"
        assert data["sources"], "Expected at least one source citation"

    def test_datasync_webhook_question_routes_to_rag(
        self, client: TestClient, auth_header: dict[str, str], webhooks_doc_only: None
    ) -> None:
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "How does DataSync verify the authenticity of webhook requests?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "rag", f"Expected RAG routing, got: {data['source']}"
        assert data["sources"], "Expected at least one source citation"

    def test_datasync_error_question_routes_to_rag(
        self, client: TestClient, auth_header: dict[str, str], errors_doc_only: None
    ) -> None:
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "What does DataSync error code DS-004 mean?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "rag", f"Expected RAG routing, got: {data['source']}"
        assert data["sources"], "Expected at least one source citation"

    def test_general_question_falls_back_to_llm(
        self, client: TestClient, auth_header: dict[str, str], datasync_only: None
    ) -> None:
        """A question unrelated to any uploaded document must not trigger RAG.

        FAILS until SIMILARITY_THRESHOLD is lowered so that off-topic queries
        exceed the threshold and fall through to the direct LLM path.
        """
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "What is the capital of France?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "llm", (
            f"Off-topic question should use LLM fallback, got: {data['source']}"
        )
        assert data["sources"] == [], "LLM fallback must return no source citations"


# ---------------------------------------------------------------------------
# Answer accuracy
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAnswerAccuracy:
    """RAG-generated answers must contain factually correct content drawn from
    the retrieved document chunk."""

    def test_token_expiry_answer(
        self, client: TestClient, auth_header: dict[str, str], auth_doc_only: None
    ) -> None:
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "How long is a DataSync API access token valid for?"},
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"].lower()
        assert any(kw in answer for kw in ("3600", "one hour", "1 hour")), (
            f"Answer should mention the 3600 s expiry, got: {answer}"
        )

    def test_webhook_signature_answer(
        self, client: TestClient, auth_header: dict[str, str], webhooks_doc_only: None
    ) -> None:
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "What algorithm does DataSync use to sign webhook payloads?"},
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"].lower()
        assert any(kw in answer for kw in ("hmac", "sha256", "hmac-sha256")), (
            f"Answer should mention HMAC-SHA256, got: {answer}"
        )

    def test_webhook_events_answer(
        self, client: TestClient, auth_header: dict[str, str], webhooks_doc_only: None
    ) -> None:
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "What events can I subscribe to with DataSync webhooks?"},
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"].lower()
        assert any(kw in answer for kw in ("sync.complete", "sync.failed")), (
            f"Answer should name webhook event types, got: {answer}"
        )

    def test_error_ds004_answer(
        self, client: TestClient, auth_header: dict[str, str], errors_doc_only: None
    ) -> None:
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "What does DataSync error code DS-004 mean?"},
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"].lower()
        assert any(kw in answer for kw in ("payload", "too large", "5mb", "5 mb")), (
            f"Answer should mention payload-too-large, got: {answer}"
        )

    def test_error_ds002_answer(
        self, client: TestClient, auth_header: dict[str, str], errors_doc_only: None
    ) -> None:
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "I got a DS-002 error from DataSync. What happened?"},
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"].lower()
        assert any(kw in answer for kw in ("token", "expired", "refresh")), (
            f"Answer should mention expired token / refresh, got: {answer}"
        )

    def test_retry_policy_answer(
        self, client: TestClient, auth_header: dict[str, str], webhooks_doc_only: None
    ) -> None:
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "How many times will DataSync retry a failed webhook delivery?"},
        )
        assert resp.status_code == 200
        answer = resp.json()["answer"].lower()
        assert any(kw in answer for kw in ("3", "three", "exponential")), (
            f"Answer should mention 3 retry attempts, got: {answer}"
        )


# ---------------------------------------------------------------------------
# Document isolation
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDocumentIsolation:
    """Citations must reflect semantic relevance. The medieval-sigils document
    (go.txt) must never appear as a source for DataSync API questions, and
    general knowledge questions must produce zero citations.

    Most tests in this class FAIL until SIMILARITY_THRESHOLD is corrected.
    """

    def test_irrelevant_doc_not_cited_for_datasync_question(
        self, client: TestClient, auth_header: dict[str, str], all_docs: None
    ) -> None:
        """go.txt must not appear as a citation for a DataSync-specific question.

        FAILS if the threshold is too permissive and go.txt chunks score below it.
        """
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "What is the DataSync API token expiration time?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        source_files = {s["filename"] for s in data["sources"]}
        assert "go.txt" not in source_files, (
            f"go.txt should not be cited for a DataSync question. Sources: {source_files}"
        )

    def test_auth_doc_cited_with_all_docs_uploaded(
        self, client: TestClient, auth_header: dict[str, str], all_docs: None
    ) -> None:
        """tech_doc1.txt must be cited and go.txt must be absent for a DataSync auth question.

        FAILS if the threshold is too permissive: MMR returns all chunks in the collection,
        so go.txt appears in sources even though it has nothing to do with DataSync.
        """
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "What is the DataSync API token expiration time?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        source_files = {s["filename"] for s in data["sources"]}
        assert "tech_doc1.txt" in source_files, (
            f"tech_doc1.txt should be cited for an auth question. Sources: {source_files}"
        )
        assert "go.txt" not in source_files, (
            f"go.txt must not appear alongside DataSync citations. Sources: {source_files}"
        )

    def test_webhook_doc_cited_and_irrelevant_doc_excluded(
        self, client: TestClient, auth_header: dict[str, str], all_docs: None
    ) -> None:
        """tech_doc2.txt must appear and go.txt must be absent for a webhook question.

        FAILS if the threshold is too permissive and go.txt sneaks into the result.
        """
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "How does DataSync sign webhook payloads?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        source_files = {s["filename"] for s in data["sources"]}
        assert "tech_doc2.txt" in source_files, (
            f"tech_doc2.txt should be cited for a webhook question. Sources: {source_files}"
        )
        assert "go.txt" not in source_files, (
            f"go.txt must not be cited for a DataSync question. Sources: {source_files}"
        )

    def test_general_question_produces_no_citations_with_all_docs(
        self, client: TestClient, auth_header: dict[str, str], all_docs: None
    ) -> None:
        """A question unrelated to any document must fall back to LLM with no citations.

        FAILS if the threshold is too permissive (routing goes to RAG instead).
        """
        resp = client.post(
            "/query",
            headers=auth_header,
            json={"question": "What is the capital of France?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "llm", (
            f"Off-topic question should use LLM fallback, got: {data['source']}"
        )
        assert data["sources"] == [], (
            f"LLM fallback must return no source citations, got: {data['sources']}"
        )
