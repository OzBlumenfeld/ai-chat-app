"""Tests for request history endpoints and service."""


class TestHistoryEndpoints:
    """Tests for /history endpoints."""

    def _register_and_get_token(self, client: object) -> str:
        resp = client.post(
            "/auth/register",
            json={"email": "history@example.com", "password": "securepass1"},
        )
        return resp.json()["token"]

    def test_list_history_empty(self, auth_client: object) -> None:
        token = self._register_and_get_token(auth_client)
        resp = auth_client.get(
            "/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["history"] == []

    def test_list_history_requires_auth(self, auth_client: object) -> None:
        resp = auth_client.get("/history")
        assert resp.status_code in (401, 403)

    def test_get_history_detail_not_found(self, auth_client: object) -> None:
        token = self._register_and_get_token(auth_client)
        resp = auth_client.get(
            "/history/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_list_history_grouped_empty(self, auth_client: object) -> None:
        token = self._register_and_get_token(auth_client)
        resp = auth_client.get(
            "/history/grouped",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["groups"] == []

    def test_list_history_grouped_requires_auth(self, auth_client: object) -> None:
        resp = auth_client.get("/history/grouped")
        assert resp.status_code in (401, 403)
