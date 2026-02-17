import requests
import hashlib
import time
import signal
import os
import re
from functools import wraps
from config import DATASET_ENDPOINTS, GAME_TITLES, GAME_ALIASES, resolve_game_key
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
        self.request_timeout = int(os.getenv("INGEST_REQUEST_TIMEOUT", "20"))
        self.max_retries = int(os.getenv("INGEST_MAX_RETRIES", "2"))
        self.retry_delay = int(os.getenv("INGEST_RETRY_DELAY", "1"))
        self.batch_size = int(os.getenv("INGEST_BATCH_SIZE", "4000"))
        self.use_upsert = os.getenv("INGEST_USE_UPSERT", "1") != "0"
        self.enable_catalog_fallback = os.getenv("INGEST_ENABLE_CATALOG_FALLBACK", "1") == "1"
        self.fallback_on_empty = os.getenv("INGEST_FALLBACK_ON_EMPTY", "1") == "1"
        self.max_catalog_candidates = int(os.getenv("INGEST_MAX_CATALOG_CANDIDATES", "3"))
        self.socrata_catalog_url = os.getenv("SOCRATA_CATALOG_URL", "https://api.us.socrata.com/api/catalog/v1")
        self.socrata_domain = os.getenv("SOCRATA_DOMAIN", "data.ny.gov")
        self.game_search_hints = {
            key: f"new york {GAME_TITLES.get(key, key)} lottery"
            for key in DATASET_ENDPOINTS.keys()
        }

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()

    def _extract_rows_and_columns(self, data):
        """Normalize Socrata responses to (rows, column_names) for ingestion."""
        if isinstance(data, dict):
            rows = data.get("data")
            if isinstance(rows, list):
                columns_meta = data.get("meta", {}).get("view", {}).get("columns", [])
                column_names = [col.get("fieldName", f"col_{idx}") for idx, col in enumerate(columns_meta)]
                return rows, column_names

            # Fallback for flat-object payloads where records are under common keys
            for key in ("results", "records", "rows"):
                candidate = data.get(key)
                if isinstance(candidate, list):
                    if candidate and isinstance(candidate[0], dict):
                        all_keys = set()
                        for item in candidate:
                            all_keys.update(item.keys())
                        return candidate, list(all_keys)
                    return candidate, []

        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                all_keys = set()
                for item in data:
                    all_keys.update(item.keys())
                return data, list(all_keys)
            return data, []

        return [], []

    def _fetch_catalog_endpoints(self, game: str):
        """Discover fallback dataset endpoints from Socrata catalog for a game."""
        if not self.enable_catalog_fallback:
            return []

        hint = self.game_search_hints.get(game, GAME_TITLES.get(game, game))
        query = hint

        try:
            response = requests.get(
                self.socrata_catalog_url,
                params={
                    "domains": self.socrata_domain,
                    "search_context": self.socrata_domain,
                    "q": query,
                    "limit": 20,
                },
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])
        except Exception as exc:
            print(f"⚠ Catalog lookup failed for {game}: {exc}")
            return []

        game_tokens = set(self._normalize_text(GAME_TITLES.get(game, game)).split())
        alias_tokens = {
            token
            for alias in GAME_ALIASES.get(game, [])
            for token in self._normalize_text(alias).split()
        }
        all_expected_tokens = {token for token in (game_tokens | alias_tokens) if token and token != "lottery"}
        ranked = []

        for item in results:
            resource = item.get("resource") or {}
            dataset_id = resource.get("id")
            if not dataset_id:
                continue

            name = self._normalize_text(resource.get("name", ""))
            description = self._normalize_text(resource.get("description", ""))
            combined = f"{name} {description}"

            score = 0
            if "lottery" in combined:
                score += 3
            token_hits = sum(1 for token in all_expected_tokens if token in combined)
            if token_hits > 0:
                score += min(token_hits, 4)
            compact_expected = self._normalize_text(GAME_TITLES.get(game, game)).replace(" ", "")
            if compact_expected and compact_expected in combined.replace(" ", ""):
                score += 5
            if "new york" in combined:
                score += 2

            # Skip unrelated catalog hits
            if score <= 0:
                continue

            endpoint = f"https://{self.socrata_domain}/api/views/{dataset_id}/rows.json?accessType=DOWNLOAD"
            ranked.append((score, endpoint, resource.get("name", dataset_id)))

        ranked.sort(key=lambda x: x[0], reverse=True)

        deduped_endpoints = []
        seen = set()
        for _, endpoint, title in ranked:
            if endpoint in seen:
                continue
            seen.add(endpoint)
            deduped_endpoints.append(endpoint)
            print(f"  ↳ Catalog candidate for {game}: {title} -> {endpoint}")

            if len(deduped_endpoints) >= self.max_catalog_candidates:
                break

        return deduped_endpoints

    def _resolve_game_endpoints(self, game: str):
        configured = DATASET_ENDPOINTS.get(game, [])

        # Fast path: use known configured datasets by default.
        # Catalog fallback is opt-in and primarily for recovery when configured endpoints are missing.
        if configured and not self.enable_catalog_fallback:
            return configured

        catalog_candidates = self._fetch_catalog_endpoints(game)

        if configured and not catalog_candidates:
            return configured

        ordered = []
        seen = set()
        for endpoint in configured + catalog_candidates:
            if endpoint in seen:
                continue
            seen.add(endpoint)
            ordered.append(endpoint)

        return ordered

    def _process_endpoints(self, game: str, endpoints: list[str], collection, column_names: list[str],
                           total_rows_processed: int, progress_callback=None):
        """Process a list of endpoints and return (rows_added, updated_column_names)."""
        batch_size = self.batch_size
        rows_before = total_rows_processed
        discovered_total_rows = 0

        for endpoint_idx, endpoint in enumerate(endpoints):
            success = False
            last_error = None

            print(f"[{game.upper()}] Endpoint {endpoint_idx + 1}/{len(endpoints)}: {endpoint}")

            for attempt in range(self.max_retries):
                try:
                    print(f"  Fetching from {endpoint} (attempt {attempt + 1}/{self.max_retries})...")
                    response = requests.get(endpoint, timeout=self.request_timeout)
                    response.raise_for_status()

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

                    fetched_rows, extracted_columns = self._extract_rows_and_columns(data)

                    if not column_names and extracted_columns:
                        column_names = extracted_columns
                        print(f"  ✓ Extracted {len(column_names)} column names from payload")
                    elif not column_names:
                        print(f"  ⚠ No column metadata found, will use generic names")

                    if not fetched_rows:
                        print(f"  ⚠ No data in this endpoint (empty 'data' array)")
                        success = True
                        break

                    discovered_total_rows += len(fetched_rows)
                    print(f"  ✓ Fetched {len(fetched_rows)} rows. Processing in batches of {batch_size}...")

                    for j in range(0, len(fetched_rows), batch_size):
                        batch = fetched_rows[j:j + batch_size]

                        try:
                            metadatas = []
                            ids = []
                            for row_idx, row in enumerate(batch):
                                if isinstance(row, dict):
                                    metadata_item = {
                                        key: (str(value) if value is not None else "")
                                        for key, value in row.items()
                                    }
                                elif isinstance(row, list):
                                    metadata_item = (
                                        {col_name: (str(value) if value is not None else "") for col_name, value in zip(column_names, row)}
                                        if column_names else
                                        {f"col_{idx}": (str(val) if val is not None else "") for idx, val in enumerate(row)}
                                    )
                                else:
                                    print(f"  ⚠ Skipping row {j + row_idx}: unsupported row type {type(row)}")
                                    continue
                                metadatas.append(metadata_item)
                                ids.append(hashlib.md5(str(row).encode()).hexdigest())

                            documents = [str(item) for item in metadatas]

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
                                total_for_progress = max(discovered_total_rows, total_rows_processed - rows_before, 1)
                                progress_callback(total_rows_processed, rows_before + total_for_progress)
                        except Exception as batch_error:
                            print(f"  ⚠ Error processing batch {j}-{j+len(batch)}: {str(batch_error)}")
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
                continue

        return total_rows_processed - rows_before, column_names
    
    def fetch_and_sync(self, game: str, progress_callback=None, force: bool = False):
        """
        Fetch game data and sync to ChromaDB in batches.
        
        Args:
            game: Game name
            progress_callback: Optional callback function(rows_fetched, total_rows) for progress tracking
        """
        game_key = resolve_game_key(game)
        if not game_key:
            raise ValueError(
                f"Unknown game '{game}'. Available configured games: {list(DATASET_ENDPOINTS.keys())}"
            )

        endpoints = self._resolve_game_endpoints(game_key)
        if not endpoints:
            raise ValueError(
                f"Game '{game_key}' endpoint not found in configured datasets or Socrata catalog. "
                f"Available configured games: {list(DATASET_ENDPOINTS.keys())}"
            )
        total_rows_processed = 0
        column_names = []

        collection_name = game_key
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

        existing_count = collection.count()
        if existing_count > 0 and not force:
            print(
                f"↷ [{game_key.upper()}] Skipping ingest: {existing_count} records already exist "
                f"(use force=True to reload)."
            )
            if progress_callback:
                progress_callback(existing_count, existing_count)
            return {
                "status": "success",
                "added": 0,
                "total": existing_count,
                "processed": 0,
                "skipped_existing": True,
            }

        rows_added, column_names = self._process_endpoints(
            game=game_key,
            endpoints=endpoints,
            collection=collection,
            column_names=column_names,
            total_rows_processed=total_rows_processed,
            progress_callback=progress_callback,
        )
        total_rows_processed += rows_added

        if rows_added == 0 and self.fallback_on_empty:
            print(f"⚠ [{game_key.upper()}] No rows from configured endpoints; trying catalog fallback candidates...")
            fallback_endpoints = self._fetch_catalog_endpoints(game_key)
            configured_set = set(endpoints)
            fallback_endpoints = [ep for ep in fallback_endpoints if ep not in configured_set]

            if fallback_endpoints:
                fallback_added, column_names = self._process_endpoints(
                    game=game_key,
                    endpoints=fallback_endpoints,
                    collection=collection,
                    column_names=column_names,
                    total_rows_processed=total_rows_processed,
                    progress_callback=progress_callback,
                )
                total_rows_processed += fallback_added

        if total_rows_processed == 0:
            raise Exception(f"No data was successfully ingested for game '{game_key}'. Check backend logs for details.")

        if progress_callback:
            progress_callback(total_rows_processed, total_rows_processed)
        
        final_total = collection.count()
        net_added = max(final_total - existing_count, 0)

        print(
            f"✓ [{game_key.upper()}] Ingestion complete: processed={total_rows_processed}, "
            f"net_added={net_added}, total={final_total}"
        )
        return {
            "status": "success",
            "added": net_added,
            "total": final_total,
            "processed": total_rows_processed,
            "skipped_existing": False,
        }

ingest_service = IngestService()
