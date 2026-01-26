import chromadb
from chromadb.config import Settings
from config import settings

class ChromaClient:
    def __init__(self):
        # Use REST (v2) client with explicit tenant/database to avoid deprecated v1 paths
        self.client = chromadb.Client(Settings(
            chroma_api_impl="rest",
            chroma_server_host=settings.CHROMA_HOST,
            chroma_server_http_port=settings.CHROMA_PORT,
            tenant="default_tenant",
            database="default_database",
        ))

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
