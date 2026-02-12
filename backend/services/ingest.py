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
        self.batch_size = int(os.getenv("INGEST_BATCH_SIZE", "500"))
        self.use_upsert = os.getenv("INGEST_USE_UPSERT", "1") != "0"
    
    def fetch_and_sync(self, game: str, progress_callback=None):
        """
        Fetch game data and sync to ChromaDB in batches.
        
        Args:
            game: Game name
            progress_callback: Optional callback function(rows_fetched, total_rows) for progress tracking
        """
        if game not in DATASET_ENDPOINTS:
            raise ValueError(f"Game '{game}' not found in dataset endpoints. Available games: {list(DATASET_ENDPOINTS.keys())}")

        endpoints = DATASET_ENDPOINTS[game]
        total_rows_processed = 0
        column_names = []
        batch_size = self.batch_size

        collection_name = game
        # Use default embedding function to avoid dimension mismatch
        default_ef = embedding_functions.DefaultEmbeddingFunction()
        
        # Lazy import to avoid ChromaDB connection during module import
        from .chroma_client import chroma_client
        
        try:
            collection = chroma_client.client.get_or_create_collection(
                name=collection_name,
                embedding_function=default_ef
            )
            print(f"✓ Connected to collection '{collection_name}'")
        except Exception as conn_error:
            raise Exception(f"Failed to connect to ChromaDB collection '{collection_name}': {str(conn_error)}")

        # Estimate total rows for progress reporting, assuming 1000 per endpoint as a rough guess
        estimated_total_rows = len(endpoints) * 1000 

        for endpoint_idx, endpoint in enumerate(endpoints):
            success = False
            last_error = None
            
            print(f"[{game.upper()}] Endpoint {endpoint_idx + 1}/{len(endpoints)}: {endpoint}")
            
            for attempt in range(self.max_retries):
                try:
                    print(f"  Fetching from {endpoint} (attempt {attempt + 1}/{self.max_retries})...")
                    response = requests.get(endpoint, timeout=self.request_timeout)
                    response.raise_for_status()
                    
                    # Validate response content
                    if not response.content:
                        last_error = "Empty response received"
                        print(f"  ⚠ {last_error}")
                        break
                    
                    try:
                        data = response.json()
                    except ValueError as json_error:
                        last_error = f"Invalid JSON response: {str(json_error)}"
                        print(f"  ⚠ {last_error}")
                        print(f"  Response preview: {response.text[:200]}")
                        break
                    
                    if not column_names:
                        # Try to extract columns from Socrata metadata
                        columns_meta = data.get('meta', {}).get('view', {}).get('columns', [])
                        if columns_meta:
                            column_names = [col.get('fieldName', f'col_{idx}') for idx, col in enumerate(columns_meta)]
                            print(f"  ✓ Extracted {len(column_names)} column names from metadata")
                        else:
                            print(f"  ⚠ No column metadata found, will use generic names")

                    fetched_rows = data.get('data', [])
                    if not fetched_rows:
                        print(f"  ⚠ No data in this endpoint (empty 'data' array)")
                        success = True
                        break

                    print(f"  ✓ Fetched {len(fetched_rows)} rows. Processing in batches of {batch_size}...")

                    for j in range(0, len(fetched_rows), batch_size):
                        batch = fetched_rows[j:j + batch_size]
                        
                        try:
                            metadatas = []
                            for row_idx, row in enumerate(batch):
                                if not isinstance(row, list):
                                    print(f"  ⚠ Skipping row {j + row_idx}: not a list (type: {type(row)})")
                                    continue
                                metadata_item = {col_name: (str(value) if value is not None else "") for col_name, value in zip(column_names, row)} if column_names else {f"col_{idx}": str(val) for idx, val in enumerate(row)}
                                metadatas.append(metadata_item)
                            
                            documents = [str(item) for item in metadatas]
                            ids = [hashlib.md5(str(row).encode()).hexdigest() for row in batch]

                            if ids:
                                if self.use_upsert and hasattr(collection, "upsert"):
                                    collection.upsert(
                                        documents=documents,
                                        metadatas=metadatas,
                                        ids=ids
                                    )
                                else:
                                    collection.add(
                                        documents=documents,
                                        metadatas=metadatas,
                                        ids=ids
                                    )
                            
                            total_rows_processed += len(batch)
                            if progress_callback:
                                # Report progress based on estimated total
                                progress_callback(total_rows_processed, estimated_total_rows)
                        except Exception as batch_error:
                            print(f"  ⚠ Error processing batch {j}-{j+len(batch)}: {str(batch_error)}")
                            # Continue with next batch instead of failing completely
                            continue

                    print(f"  ✓ Processed and stored {len(fetched_rows)} rows from endpoint.")
                    success = True
                    break
                    
                except requests.Timeout:
                    last_error = f"Request timeout after {self.request_timeout}s"
                    print(f"  ⚠ {last_error}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                        
                except requests.RequestException as req_error:
                    last_error = f"Request error: {str(req_error)}"
                    print(f"  ⚠ {last_error}")
                    if hasattr(req_error, 'response') and req_error.response is not None:
                        print(f"  Response status: {req_error.response.status_code}")
                        print(f"  Response preview: {req_error.response.text[:200]}")
                    break
                except Exception as unexpected_error:
                    last_error = f"Unexpected error: {str(unexpected_error)}"
                    print(f"  ✗ {last_error}")
                    import traceback
                    traceback.print_exc()
                    break
            
            if not success and last_error:
                print(f"  ✗ Failed to fetch from endpoint: {last_error}")
                # Don't raise, just continue with next endpoint
                continue

        if total_rows_processed == 0:
            raise Exception(f"No data was successfully ingested for game '{game}'. Check backend logs for details.")
        
        print(f"✓ [{game.upper()}] Ingestion complete: {total_rows_processed} total rows processed")
        return {"status": "success", "added": total_rows_processed, "total": total_rows_processed}

ingest_service = IngestService()
