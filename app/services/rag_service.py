import logging
from uuid import UUID

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

from app.config import Settings
from app.services.interfaces import AbstractRAGService, SourceInfo

logger = logging.getLogger(__name__)

_RAG_SYSTEM_PROMPT = """You are a helpful assistant who answers questions based on the provided context.
If the answer is not in the context, say that you don't know based on the available documents.
Do not make up information.

Context from documents:
{context}"""

_DIRECT_SYSTEM_PROMPT = "You are a helpful assistant."


class RAGService(AbstractRAGService):
    """Concrete RAG service backed by ChromaDB, HuggingFace embeddings, and Ollama or Gemini."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._chroma_client: chromadb.ClientAPI | None = None
        self._embeddings: HuggingFaceEmbeddings | None = None
        self._llm: BaseChatModel | None = None
        self._rag_chain: Runnable | None = None
        self._direct_chain: Runnable | None = None

    @property
    def is_ready(self) -> bool:
        return self._chroma_client is not None and self._llm is not None

    async def initialize(self) -> None:
        """Called once during app startup."""
        logger.info("Initializing RAG chain")

        logger.info("Loading embedding model", extra={"model": self._settings.EMBEDDING_MODEL_NAME})
        self._embeddings = HuggingFaceEmbeddings(
            model_name=self._settings.EMBEDDING_MODEL_NAME
        )

        logger.info("Connecting to ChromaDB", extra={"host": self._settings.CHROMA_HOST, "port": self._settings.CHROMA_PORT})
        self._chroma_client = chromadb.HttpClient(
            host=self._settings.CHROMA_HOST, port=int(self._settings.CHROMA_PORT)
        )
        logger.info("Connected to ChromaDB")

        if self._settings.LLM_MODE == "gemini":
            logger.info("Loading Gemini model", extra={"model": self._settings.GEMINI_MODEL})
            self._llm = ChatGoogleGenerativeAI(
                model=self._settings.GEMINI_MODEL,
                google_api_key=self._settings.GEMINI_API_KEY,
            )
        else:
            logger.info("Loading Ollama LLM", extra={"model": self._settings.LLM_MODEL_NAME})
            self._llm = ChatOllama(
                model=self._settings.LLM_MODEL_NAME,
                base_url=self._settings.OLLAMA_BASE_URL,
            )
        logger.info("LLM loaded successfully")

        rag_prompt = ChatPromptTemplate.from_messages([
            ("system", _RAG_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", "{question}"),
        ])
        direct_prompt = ChatPromptTemplate.from_messages([
            ("system", _DIRECT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", "{question}"),
        ])
        parser = StrOutputParser()
        self._rag_chain = rag_prompt | self._llm | parser
        self._direct_chain = direct_prompt | self._llm | parser
        logger.info("RAG chain initialized successfully")

    async def query(
        self,
        question: str,
        user_id: UUID,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str, str, list[SourceInfo]]:
        """
        Run similarity search + RAG chain or LLM fallback.
        Returns (answer, source, sources) where source is "rag" or "llm".
        """
        history_msgs = self._build_history(history)
        vectorstore = self._get_user_vectorstore(user_id)
        docs_with_scores = vectorstore.similarity_search_with_score(question, k=4)
        relevant_docs = [
            (doc, score)
            for doc, score in docs_with_scores
            if score < self._settings.SIMILARITY_THRESHOLD
        ]

        if relevant_docs:
            best_score = min(score for _, score in relevant_docs)
            logger.debug(
                "Relevant documents found, using RAG",
                extra={"count": len(relevant_docs), "best_score": round(best_score, 3)},
            )
            context = "\n\n".join(doc.page_content for doc, _ in relevant_docs)
            answer = await self._rag_chain.ainvoke(
                {"context": context, "question": question, "history": history_msgs}
            )
            sources = [self._make_source(doc) for doc, _ in relevant_docs]
            return answer, "rag", sources

        if docs_with_scores:
            best_score = min(score for _, score in docs_with_scores)
            logger.debug(
                "No relevant documents above threshold, using LLM directly",
                extra={"best_score": round(best_score, 3), "threshold": self._settings.SIMILARITY_THRESHOLD},
            )
        else:
            logger.debug("No documents in store, using LLM directly")

        answer = await self._direct_chain.ainvoke(
            {"question": question, "history": history_msgs}
        )
        return answer, "llm", []

    def _get_user_vectorstore(self, user_id: UUID) -> Chroma:
        """Get or create a vectorstore for a user's documents."""
        collection_name = f"user_{user_id}"
        return Chroma(
            client=self._chroma_client,
            collection_name=collection_name,
            embedding_function=self._embeddings,
        )

    @staticmethod
    def _build_history(history: list[dict[str, str]] | None) -> list[BaseMessage]:
        """Convert plain dicts to LangChain message objects."""
        if not history:
            return []
        messages: list[BaseMessage] = []
        for msg in history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            else:
                messages.append(AIMessage(content=msg.get("content", "")))
        return messages

    @staticmethod
    def _make_source(doc: object) -> SourceInfo:
        """Build a SourceInfo from a retrieved LangChain document."""
        metadata: dict[str, object] = getattr(doc, "metadata", {})
        page_content: str = getattr(doc, "page_content", "")
        raw_page = metadata.get("page")
        page: int | None = int(raw_page) if isinstance(raw_page, (int, float)) else None
        return SourceInfo(
            filename=str(metadata.get("filename") or metadata.get("source") or "Unknown"),
            doc_id=str(metadata.get("doc_id", "")),
            excerpt=page_content[:200],
            page=page,
        )


# Module-level singleton — created at import time, initialized at startup
def _create_default() -> RAGService:
    from app.config import settings
    return RAGService(settings=settings)

rag_service = _create_default()
