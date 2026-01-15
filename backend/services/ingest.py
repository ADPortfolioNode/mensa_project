import requests
import hashlib
from .chroma_client import chroma_client
from config import DATASET_ENDPOINTS

class IngestService:
    def fetch_and_sync(self, game: str):
        if game not in DATASET_ENDPOINTS:
            raise ValueError(f"Game '{game}' not found in dataset endpoints.")

        endpoints = DATASET_ENDPOINTS[game]
        all_rows = []
        column_names = []

        for endpoint in endpoints:
            try:
                response = requests.get(endpoint)
                response.raise_for_status()
                data = response.json()
                
                if not column_names:
                    column_names = [col['fieldName'] for col in data.get('meta', {}).get('view', {}).get('columns', [])]

                all_rows.extend(data.get('data', []))

            except requests.RequestException as e:
                print(f"Error fetching data from {endpoint}: {e}")
                continue

        if not all_rows:
            return {"status": "error", "message": "No data fetched."}
        
        if not column_names:
            return {"status": "error", "message": "Could not determine column names from data source."}

        collection_name = game
        collection = chroma_client.client.get_or_create_collection(collection_name)

        metadatas = []
        for row in all_rows:
            metadata_item = {}
            for col_name, value in zip(column_names, row):
                # Convert None to an empty string to ensure metadata values are valid types
                metadata_item[col_name] = value if value is not None else "" 
            metadatas.append(metadata_item)
        documents = [str(item) for item in metadatas]
        
        # Generate a unique ID based on the content of the row
        ids = [hashlib.md5(str(row).encode()).hexdigest() for row in all_rows]

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
