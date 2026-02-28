"""
Tests for POST /email/send endpoint.
"""
from unittest.mock import AsyncMock


from app.services.email_service import EmailService, get_email_service


class TestSendEmail:
    """POST /email/send"""

    def _register_and_token(self, client) -> str:
        resp = client.post(
            "/auth/register",
            json={"email": "sender@example.com", "password": "securepass1"},
        )
        return resp.json()["token"]

    def test_send_email_success(self, auth_client) -> None:
        token = self._register_and_token(auth_client)

        mock_service = AsyncMock(spec=EmailService)
        mock_service.send_email.return_value = True

        from main import app

        app.dependency_overrides[get_email_service] = lambda: mock_service

        try:
            resp = auth_client.post(
                "/email/send",
                json={
                    "recipient_email": "recipient@example.com",
                    "subject": "Hello",
                    "body": "Test body",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            del app.dependency_overrides[get_email_service]

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "sent" in data["message"].lower()
        mock_service.send_email.assert_called_once_with(
            recipient_email="recipient@example.com",
            subject="Hello",
            body="Test body",
        )

    def test_send_email_failure_returns_500(self, auth_client) -> None:
        token = self._register_and_token(auth_client)

        mock_service = AsyncMock(spec=EmailService)
        mock_service.send_email.return_value = False

        from main import app

        app.dependency_overrides[get_email_service] = lambda: mock_service

        try:
            resp = auth_client.post(
                "/email/send",
                json={
                    "recipient_email": "recipient@example.com",
                    "subject": "Hello",
                    "body": "Test body",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            del app.dependency_overrides[get_email_service]

        assert resp.status_code == 500
        assert "failed" in resp.json()["detail"].lower()

    def test_send_email_unauthenticated_returns_401(self, auth_client) -> None:
        resp = auth_client.post(
            "/email/send",
            json={
                "recipient_email": "recipient@example.com",
                "subject": "Hello",
                "body": "Test body",
            },
        )
        assert resp.status_code in (401, 403)

    def test_send_email_invalid_recipient_returns_422(self, auth_client) -> None:
        token = self._register_and_token(auth_client)

        mock_service = AsyncMock(spec=EmailService)

        from main import app

        app.dependency_overrides[get_email_service] = lambda: mock_service

        try:
            resp = auth_client.post(
                "/email/send",
                json={
                    "recipient_email": "not-an-email",
                    "subject": "Hello",
                    "body": "Test body",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            del app.dependency_overrides[get_email_service]

        assert resp.status_code == 422

    def test_send_email_missing_fields_returns_422(self, auth_client) -> None:
        token = self._register_and_token(auth_client)

        mock_service = AsyncMock(spec=EmailService)

        from main import app

        app.dependency_overrides[get_email_service] = lambda: mock_service

        try:
            resp = auth_client.post(
                "/email/send",
                json={"recipient_email": "recipient@example.com"},
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            del app.dependency_overrides[get_email_service]

        assert resp.status_code == 422
