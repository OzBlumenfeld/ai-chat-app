"""
Tests for the RAG Model API query endpoint.

Integration tests require ChromaDB and Ollama to be running with documents ingested.
"""
import pytest
import os
from fastapi.testclient import TestClient
from main import app


TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app with startup events."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def _register_test_user(client):
    """Register the test user once per module (tolerates 409 if already exists)."""
    assert TEST_USER_EMAIL
    assert TEST_USER_PASSWORD

    response = client.post(
        "/auth/register",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert response.status_code in (200, 409), f"Failed to register test user: {response.text}"

@pytest.fixture
def auth_header(client, _register_test_user):
    """Login and return a valid JWT auth header."""
    response = client.post(
        "/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 200, f"Failed to login test user: {response.text}"
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestRAGRouting:
    """Tests that verify the RAG vs LLM routing logic."""

    def test_document_question_uses_rag(self, client, auth_header):
        """Questions about ingested documents should use RAG."""
        response = client.post(
            "/query",
            json={"question": "Who is Oz Blumenfeld?"},
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "rag", f"Expected RAG source, got: {data['source']}"
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_general_question_uses_llm(self, client, auth_header):
        """General knowledge questions should use LLM directly."""
        response = client.post(
            "/query",
            json={"question": "What is the capital of France?"},
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "llm", f"Expected LLM source, got: {data['source']}"
        assert "paris" in data["answer"].lower()

    def test_unrelated_question_uses_llm(self, client, auth_header):
        """Questions unrelated to documents should use LLM."""
        response = client.post(
            "/query",
            json={"question": "What is 2 + 2?"},
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "llm", f"Expected LLM source, got: {data['source']}"


@pytest.mark.integration
class TestRAGAnswerQuality:
    """Tests that verify answer quality from RAG responses."""

    def test_oz_question_returns_relevant_info(self, client, auth_header):
        """RAG should return relevant information about Oz."""
        response = client.post(
            "/query",
            json={"question": "Who is Oz Blumenfeld?"},
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()

        answer_lower = data["answer"].lower()
        assert "oz" in answer_lower or "blumenfeld" in answer_lower, \
            f"Answer should mention Oz or Blumenfeld. Got: {data['answer']}"
        assert "don't know" not in answer_lower, \
            f"Answer should not be 'I don't know'. Got: {data['answer']}"

    def test_oz_question_variations(self, client, auth_header):
        """Various phrasings about Oz should all use RAG and return relevant info."""
        questions = [
            "Who is Oz?",
            "Tell me about Oz Blumenfeld",
            "What do you know about Oz?",
        ]

        for question in questions:
            response = client.post(
                "/query",
                json={"question": question},
                headers=auth_header,
            )
            assert response.status_code == 200
            data = response.json()

            # All variations should use RAG since they're about the document
            assert data["source"] == "rag", \
                f"Question '{question}' should use RAG, got: {data['source']}"


@pytest.mark.integration
class TestResponseStructure:
    """Tests for API response structure and validation."""

    def test_response_contains_required_fields(self, client, auth_header):
        """Response should contain answer and source fields."""
        response = client.post(
            "/query",
            json={"question": "Who is Oz Blumenfeld?"},
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data, "Response should contain 'answer' field"
        assert "source" in data, "Response should contain 'source' field"
        assert isinstance(data["answer"], str)
        assert data["source"] in ["rag", "llm"], f"Source should be 'rag' or 'llm', got: {data['source']}"

    def test_invalid_request_missing_question(self, client, auth_header):
        """Missing question field should return 422."""
        response = client.post("/query", json={}, headers=auth_header)
        assert response.status_code == 422

    def test_empty_question(self, client, auth_header):
        """Empty question should be handled gracefully."""
        response = client.post(
            "/query", json={"question": ""}, headers=auth_header
        )
        assert response.status_code in [200, 422]


class TestServiceInitialization:
    """Tests for service initialization and error handling."""

    def test_uninitialized_service_returns_503(self):
        """Endpoint should return 503 if service is not initialized."""
        from fastapi import FastAPI, HTTPException
        from app.schemas import QueryRequest, QueryResponse

        test_app = FastAPI()

        @test_app.post("/query", response_model=QueryResponse)
        async def query_model(request: QueryRequest):
            raise HTTPException(status_code=503, detail="Service is not initialized.")

        test_client = TestClient(test_app)
        response = test_client.post("/query", json={"question": "test"})
        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"].lower()


@pytest.mark.integration
class TestLLMFallback:
    """Tests for LLM direct response (when no relevant documents)."""

    def test_general_knowledge_uses_llm_and_answers_correctly(self, client, auth_header):
        """General knowledge questions should use LLM and return correct answers."""
        response = client.post(
            "/query",
            json={"question": "What is the capital of France?"},
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["source"] == "llm", "General question should use LLM"
        assert "paris" in data["answer"].lower(), f"Expected Paris in answer: {data['answer']}"

    def test_math_question_uses_llm(self, client, auth_header):
        """Math questions should use LLM directly."""
        response = client.post(
            "/query",
            json={"question": "What is 15 multiplied by 7?"},
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "llm", "Math question should use LLM"
