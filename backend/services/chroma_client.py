import chromadb
from config import settings

class ChromaClient:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            # Lazy initialization - only connect when first accessed
            self._client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
            )
        return self._client

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
