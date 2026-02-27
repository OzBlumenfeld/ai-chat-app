"""
Tests for the authentication flow (register, login, token protection).

These tests use an in-memory SQLite DB via the ``auth_client`` fixture
so they run without Postgres, ChromaDB, or Ollama.
"""
import jwt
from app.config import settings


class TestRegister:
    """POST /auth/register"""

    def test_register_returns_token_and_email(self, auth_client):
        resp = auth_client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "securepass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert "token" in data
        # token should be a valid JWT containing the email
        payload = jwt.decode(
            data["token"], settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["email"] == "new@example.com"
        assert "user_id" in payload

    def test_register_duplicate_email_returns_409(self, auth_client):
        auth_client.post(
            "/auth/register",
            json={"email": "dup@example.com", "password": "securepass1"},
        )
        resp = auth_client.post(
            "/auth/register",
            json={"email": "dup@example.com", "password": "securepass1"},
        )
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    def test_register_short_password_returns_422(self, auth_client):
        resp = auth_client.post(
            "/auth/register",
            json={"email": "short@example.com", "password": "abc"},
        )
        assert resp.status_code == 422

    def test_register_long_password_returns_422(self, auth_client):
        resp = auth_client.post(
            "/auth/register",
            json={"email": "long@example.com", "password": "a" * 17},
        )
        assert resp.status_code == 422

    def test_register_invalid_email_returns_422(self, auth_client):
        resp = auth_client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "securepass1"},
        )
        assert resp.status_code == 422

    def test_register_missing_fields_returns_422(self, auth_client):
        resp = auth_client.post("/auth/register", json={})
        assert resp.status_code == 422


class TestLogin:
    """POST /auth/login"""

    def test_login_valid_credentials(self, auth_client):
        auth_client.post(
            "/auth/register",
            json={"email": "login@example.com", "password": "securepass1"},
        )
        resp = auth_client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "securepass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "login@example.com"
        assert "token" in data

    def test_login_wrong_password_returns_401(self, auth_client):
        auth_client.post(
            "/auth/register",
            json={"email": "wp@example.com", "password": "securepass1"},
        )
        resp = auth_client.post(
            "/auth/login",
            json={"email": "wp@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_login_nonexistent_user_returns_401(self, auth_client):
        resp = auth_client.post(
            "/auth/login",
            json={"email": "ghost@example.com", "password": "securepass1"},
        )
        assert resp.status_code == 401

    def test_login_token_is_valid_jwt(self, auth_client):
        auth_client.post(
            "/auth/register",
            json={"email": "jwt@example.com", "password": "securepass1"},
        )
        resp = auth_client.post(
            "/auth/login",
            json={"email": "jwt@example.com", "password": "securepass1"},
        )
        token = resp.json()["token"]
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["email"] == "jwt@example.com"
        assert "exp" in payload


class TestTokenProtection:
    """Verify that protected endpoints reject unauthenticated requests."""

    def test_query_without_token_returns_401(self, auth_client):
        resp = auth_client.post("/query", json={"question": "hello"})
        assert resp.status_code in (401, 403)

    def test_query_with_invalid_token_returns_401(self, auth_client):
        resp = auth_client.post(
            "/query",
            json={"question": "hello"},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_query_with_expired_token_returns_401(self, auth_client):
        from datetime import datetime, timedelta, timezone

        expired_payload = {
            "user_id": "00000000-0000-0000-0000-000000000000",
            "email": "expired@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )
        resp = auth_client.post(
            "/query",
            json={"question": "hello"},
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    def test_query_with_valid_token_is_not_401(self, auth_client):
        """A valid token should pass auth (may still fail downstream, but not 401)."""
        reg = auth_client.post(
            "/auth/register",
            json={"email": "authed@example.com", "password": "securepass1"},
        )
        token = reg.json()["token"]
        resp = auth_client.post(
            "/query",
            json={"question": "hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should NOT be an auth error — may be 503 (RAG not init) or 500, but not 401
        assert resp.status_code != 401
