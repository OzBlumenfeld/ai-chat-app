# Application Architecture

## High-Level Stack
- **FastAPI** serves as the HTTP/API layer, wiring together authentication, document management, RAG queries, and request history endpoints. `main.py` wires routers, applies CORS, and drives the async lifespan hooks that prepare the database, RAG service, and document service before accepting traffic.
- **PostgreSQL** (via SQLAlchemy/Alembic) stores users, documents, and a log of every `/query` request. Documents and requests are scoped by user ID so each caller only sees their own data.
- **ChromaDB** acts as the vector store, with a separate collection per user (`user_{user_id}`). A local file store keeps the original blobs so they can be re-read if needed.
- **LangChain + LangChain Community adapters** orchestrate embeddings, vector stores, and LLM chains. HuggingFace embeddings convert document chunks and user queries into vectors, while either Ollama or Google Gemini supplies the chat model depending on `LLM_MODE`.
- **LLM (Ollama/Gemini)** is always invoked through LangChain chat prompts. The choice is governed by `LLM_MODE`: "gemini" uses `ChatGoogleGenerativeAI`, otherwise `ChatOllama` pointing at the `OLLAMA_BASE_URL` and configured model name.

## Document Ingestion Pipeline
1. **Upload handling (`/documents/upload`)**: Each file passes through `DocumentService.validate_file`, which checks the extension, size, and presence of a filename before processing.
2. **File storage**: `FileStorageService.save` writes every upload under `FILE_STORAGE_ROOT/<category>/<user_id>/` with a UUID-prefixed filename so there are no collisions even for identically named files.
3. **Document metadata**: A `Document` row is inserted with the original filename, user ID, collection name, and processing status (`processing`, `ready`, or `failed`). This row is used for listing, delete, and audit.
4. **Content extraction**: PDFs go through `PyPDFLoader`, while plain text files are decoded directly. The loader artifacts are split into chunks via `RecursiveCharacterTextSplitter` (1,500 char chunks with 300 char overlap) to keep chunks manageable.
5. **Embedding & storage**: Each chunk receives metadata (`doc_id`, `filename`, normalized `source`) before `Chroma.from_documents` stores them in the user-specific collection. Chunk IDs combine the document ID and chunk index so they are deterministic and unique per upload.
6. **Finalization**: The document row is updated with file size, chunk count, and `ready` status once ingestion succeeds; failures mark the status `failed` with a logged error.

## RAG Query Pipeline
1. **Query endpoint (`/query`)**: Authenticated users submit `question` (and optionally `history`). The route logs each request in the `requests` table and enforces rate limits.
2. **Vector search**: `RAGService.query` builds the LangChain history, selects the user collection (`user_{user_id}`), and runs `similarity_search_with_score(question, k=4)`.
3. **Threshold gating**: Only documents with a cosine score below `SIMILARITY_THRESHOLD` are considered relevant. If any exist:
   - The page contents of those chunks are concatenated into `context`.
   - `_rag_chain` runs a system prompt that instructs the LLM to answer purely from the given context (no hallucination) before invoking `ainvoke` on the configured chat model.
   - Retrieved chunks are summarized into `SourceInfo` records for the `/query` response.
4. **LLM fallback**: When no chunk passes the threshold (or the collection is empty), the service skips retrieval and runs `_direct_chain`, which uses a single system prompt (`"You are a helpful assistant."`) directly on the LLM with the raw question and history.
5. **Response metadata**: The response payload includes `source: "rag"` when retrieval helped and `source: "llm"` when the LLM answered without context, along with any citations captured earlier.

## LLM Usage and Control Flow
- **Initialization** (`RAGService.initialize`): Sets up HuggingFace embeddings, connects to Chroma, and instantiates either `ChatOllama` or `ChatGoogleGenerativeAI` (Gemini). Two runnable chains share the same LLM but use different prompts/outputs:
  - `_rag_chain` is `rag_prompt | llm | StrOutputParser`. The prompt enforces grounding in the supplied documents.
  - `_direct_chain` omits the context to let the LLM answer from general knowledge.
- **History handling**: `RAGService._build_history` converts stored history entries into LangChain `HumanMessage`/`AIMessage` objects so threading/prompting keeps conversational continuity.
- **When the LLM runs**:
  - With a relevant document context (score under threshold) the chain includes the RAG system prompt and context text.
  - Without relevant documents the chain runs the simpler direct prompt, still passing through history for conversational coherence.

## Document Storage Semantics & Deduplication
- Every upload, even if identical to a previous one, creates a new `Document` record, saves the file under `FILE_STORAGE_ROOT`, and pushes fresh chunks to Chroma. There is no automatic deduplication or hash comparison in the current pipeline, so duplicates accumulate unless you implement a custom check before ingestion.
- Chunk IDs and metadata intentionally include the database document ID to maintain one-to-many relationships between uploads and vectors. This lets deletion remove only the vectors introduced by that upload (see `DocumentService.delete_document`).
- To avoid repeated ingestion of identical content you can:
  1. Add your own pre-ingest dedup check (e.g., compute a hash of the file bytes and skip if the same hash already exists for the user).
  2. Compare the list from `/documents` (by filename, size, or chunk count) before uploading new files.
  3. Extend `Document`/Chroma logic to enforce a unique constraint or maintain a manifest table of expected hashes/filenames.

## Operational Notes
- **Docker mode**: When `LLM_MODE` is set to `docker`, `DockerManager` spins up the compose project before initialization (useful if you want a reproducible Ollama/Chroma stack). Otherwise, you must run `ollama serve` manually and ensure Chroma/DB services are available.
- **Testing & code structure**: Services expose abstract interfaces (`AbstractRAGService`, `AbstractDocumentService`, `AbstractFileStorageService`), making it easier to swap implementations in tests. Business logic lives in `app/services`, while HTTP glue lives in `app/routes` as per the project guide.
