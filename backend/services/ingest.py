import requests
import hashlib
import time
import signal
from functools import wraps
from config import DATASET_ENDPOINTS
from chromadb.utils import embedding_functions

class TimeoutError(Exception):
    """Raised when an operation exceeds the time limit."""
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def with_timeout(seconds):
    """Decorator to add a timeout to a function (Unix/Linux only, will pass on Windows)."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # On Windows, signal.SIGALRM is not available; just run normally
            if not hasattr(signal, 'SIGALRM'):
                return func(*args, **kwargs)
            
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)  # Cancel alarm
                signal.signal(signal.SIGALRM, old_handler)
            return result
        return wrapper
    return decorator

class IngestService:
    def __init__(self):
        self.request_timeout = 30  # 30 second timeout per request
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def fetch_and_sync(self, game: str, progress_callback=None):
        """
        Fetch game data and sync to ChromaDB in batches.
        
        Args:
            game: Game name
            progress_callback: Optional callback function(rows_fetched, total_rows) for progress tracking
        """
        if game not in DATASET_ENDPOINTS:
            raise ValueError(f"Game '{game}' not found in dataset endpoints.")

        endpoints = DATASET_ENDPOINTS[game]
        total_rows_processed = 0
        column_names = []
        batch_size = 500  # Process 500 records at a time

        collection_name = game
        # Use default embedding function to avoid dimension mismatch
        default_ef = embedding_functions.DefaultEmbeddingFunction()
        
        # Lazy import to avoid ChromaDB connection during module import
        from .chroma_client import chroma_client
        
        collection = chroma_client.client.get_or_create_collection(
            name=collection_name,
            embedding_function=default_ef
        )

        # Estimate total rows for progress reporting, assuming 1000 per endpoint as a rough guess
        estimated_total_rows = len(endpoints) * 1000 

        for i, endpoint in enumerate(endpoints):
            success = False
            last_error = None
            
            for attempt in range(self.max_retries):
                try:
                    print(f"  Fetching from {endpoint} (attempt {attempt + 1}/{self.max_retries})...")
                    response = requests.get(endpoint, timeout=self.request_timeout)
                    response.raise_for_status()
                    data = response.json()
                    
                    if not column_names:
                        # Try to extract columns from Socrata metadata
                        columns_meta = data.get('meta', {}).get('view', {}).get('columns', [])
                        if columns_meta:
                            column_names = [col.get('fieldName', f'col_{idx}') for idx, col in enumerate(columns_meta)]

                    fetched_rows = data.get('data', [])
                    if not fetched_rows:
                        print("  No data in this endpoint.")
                        success = True
                        break

                    print(f"  ✓ Fetched {len(fetched_rows)} rows. Processing in batches...")

                    for j in range(0, len(fetched_rows), batch_size):
                        batch = fetched_rows[j:j + batch_size]
                        
                        metadatas = []
                        for row in batch:
                            metadata_item = {col_name: (value if value is not None else "") for col_name, value in zip(column_names, row)}
                            metadatas.append(metadata_item)
                        
                        documents = [str(item) for item in metadatas]
                        ids = [hashlib.md5(str(row).encode()).hexdigest() for row in batch]

                        if ids:
                            collection.add(
                                documents=documents,
                                metadatas=metadatas,
                                ids=ids
                            )
                        
                        total_rows_processed += len(batch)
                        if progress_callback:
                            # Report progress based on estimated total
                            progress_callback(total_rows_processed, estimated_total_rows)

                    print(f"  ✓ Processed and stored {len(fetched_rows)} rows from endpoint.")
                    success = True
                    break
                    
                except requests.Timeout:
                    last_error = f"Request timeout after {self.request_timeout}s"
                    print(f"  ⚠ {last_error}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                        
                except requests.RequestException as e:
                    last_error = f"Request error: {str(e)}"
                    print(f"  ⚠ {last_error}")
                    break
            
            if not success and last_error:
                print(f"  ✗ Failed to fetch from endpoint: {last_error}")
                continue

        return {"status": "success", "added": total_rows_processed}

ingest_service = IngestService()
