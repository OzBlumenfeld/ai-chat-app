"""Tests for document upload, list, get-by-id, and delete endpoints."""

import uuid
from datetime import datetime
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from uuid6 import uuid7

from app.common.uuid_mask import mask_uuid
from app.models.document import Document
from app.services.document_service import DocumentValidationError


def _stub_doc(user_id: uuid.UUID, filename: str = "test.txt") -> Document:
    """Build an in-memory Document stub (not persisted to DB)."""
    return Document(
        id=uuid7(),
        user_id=user_id,
        original_filename=filename,
        file_size=1024,
        chunk_count=5,
        collection_name=f"user_{user_id}",
        status="ready",
        created_at=datetime(2025, 1, 15, 10, 0, 0),
    )


class TestDocumentUpload:
    """POST /documents/upload"""

    def _register_and_token(self, client: Any) -> str:
        email = f"upload_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/auth/register",
            json={"email": email, "password": "securepass1"},
        )
        assert resp.status_code == 200
        return resp.json()["token"]

    def test_upload_requires_auth(self, auth_client: Any) -> None:
        resp = auth_client.post(
            "/documents/upload",
            files=[("files", ("test.txt", BytesIO(b"hello"), "text/plain"))],
        )
        assert resp.status_code in (401, 403)

    def test_upload_single_file_success(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)

        with patch("app.routes.document_routes.document_service") as mock_svc:
            mock_svc.validate_file = MagicMock()

            async def fake_process(
                file: Any, user_id: uuid.UUID, user_email: str, session: Any
            ) -> Document:
                return _stub_doc(user_id, file.filename)

            mock_svc.process_document = AsyncMock(side_effect=fake_process)

            resp = auth_client.post(
                "/documents/upload",
                files=[("files", ("report.txt", BytesIO(b"hello world"), "text/plain"))],
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["uploaded"]) == 1
        assert data["errors"] == []
        assert data["uploaded"][0]["original_filename"] == "report.txt"
        assert data["uploaded"][0]["status"] == "ready"

    def test_upload_validation_error_collected_in_errors(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)

        with patch("app.routes.document_routes.document_service") as mock_svc:
            mock_svc.validate_file = MagicMock(
                side_effect=DocumentValidationError("Unsupported file type")
            )

            resp = auth_client.post(
                "/documents/upload",
                files=[("files", ("malware.exe", BytesIO(b"data"), "application/octet-stream"))],
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["uploaded"] == []
        assert len(data["errors"]) == 1
        assert "malware.exe" in data["errors"][0]

    def test_upload_too_many_files_returns_400(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)

        from app.config import settings

        files = [
            ("files", (f"f{i}.txt", BytesIO(b"x"), "text/plain"))
            for i in range(settings.MAX_FILES_PER_UPLOAD + 1)
        ]
        resp = auth_client.post(
            "/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "maximum" in resp.json()["detail"].lower()

    def test_upload_partial_success(self, auth_client: Any) -> None:
        """First file succeeds; second fails validation — each appears in the correct list."""
        token = self._register_and_token(auth_client)

        call_count = 0

        with patch("app.routes.document_routes.document_service") as mock_svc:

            def validate_side_effect(file: Any) -> None:
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise DocumentValidationError("unsupported type")

            mock_svc.validate_file = MagicMock(side_effect=validate_side_effect)

            async def fake_process(
                file: Any, user_id: uuid.UUID, user_email: str, session: Any
            ) -> Document:
                return _stub_doc(user_id, file.filename)

            mock_svc.process_document = AsyncMock(side_effect=fake_process)

            resp = auth_client.post(
                "/documents/upload",
                files=[
                    ("files", ("good.txt", BytesIO(b"hello"), "text/plain")),
                    ("files", ("bad.exe", BytesIO(b"data"), "application/octet-stream")),
                ],
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["uploaded"]) == 1
        assert data["uploaded"][0]["original_filename"] == "good.txt"
        assert len(data["errors"]) == 1
        assert "bad.exe" in data["errors"][0]


class TestDocumentList:
    """GET /documents"""

    def _register_and_token(self, client: Any) -> str:
        email = f"listdoc_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/auth/register",
            json={"email": email, "password": "securepass1"},
        )
        assert resp.status_code == 200
        return resp.json()["token"]

    def test_list_requires_auth(self, auth_client: Any) -> None:
        resp = auth_client.get("/documents")
        assert resp.status_code in (401, 403)

    def test_list_empty_returns_empty_list(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)

        with patch("app.routes.document_routes.document_service") as mock_svc:
            mock_svc.list_documents = AsyncMock(return_value=[])

            resp = auth_client.get(
                "/documents",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["documents"] == []

    def test_list_returns_user_documents(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)
        user_id = uuid.uuid4()
        fake_doc = _stub_doc(user_id, "report.pdf")

        with patch("app.routes.document_routes.document_service") as mock_svc:
            mock_svc.list_documents = AsyncMock(return_value=[fake_doc])

            resp = auth_client.get(
                "/documents",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        docs = resp.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["original_filename"] == "report.pdf"
        assert docs[0]["file_size"] == 1024
        assert docs[0]["status"] == "ready"


class TestDocumentGetById:
    """GET /documents/{doc_id}"""

    def _register_and_token(self, client: Any) -> str:
        email = f"getdoc_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/auth/register",
            json={"email": email, "password": "securepass1"},
        )
        assert resp.status_code == 200
        return resp.json()["token"]

    def _upload_real_doc(
        self, auth_client: Any, token: str, filename: str = "test.txt"
    ) -> str:
        """Upload a document that is actually persisted to the DB. Returns its masked ID."""
        with patch("app.routes.document_routes.document_service") as mock_svc:
            mock_svc.validate_file = MagicMock()

            async def fake_process(
                file: Any, user_id: uuid.UUID, user_email: str, session: Any
            ) -> Document:
                doc = Document(
                    user_id=user_id,
                    original_filename=file.filename,
                    file_size=1024,
                    chunk_count=5,
                    collection_name=f"user_{user_id}",
                    status="ready",
                    created_at=datetime(2025, 1, 15, 10, 0, 0),
                )
                session.add(doc)
                await session.flush()
                await session.commit()
                return doc

            mock_svc.process_document = AsyncMock(side_effect=fake_process)

            resp = auth_client.post(
                "/documents/upload",
                files=[("files", (filename, BytesIO(b"content"), "text/plain"))],
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        return str(resp.json()["uploaded"][0]["id"])

    def test_get_requires_auth(self, auth_client: Any) -> None:
        masked = str(mask_uuid(uuid.uuid4()))
        resp = auth_client.get(f"/documents/{masked}")
        assert resp.status_code in (401, 403)

    def test_get_nonexistent_returns_404(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)
        masked = str(mask_uuid(uuid.uuid4()))

        resp = auth_client.get(
            f"/documents/{masked}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_get_owned_document_returns_200(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)
        masked_id = self._upload_real_doc(auth_client, token, "myfile.txt")

        resp = auth_client.get(
            f"/documents/{masked_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["original_filename"] == "myfile.txt"
        assert data["status"] == "ready"

    def test_get_other_users_document_returns_404(self, auth_client: Any) -> None:
        """User B must not be able to retrieve User A's document."""
        token_a = self._register_and_token(auth_client)
        masked_id = self._upload_real_doc(auth_client, token_a, "userA_doc.txt")

        email_b = f"docget_b_{uuid.uuid4().hex[:8]}@example.com"
        token_b = auth_client.post(
            "/auth/register",
            json={"email": email_b, "password": "securepass1"},
        ).json()["token"]

        resp = auth_client.get(
            f"/documents/{masked_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404


class TestDocumentDelete:
    """DELETE /documents/{doc_id}"""

    def _register_and_token(self, client: Any) -> str:
        email = f"deldoc_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/auth/register",
            json={"email": email, "password": "securepass1"},
        )
        assert resp.status_code == 200
        return resp.json()["token"]

    def test_delete_requires_auth(self, auth_client: Any) -> None:
        masked = str(mask_uuid(uuid.uuid4()))
        resp = auth_client.delete(f"/documents/{masked}")
        assert resp.status_code in (401, 403)

    def test_delete_success(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)
        masked = str(mask_uuid(uuid.uuid4()))

        with patch("app.routes.document_routes.document_service") as mock_svc:
            mock_svc.delete_document = AsyncMock(return_value=None)

            resp = auth_client.delete(
                f"/documents/{masked}",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Document deleted successfully"

    def test_delete_not_found_returns_404(self, auth_client: Any) -> None:
        token = self._register_and_token(auth_client)
        masked = str(mask_uuid(uuid.uuid4()))

        with patch("app.routes.document_routes.document_service") as mock_svc:
            mock_svc.delete_document = AsyncMock(
                side_effect=ValueError("Document not found or unauthorized")
            )

            resp = auth_client.delete(
                f"/documents/{masked}",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
