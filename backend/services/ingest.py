import requests
import hashlib
import time
from .chroma_client import chroma_client
from config import DATASET_ENDPOINTS

class IngestService:
    def __init__(self):
        self.request_timeout = 30  # 30 second timeout per request
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def fetch_and_sync(self, game: str):
        if game not in DATASET_ENDPOINTS:
            raise ValueError(f"Game '{game}' not found in dataset endpoints.")

        endpoints = DATASET_ENDPOINTS[game]
        all_rows = []
        column_names = []

        for endpoint in endpoints:
            success = False
            last_error = None
            
            # Retry logic with exponential backoff
            for attempt in range(self.max_retries):
                try:
                    print(f"  Fetching from {endpoint} (attempt {attempt + 1}/{self.max_retries})...")
                    
                    # Add timeout to prevent hanging requests
                    response = requests.get(endpoint, timeout=self.request_timeout)
                    response.raise_for_status()
                    data = response.json()
                    
                    if not column_names:
                        column_names = [col['fieldName'] for col in data.get('meta', {}).get('view', {}).get('columns', [])]

                    all_rows.extend(data.get('data', []))
                    print(f"  ✓ Successfully fetched {len(data.get('data', []))} rows from endpoint")
                    success = True
                    break
                    
                except requests.Timeout:
                    last_error = f"Request timeout after {self.request_timeout}s"
                    print(f"  ⚠ {last_error}")
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        print(f"  Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        
                except requests.ConnectionError as e:
                    last_error = f"Connection error: {str(e)}"
                    print(f"  ⚠ {last_error}")
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        print(f"  Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        
                except requests.RequestException as e:
                    last_error = f"Request error: {str(e)}"
                    print(f"  ⚠ {last_error}")
                    break  # Don't retry for other request errors
            
            if not success and last_error:
                print(f"  ✗ Failed to fetch from endpoint: {last_error}")
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

