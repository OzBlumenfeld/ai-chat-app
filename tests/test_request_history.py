"""Tests for request history endpoints and service."""

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch


def _make_query(
    client: Any,
    token: str,
    question: str = "What is the capital of France?",
    answer: str = "Paris.",
) -> None:
    """Issue a POST /query with a fully mocked RAG service to create one history entry."""
    with patch("app.routes.query_routes.rag_service") as mock_rag:
        mock_rag.is_ready = True
        mock_rag.query = AsyncMock(return_value=(answer, "llm"))
        client.post(
            "/query",
            json={"question": question},
            headers={"Authorization": f"Bearer {token}"},
        )


class TestHistoryEndpoints:
    """Basic /history endpoint tests (empty state, auth guards)."""

    def _register_and_get_token(self, client: Any) -> str:
        resp = client.post(
            "/auth/register",
            json={"email": "history@example.com", "password": "securepass1"},
        )
        return resp.json()["token"]

    def test_list_history_empty(self, auth_client: Any) -> None:
        token = self._register_and_get_token(auth_client)
        resp = auth_client.get(
            "/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["history"] == []

    def test_list_history_requires_auth(self, auth_client: Any) -> None:
        resp = auth_client.get("/history")
        assert resp.status_code in (401, 403)

    def test_get_history_detail_not_found(self, auth_client: Any) -> None:
        token = self._register_and_get_token(auth_client)
        resp = auth_client.get(
            "/history/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_list_history_grouped_empty(self, auth_client: Any) -> None:
        token = self._register_and_get_token(auth_client)
        resp = auth_client.get(
            "/history/grouped",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["groups"] == []

    def test_list_history_grouped_requires_auth(self, auth_client: Any) -> None:
        resp = auth_client.get("/history/grouped")
        assert resp.status_code in (401, 403)


class TestHistoryWithData:
    """History endpoints with actual Request records created via /query."""

    def _register_and_token(self, client: Any, suffix: str = "") -> str:
        email = f"histdata{suffix}_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/auth/register",
            json={"email": email, "password": "securepass1"},
        )
        assert resp.status_code == 200
        return resp.json()["token"]

    def test_list_history_returns_entries(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)
        _make_query(auth_client, token, "What is Python?")

        resp = auth_client.get("/history", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        history = resp.json()["history"]
        assert len(history) == 1
        assert history[0]["question"] == "What is Python?"
        assert history[0]["source"] == "llm"
        assert "id" in history[0]
        assert "created_at" in history[0]

    def test_list_history_contains_multiple_entries(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)
        _make_query(auth_client, token, "First question")
        _make_query(auth_client, token, "Second question")

        resp = auth_client.get("/history", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        history = resp.json()["history"]
        assert len(history) == 2
        questions = [h["question"] for h in history]
        assert "First question" in questions
        assert "Second question" in questions

    def test_get_history_detail_returns_full_answer(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)

        with patch("app.routes.query_routes.rag_service") as mock_rag:
            mock_rag.is_ready = True
            mock_rag.query = AsyncMock(return_value=("The capital is Paris.", "llm"))
            auth_client.post(
                "/query",
                json={"question": "What is the capital of France?"},
                headers={"Authorization": f"Bearer {token}"},
            )

        list_resp = auth_client.get(
            "/history", headers={"Authorization": f"Bearer {token}"}
        )
        entry_id = list_resp.json()["history"][0]["id"]

        resp = auth_client.get(
            f"/history/{entry_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["question"] == "What is the capital of France?"
        assert data["response"] == "The capital is Paris."
        assert data["source"] == "llm"

    def test_grouped_history_contains_all_entries(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)
        _make_query(auth_client, token, "Question 1")
        _make_query(auth_client, token, "Question 2")

        resp = auth_client.get(
            "/history/grouped", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        groups = resp.json()["groups"]
        assert len(groups) >= 1
        total_entries = sum(len(g["entries"]) for g in groups)
        assert total_entries == 2


class TestHistoryIsolation:
    """User A's history records must not be visible to User B."""

    def _register_and_token(self, client: Any, suffix: str) -> str:
        email = f"histiso_{suffix}_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/auth/register",
            json={"email": email, "password": "securepass1"},
        )
        assert resp.status_code == 200
        return resp.json()["token"]

    def test_user_sees_only_own_history(self, auth_client: Any) -> None:
        token_a = self._register_and_token(auth_client, "a")
        token_b = self._register_and_token(auth_client, "b")

        _make_query(auth_client, token_a, "User A's question")

        resp_a = auth_client.get("/history", headers={"Authorization": f"Bearer {token_a}"})
        resp_b = auth_client.get("/history", headers={"Authorization": f"Bearer {token_b}"})

        assert len(resp_a.json()["history"]) == 1
        assert resp_b.json()["history"] == []

    def test_user_cannot_access_other_users_history_detail(self, auth_client: Any) -> None:
        token_a = self._register_and_token(auth_client, "a")
        token_b = self._register_and_token(auth_client, "b")

        _make_query(auth_client, token_a, "User A's private question")

        list_resp = auth_client.get(
            "/history", headers={"Authorization": f"Bearer {token_a}"}
        )
        entry_id = list_resp.json()["history"][0]["id"]

        resp = auth_client.get(
            f"/history/{entry_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404
