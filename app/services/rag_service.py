import asyncio
import logging
from uuid import UUID

from langchain_postgres import PGVector
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.runnables import Runnable
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import Settings
from app.services.interfaces import AbstractRAGService, SourceInfo

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


class RAGService(AbstractRAGService):
    """Concrete RAG service backed by pgvector, HuggingFace embeddings, and Ollama or Gemini."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pgvector_connection: str | None = None
        self._embeddings: HuggingFaceEmbeddings | None = None
        self._llm: BaseChatModel | None = None
        self._rag_chain: Runnable | None = None
        self._direct_chain: Runnable | None = None
        self._mcp_client: MultiServerMCPClient | None = None

    @property
    def is_ready(self) -> bool:
        return self._pgvector_connection is not None and self._llm is not None

    async def initialize(self) -> None:
        """Called once during app startup."""
        logger.info("Initializing RAG chain")

        logger.info("Loading embedding model", extra={"model": self._settings.EMBEDDING_MODEL_NAME})
        self._embeddings = HuggingFaceEmbeddings(
            model_name=self._settings.EMBEDDING_MODEL_NAME
        )

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

# --- MCP INTEGRATION START ---
        logger.info("Connecting to MCP Server via SSE")
        mcp_tools = [] # Initialize as empty list
        try:
            self._mcp_client = MultiServerMCPClient({
                "assistant": {
                    "url": "http://127.0.0.1:9005/sse",
                    "transport": "sse"
                }
            })
            mcp_tools = await self._mcp_client.get_tools()
            logger.info("Successfully loaded tools from MCP", extra={"tools_count" : len(mcp_tools), "tools": [t.name for t in mcp_tools]})
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}. Proceeding without tools.")
        # --- MCP INTEGRATION END ---

        # 2. Define the Agent Prompts
        rag_prompt = ChatPromptTemplate.from_messages([
            ("system", _RAG_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", "{question}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        direct_prompt = ChatPromptTemplate.from_messages([
            ("system", _DIRECT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", "{question}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 3. Create the Agents
        # By passing mcp_tools (even if empty), the agent won't crash
        rag_agent_runnable = create_tool_calling_agent(self._llm, mcp_tools, rag_prompt)
        direct_agent_runnable = create_tool_calling_agent(self._llm, mcp_tools, direct_prompt)

        # 4. Wrap in Executors
        self._rag_executor = AgentExecutor(agent=rag_agent_runnable, tools=mcp_tools, verbose=True)
        self._direct_executor = AgentExecutor(agent=direct_agent_runnable, tools=mcp_tools, verbose=True)

        logger.info("RAG Agent Executor initialized successfully")


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
        docs_with_scores = await asyncio.to_thread(
            vectorstore.similarity_search_with_score, question, k=8
        )
        # Filter by similarity threshold but keep at least the top result to avoid
        # incorrectly falling back to LLM when documents exist but score is borderline.
        relevant_docs = [
            (doc, score)
            for doc, score in docs_with_scores
            if score < self._settings.SIMILARITY_THRESHOLD
        ]
        if not relevant_docs and docs_with_scores:
            relevant_docs = [docs_with_scores[0]]

        if relevant_docs:
            context = "\n\n".join(doc.page_content for doc, _ in relevant_docs)

            result = await self._rag_executor.ainvoke({
                "question": question,
                "context": context,
                "history": history_msgs
            })

            answer = result["output"]
            sources = [self._make_source(doc) for doc, _ in relevant_docs]
            return answer, "rag", sources

        # Fallback to direct executor
        result = await self._direct_executor.ainvoke({
            "question": question,
            "history": history_msgs
        })

        return result["output"], "llm", []


    def _get_user_vectorstore(self, user_id: UUID) -> PGVector:
        """Get a vectorstore scoped to the user's collection."""
        return PGVector(
            embeddings=self._embeddings,
            collection_name=f"user_{user_id}",
            connection=self._pgvector_connection,
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
