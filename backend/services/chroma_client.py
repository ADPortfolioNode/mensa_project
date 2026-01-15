import chromadb
from chromadb.config import Settings

class ChromaClient:
    def __init__(self):
        # The ChromaDB server is running on the 'chroma' service, at port 8000.
        self.client = chromadb.HttpClient(
            host="chroma", 
            port=8000, 
            settings=Settings(anonymized_telemetry=False)
        )

    def get_chroma_status(self):
        try:
            self.client.heartbeat()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_collections(self):
        return self.client.list_collections()

    def count_documents(self, collection_name: str) -> int:
        try:
            collection = self.client.get_collection(collection_name)
            return collection.count()
        except Exception as e:
            # Assuming an exception is thrown for non-existent collections.
            # This is a simplification; specific exceptions should be caught.
            print(f"Error counting documents for {collection_name}: {e}")
            return 0

chroma_client = ChromaClient()
