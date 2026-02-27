import os

import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.config import settings

DOCS_DIR = "docs"


def main():
    """
    Main function to ingest PDF documents into the ChromaDB vector store.
    """
    print("Starting ingestion process...")

    # 1. Load Documents
    documents = []
    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".pdf"):
            filepath = os.path.join(DOCS_DIR, filename)
            try:
                loader = PyPDFLoader(filepath)
                documents.extend(loader.load())
                print(f"Successfully loaded '{filename}'")
            except Exception as e:
                print(f"Error loading '{filename}': {e}")

    if not documents:
        print("No PDF documents found in the 'docs' directory. Exiting.")
        return

    # 2. Split Documents into Chunks with Unique IDs
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    # Generate unique IDs for each chunk based on filename + index
    splits = []
    for doc in documents:
        filename = os.path.basename(doc.metadata.get("source", "unknown"))
        doc_splits = text_splitter.split_documents([doc])
        for idx, split in enumerate(doc_splits):
            split.metadata["doc_id"] = f"{filename}_{idx}"
            splits.append(split)

    print(f"Created {len(splits)} text chunks.")

    # 3. Initialize Embedding Model
    print(f"Initializing embedding model: '{settings.EMBEDDING_MODEL_NAME}'...")
    embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)

    # 4. Initialize ChromaDB Client
    print(f"Connecting to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}...")
    chroma_client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)

    # 5. Clean existing collection
    print("Cleaning existing collection...")
    try:
        chroma_client.delete_collection(settings.COLLECTION_NAME)
        print(f"Deleted existing '{settings.COLLECTION_NAME}' collection.")
    except Exception as e:
        print(f"No existing collection to delete or error: {e}")

    # 6. Create and Persist Vector Store
    print("Creating and persisting vector store in ChromaDB...")

    Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        client=chroma_client,
        collection_name=settings.COLLECTION_NAME,
        ids=[doc.metadata["doc_id"] for doc in splits],
    )

    print(f"Successfully ingested {len(splits)} chunks into the '{settings.COLLECTION_NAME}' collection.")
    print("Ingestion process complete.")


if __name__ == "__main__":
    main()
