import chromadb
from chromadb.config import Settings
from config import settings
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import requests

class ChromaClient:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            # Lazy initialization - only connect when first accessed
            # chromadb.HttpClient expects a full host URL (including scheme).
            base = f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}"
            self._client = chromadb.HttpClient(
                host=base,
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client

    def get_chroma_status(self):
        try:
            self.client.heartbeat()
            return {"status": "ok"}
        except Exception as e:
            # Fallback: try a raw HTTP check to the Chroma pre-flight endpoint
            try:
                url = f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}/api/v1/pre-flight-checks"
                r = requests.get(url, timeout=3)
                if r.status_code == 200:
                    return {"status": "ok", "http_status": r.status_code}
                return {"status": "error", "message": f"http_status={r.status_code}", "body": r.text[:200]}
            except Exception as http_exc:
                return {"status": "error", "message": str(e), "http_error": str(http_exc)}

    def list_collections(self):
        return self.client.list_collections()

    def get_collection(self, collection_name: str):
        return self.client.get_collection(collection_name)

    def get_or_create_collection(self, collection_name: str):
        return self.client.get_or_create_collection(collection_name)

    def count_documents(self, collection_name: str) -> int:
        try:
            collection = self.client.get_collection(collection_name)
            return collection.count()
        except Exception as e:
            # Assuming an exception is thrown for non-existent collections.
            # This is a simplification; specific exceptions should be caught.
            print(f"Error counting documents for {collection_name}: {e}")
            return 0

    def get_collections_snapshot(self, collection_names: list[str], timeout_seconds: float = 2.5) -> list[dict]:
        def query_collection(name: str, record_index: int) -> dict:
            snapshot = {
                "name": name,
                "record_index": record_index,
                "count": 0,
                "metadata": {},
                "state": "ok",
            }
            try:
                collection = self.client.get_collection(name)
                snapshot["count"] = collection.count()
                snapshot["metadata"] = getattr(collection, "metadata", {}) or {}
            except Exception as exc:
                snapshot["state"] = "error"
                snapshot["error"] = str(exc)
            return snapshot

        if not collection_names:
            return []

        max_workers = min(max(len(collection_names), 1), 8)
        snapshots: list[dict] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(query_collection, name, idx + 1): (name, idx + 1)
                for idx, name in enumerate(collection_names)
            }

            for future, (name, record_index) in futures.items():
                try:
                    snapshots.append(future.result(timeout=timeout_seconds))
                except TimeoutError:
                    snapshots.append({
                        "name": name,
                        "record_index": record_index,
                        "count": 0,
                        "metadata": {},
                        "state": "timeout",
                        "error": "Collection query timed out",
                    })
                except Exception as exc:
                    snapshots.append({
                        "name": name,
                        "record_index": record_index,
                        "count": 0,
                        "metadata": {},
                        "state": "error",
                        "error": str(exc),
                    })

        snapshots.sort(key=lambda item: item.get("record_index", 0))
        return snapshots

chroma_client = ChromaClient()
