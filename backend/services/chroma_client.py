import chromadb

class ChromaClient:
    def __init__(self):
        # The ChromaDB server is running on the 'chroma' service, at port 8000.
        self.client = chromadb.HttpClient(host="chroma", port=8000)

    def get_chroma_status(self):
        try:
            self.client.heartbeat()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_collections(self):
        return self.client.list_collections()

    def count_documents(self, collection_name: str) -> int:
        collection = self.client.get_collection(collection_name)
        return collection.count()

chroma_client = ChromaClient()
