import requests
from .chroma_client import chroma_client
from config import DATASET_ENDPOINTS

class IngestService:
    def fetch_and_sync(self, game: str):
        if game not in DATASET_ENDPOINTS:
            raise ValueError(f"Game '{game}' not found in dataset endpoints.")

        endpoints = DATASET_ENDPOINTS[game]
        all_data = []
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint)
                response.raise_for_status()
                data = response.json()
                all_data.extend(data)
            except requests.RequestException as e:
                print(f"Error fetching data from {endpoint}: {e}")
                continue  # Continue to next endpoint if one fails

        if not all_data:
            return {"status": "error", "message": "No data fetched."}

        # In a real application, you would transform the data to a suitable format
        # and generate embeddings before adding to ChromaDB.
        # For this scaffold, we'll just add the raw data as metadata.
        
        collection_name = game
        collection = chroma_client.client.get_or_create_collection(collection_name)

        # Simple example: add documents with their draw numbers as IDs
        # This assumes the data has a 'draw_number' field.
        # You'll need to adapt this to the actual data structure.
        documents = [str(item) for item in all_data]
        metadatas = all_data
        ids = [str(item.get('draw_number', i)) for i, item in enumerate(all_data)]

        if ids:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            return {"status": "success", "added": len(ids)}
        else:
            return {"status": "success", "added": 0}

ingest_service = IngestService()
