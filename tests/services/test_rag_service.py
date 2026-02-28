"""Unit tests for RAGService query routing and initialization."""

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rag_service import RAGService


@pytest.fixture()
def mock_settings() -> Any:
    settings = MagicMock()
    settings.CHROMA_HOST = "localhost"
    settings.CHROMA_PORT = "8000"
    settings.EMBEDDING_MODEL_NAME = "test-model"
    settings.LLM_MODEL_NAME = "test-llm"
    settings.OLLAMA_BASE_URL = "http://localhost:11434"
    settings.SIMILARITY_THRESHOLD = 0.5
    return settings


@pytest.fixture()
def rag_service(mock_settings: Any) -> RAGService:
    return RAGService(settings=mock_settings)


class TestIsReady:
    """RAGService.is_ready reflects initialization state."""

    def test_not_ready_before_initialize(self, rag_service: RAGService) -> None:
        assert rag_service.is_ready is False

    @pytest.mark.asyncio
    async def test_ready_after_initialize(self, rag_service: RAGService) -> None:
        with (
            patch("app.services.rag_service.chromadb.HttpClient"),
            patch("app.services.rag_service.HuggingFaceEmbeddings"),
            patch("app.services.rag_service.OllamaLLM"),
            patch("app.services.rag_service.PromptTemplate"),
        ):
            await rag_service.initialize()

        assert rag_service.is_ready is True


class TestQueryRouting:
    """RAGService.query routes to RAG or LLM based on similarity scores."""

    def _setup_initialized(
        self, service: RAGService
    ) -> tuple[MagicMock, MagicMock]:
        """Put the service into an initialized state, return (rag_chain, llm) mocks."""
        mock_rag_chain = MagicMock()
        mock_rag_chain.ainvoke = AsyncMock(return_value="RAG answer")

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value="LLM answer")

        service._chroma_client = MagicMock()
        service._embeddings = MagicMock()
        service._rag_chain = mock_rag_chain
        service._llm = mock_llm

        return mock_rag_chain, mock_llm

    @pytest.mark.asyncio
    async def test_query_uses_rag_when_relevant_docs_found(
        self, rag_service: RAGService
    ) -> None:
        """Score below threshold → RAG chain used, source is 'rag'."""
        mock_rag_chain, _ = self._setup_initialized(rag_service)

        mock_doc = MagicMock()
        mock_doc.page_content = "relevant content about the topic"
        mock_vectorstore = MagicMock()
        mock_vectorstore.similarity_search_with_score.return_value = [(mock_doc, 0.2)]
        rag_service._get_user_vectorstore = MagicMock(return_value=mock_vectorstore)

        answer, source = await rag_service.query("What is this about?", uuid.uuid4())

        assert source == "rag"
        assert answer == "RAG answer"
        mock_rag_chain.ainvoke.assert_called_once()
        call_kwargs = mock_rag_chain.ainvoke.call_args[0][0]
        assert call_kwargs["context"] == "relevant content about the topic"
        assert call_kwargs["question"] == "What is this about?"

    @pytest.mark.asyncio
    async def test_query_uses_llm_when_no_docs_below_threshold(
        self, rag_service: RAGService
    ) -> None:
        """Score above threshold → LLM fallback, source is 'llm'."""
        mock_rag_chain, mock_llm = self._setup_initialized(rag_service)

        mock_doc = MagicMock()
        mock_vectorstore = MagicMock()
        mock_vectorstore.similarity_search_with_score.return_value = [
            (mock_doc, 0.9)
        ]  # 0.9 > 0.5 threshold
        rag_service._get_user_vectorstore = MagicMock(return_value=mock_vectorstore)

        answer, source = await rag_service.query("General question?", uuid.uuid4())

        assert source == "llm"
        assert answer == "LLM answer"
        mock_llm.ainvoke.assert_called_once_with("General question?")
        mock_rag_chain.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_uses_llm_when_vectorstore_is_empty(
        self, rag_service: RAGService
    ) -> None:
        """Empty vectorstore → LLM fallback, source is 'llm'."""
        _, mock_llm = self._setup_initialized(rag_service)

        mock_vectorstore = MagicMock()
        mock_vectorstore.similarity_search_with_score.return_value = []
        rag_service._get_user_vectorstore = MagicMock(return_value=mock_vectorstore)

        answer, source = await rag_service.query("Anything?", uuid.uuid4())

        assert source == "llm"
        assert answer == "LLM answer"
        mock_llm.ainvoke.assert_called_once_with("Anything?")

    @pytest.mark.asyncio
    async def test_query_filters_only_docs_below_threshold(
        self, rag_service: RAGService
    ) -> None:
        """Mixed scores: only docs below threshold are used in context."""
        mock_rag_chain, _ = self._setup_initialized(rag_service)

        doc_a = MagicMock()
        doc_a.page_content = "good content"
        doc_b = MagicMock()
        doc_b.page_content = "irrelevant content"

        mock_vectorstore = MagicMock()
        mock_vectorstore.similarity_search_with_score.return_value = [
            (doc_a, 0.3),  # below 0.5 → included
            (doc_b, 0.8),  # above 0.5 → excluded
        ]
        rag_service._get_user_vectorstore = MagicMock(return_value=mock_vectorstore)

        answer, source = await rag_service.query("test?", uuid.uuid4())

        assert source == "rag"
        call_kwargs = mock_rag_chain.ainvoke.call_args[0][0]
        assert "good content" in call_kwargs["context"]
        assert "irrelevant content" not in call_kwargs["context"]


class TestGetUserVectorstore:
    """RAGService._get_user_vectorstore uses the correct collection name."""

    def test_vectorstore_collection_name_includes_user_id(
        self, rag_service: RAGService
    ) -> None:
        user_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        rag_service._chroma_client = MagicMock()
        rag_service._embeddings = MagicMock()

        with patch("app.services.rag_service.Chroma") as mock_chroma_cls:
            mock_chroma_cls.return_value = MagicMock()
            rag_service._get_user_vectorstore(user_id)

        mock_chroma_cls.assert_called_once_with(
            client=rag_service._chroma_client,
            collection_name=f"user_{user_id}",
            embedding_function=rag_service._embeddings,
        )
