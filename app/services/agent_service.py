import asyncio
import logging
from typing import Any
from uuid import UUID

import httpx
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langchain_postgres import PGVector

from app.config import Settings
from app.services.interfaces import AbstractAgentOrchestrationService, SourceInfo
from app.services.tool_utils import patch_tools_for_ollama

logger = logging.getLogger(__name__)

_RAG_SYSTEM_PROMPT = """You are a helpful assistant who answers questions based on the provided context.
If the answer is not in the context, say that you don't know based on the available documents.
Do not make up information.

Context from documents:
{context}

You have access to tools for math and email.
When a tool returns a result, just inform the user of that result concisely.
DO NOT mention or call any tools that are not explicitly provided to you (e.g., do NOT mention 'get_email_body').
"""

_DIRECT_SYSTEM_PROMPT = """You are a helpful assistant.
You have access to tools for math and email.
When a tool returns a result, just inform the user of that result concisely.
DO NOT mention or call any tools that are not explicitly provided to you (e.g., do NOT mention 'get_email_body').
"""

# Simplified prompts used when the model does not support tool calling.
_RAG_SYSTEM_PROMPT_NOTOOL = """You are a helpful assistant who answers questions based on the provided context.
If the answer is not in the context, say that you don't know based on the available documents.
Do not make up information.

Context from documents:
{context}
"""

_DIRECT_SYSTEM_PROMPT_NOTOOL = """You are a helpful assistant."""


class AgentOrchestrationService(AbstractAgentOrchestrationService):
    """Orchestrates AI query execution across three modes:

    - RAG: retrieves relevant document chunks from pgvector and injects them as context.
    - Tool-calling agent: invokes MCP tools when the active model supports it.
    - Direct LLM: falls back to plain LLM when no relevant documents are found.

    Manages the full lifecycle of embeddings, LLM, vectorstore, and MCP client.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pgvector_connection: str | None = None
        self._embeddings: HuggingFaceEmbeddings | None = None
        self._llm: BaseChatModel | None = None
        self._rag_executor: Runnable[Any, Any] | None = None
        self._direct_executor: Runnable[Any, Any] | None = None
        self._mcp_client: MultiServerMCPClient | None = None
        self._model_supports_tools: bool = False

    @property
    def is_ready(self) -> bool:
        return self._pgvector_connection is not None and self._llm is not None

    async def initialize(self) -> None:
        """Load all AI components during app startup.

        Sequence: HuggingFace embeddings → pgvector connection → LLM (Gemini or Ollama)
        → tool-support check → MCP client + tools → executor selection (agent or plain chain).
        """
        logger.info("Initializing agent orchestration service")

        logger.info("Loading embedding model", extra={"model": self._settings.EMBEDDING_MODEL_NAME})
        self._embeddings = HuggingFaceEmbeddings(model_name=self._settings.EMBEDDING_MODEL_NAME)

        logger.info("Connecting to pgvector")
        self._pgvector_connection = self._settings.pgvector_connection_string
        logger.info("pgvector connection configured")

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

        self._model_supports_tools = await self._check_model_supports_tools()

        mcp_tools: list[BaseTool] = []
        if self._model_supports_tools:
            logger.info("Connecting to MCP Server via SSE")
            try:
                self._mcp_client = MultiServerMCPClient(
                    {
                        "assistant": {
                            "transport": "sse",
                            "url": self._settings.MCP_SERVER_URL,
                        }
                    }
                )
                mcp_tools = await self._mcp_client.get_tools()
                patch_tools_for_ollama(mcp_tools)
                logger.info(
                    "Successfully loaded tools from MCP",   
                    extra={"tools_count": len(mcp_tools), "tools": [t.name for t in mcp_tools]},
                )
            except Exception as e:
                logger.error(f"Failed to load MCP tools: {e}. Proceeding without tools.")

        if self._model_supports_tools and mcp_tools:
            self._rag_executor, self._direct_executor = self._build_agent_executors(mcp_tools)
            logger.info("RAG Agent Executor initialized successfully")
        else:
            self._rag_executor, self._direct_executor = self._build_plain_chains()
            logger.info("RAG plain chains initialized (model does not support tool calling)")

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

        # Fire both vector searches concurrently using native async methods — no
        # asyncio.to_thread needed since PGVector exposes proper async variants.
        # MMR fetches diverse chunks; similarity_search_with_score provides the
        # threshold score used to detect off-topic collections.
        mmr_docs, scored = await asyncio.gather(
            vectorstore.amax_marginal_relevance_search(question, k=8, fetch_k=30),
            vectorstore.asimilarity_search_with_score(question, k=1),
        )

        if mmr_docs:
            best_score = scored[0][1] if scored else 0.0
            relevant_docs = mmr_docs if best_score < self._settings.SIMILARITY_THRESHOLD else []
        else:
            relevant_docs = []

        if relevant_docs:
            context = "\n\n".join(doc.page_content for doc in relevant_docs)
            raw = await self._rag_executor.ainvoke(  # type: ignore[union-attr]
                {"question": question, "context": context, "history": history_msgs}
            )
            answer = raw["output"] if isinstance(raw, dict) else raw
            sources = [self._make_source(doc) for doc in relevant_docs]
            return answer, "rag", sources

        raw = await self._direct_executor.ainvoke(  # type: ignore[union-attr]
            {"question": question, "history": history_msgs}
        )
        answer = raw["output"] if isinstance(raw, dict) else raw
        return answer, "llm", []

    async def _check_model_supports_tools(self) -> bool:
        """Return True if the active LLM supports tool calling.

        Gemini always supports tools. For Ollama, the /api/show endpoint
        exposes a 'capabilities' list that includes 'tools' when supported.
        """
        if self._settings.LLM_MODE == "gemini":
            return True

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._settings.OLLAMA_BASE_URL}/api/show",
                    json={"name": self._settings.LLM_MODEL_NAME},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    capabilities: list[str] = response.json().get("capabilities", [])
                    supported = "tools" in capabilities
                    logger.info(
                        "Ollama tool support check",
                        extra={
                            "model": self._settings.LLM_MODEL_NAME,
                            "supports_tools": supported,
                        },
                    )
                    return supported
        except Exception as e:
            logger.warning(f"Could not determine model tool support: {e}. Defaulting to no tools.")

        return False

    def _build_agent_executors(
        self, tools: list[BaseTool]
    ) -> tuple[AgentExecutor, AgentExecutor]:
        """Build tool-calling AgentExecutors for the RAG and direct paths."""
        rag_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _RAG_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", "{question}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        direct_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _DIRECT_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", "{question}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        rag_executor = AgentExecutor(
            agent=create_tool_calling_agent(self._llm, tools, rag_prompt),  # type: ignore[arg-type]
            tools=tools,
            verbose=True,
        )
        direct_executor = AgentExecutor(
            agent=create_tool_calling_agent(self._llm, tools, direct_prompt),  # type: ignore[arg-type]
            tools=tools,
            verbose=True,
        )
        return rag_executor, direct_executor

    def _build_plain_chains(
        self,
    ) -> tuple[Runnable[Any, Any], Runnable[Any, Any]]:
        """Build simple LLM chains for models that do not support tool calling."""
        rag_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _RAG_SYSTEM_PROMPT_NOTOOL),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", "{question}"),
            ]
        )
        direct_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _DIRECT_SYSTEM_PROMPT_NOTOOL),
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", "{question}"),
            ]
        )
        parser = StrOutputParser()
        return rag_prompt | self._llm | parser, direct_prompt | self._llm | parser  # type: ignore[operator]

    def _get_user_vectorstore(self, user_id: UUID) -> PGVector:
        """Get a vectorstore scoped to the user's collection."""
        return PGVector(
            embeddings=self._embeddings,
            collection_name=f"user_{user_id}",
            connection=self._pgvector_connection,
            async_mode=True,
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
