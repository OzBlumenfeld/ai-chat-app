import chromadb

from app.config import settings


def view_chroma_data():
    try:
        print(f"Connecting to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}...")
        chroma_client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        print("Successfully connected to ChromaDB.")

        print("\nListing all collections:")
        collections = chroma_client.list_collections()
        if not collections:
            print("No collections found in ChromaDB.")
            return

        for collection in collections:
            print(f"- {collection.name}")

        print(f"\nAttempting to view data from collection: '{settings.COLLECTION_NAME}'")
        try:
            collection = chroma_client.get_collection(name=settings.COLLECTION_NAME)
            print(f"Collection '{settings.COLLECTION_NAME}' contains {collection.count()} documents.")

            # Fetch and display the first 5 documents from the collection
            if collection.count() > 0:
                print("\nFirst 5 documents (or fewer if less than 5 exist):")
                sample_data = collection.peek(limit=5)
                for i, id_val in enumerate(sample_data['ids']):
                    print(f"--- Document {i+1} ---")
                    print(f"ID: {id_val}")
                    if sample_data['metadatas'] and sample_data['metadatas'][i]:
                        print(f"Metadata: {sample_data['metadatas'][i]}")
                    if sample_data['documents'] and sample_data['documents'][i]:
                        print(f"Content (truncated): {sample_data['documents'][i][:200]}...")
                    print("-" * 20)
            else:
                print(f"Collection '{settings.COLLECTION_NAME}' is empty.")

        except Exception as e:
            print(f"Error accessing collection '{settings.COLLECTION_NAME}': {e}")
            print(f"Please ensure the collection '{settings.COLLECTION_NAME}' exists or update the script with the correct collection name.")

    except Exception as e:
        print(f"Failed to connect to ChromaDB: {e}")
        print("Please ensure your ChromaDB server is running.")


if __name__ == "__main__":
    view_chroma_data()
