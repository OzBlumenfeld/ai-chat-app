import logging
from uuid import UUID

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

from app.config import Settings  # used for type hint in __init__
from app.services.interfaces import AbstractRAGService

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """You are a helpful assistant who answers questions based on the provided context.
If you don't know the answer, just say that you don't know. Don't try to make up an answer.

Context:
{context}

Question:
{question}

Answer:"""


class RAGService(AbstractRAGService):
    """Concrete RAG service backed by ChromaDB, HuggingFace embeddings, and Ollama or Gemini."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._chroma_client: chromadb.ClientAPI | None = None
        self._embeddings: HuggingFaceEmbeddings | None = None
        self._llm: BaseLanguageModel | None = None
        self._rag_chain: Runnable | None = None

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
            self._llm = OllamaLLM(
                model=self._settings.LLM_MODEL_NAME,
                base_url=self._settings.OLLAMA_BASE_URL,
            )
        logger.info("LLM loaded successfully")

        prompt = PromptTemplate.from_template(_PROMPT_TEMPLATE)
        self._rag_chain = prompt | self._llm | StrOutputParser()
        logger.info("RAG chain initialized successfully")

    async def query(self, question: str, user_id: UUID) -> tuple[str, str]:
        """
        Run similarity search + RAG chain or LLM fallback.
        Returns (answer, source) where source is "rag" or "llm".
        """
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
                {"context": context, "question": question}
            )
            return answer, "rag"

        if docs_with_scores:
            best_score = min(score for _, score in docs_with_scores)
            logger.debug(
                "No relevant documents above threshold, using LLM directly",
                extra={"best_score": round(best_score, 3), "threshold": self._settings.SIMILARITY_THRESHOLD},
            )
        else:
            logger.debug("No documents in store, using LLM directly")

        answer = await self._llm.ainvoke(question)
        return answer, "llm"

    def _get_user_vectorstore(self, user_id: UUID) -> Chroma:
        """Get or create a vectorstore for a user's documents."""
        collection_name = f"user_{user_id}"
        return Chroma(
            client=self._chroma_client,
            collection_name=collection_name,
            embedding_function=self._embeddings,
        )


# Module-level singleton — created at import time, initialized at startup
def _create_default() -> RAGService:
    from app.config import settings
    return RAGService(settings=settings)

rag_service = _create_default()
