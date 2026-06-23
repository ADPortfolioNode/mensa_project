"""
Manual ingestion queue management and worker.
"""
import threading
from collections import deque
from state.ingest_state import (
    manual_ingest_queue, 
    manual_ingest_worker_running, 
    manual_ingest_queue_lock,
    set_manual_ingest_state,
    get_manual_ingest_queue_size,
    enqueue_manual_ingest
)
from services.ingest import ingest_service


def _start_manual_ingest_worker_if_needed():
    """Start the manual ingestion worker if not already running."""
    global manual_ingest_worker_running

    def worker():
        global manual_ingest_worker_running
        try:
            while True:
                with manual_ingest_queue_lock:
                    if not manual_ingest_queue:
                        manual_ingest_worker_running = False
                        return
                    job = manual_ingest_queue.popleft()

                game_key = job.get("game")
                force = job.get("force", False)

                # Mark queued -> ingesting
                set_manual_ingest_state(game_key, {
                    "status": "ingesting",
                    "rows_fetched": 0,
                    "total_rows": 0,
                    "progress": 0,
                    "queued": False,
                })

                def progress_callback(rows_fetched, total_rows):
                    set_manual_ingest_state(game_key, {
                        "status": "ingesting",
                        "rows_fetched": rows_fetched,
                        "total_rows": total_rows,
                        "progress": (rows_fetched / total_rows * 100) if total_rows > 0 else 0,
                    })

                try:
                    print(f"📥 [QUEUE] Starting ingest for {game_key}")
                    result = ingest_service.fetch_and_sync(
                        game_key,
                        progress_callback=progress_callback,
                        force=force,
                    )

                    set_manual_ingest_state(game_key, {
                        "status": "completed",
                        "rows_fetched": result.get("total", 0),
                        "total_rows": result.get("total", 0),
                        "progress": 100,
                        "added": result.get("added", 0),
                    })
                    print(f"✅ [QUEUE] Completed ingest for {game_key}")
                except Exception as exc:
                    set_manual_ingest_state(game_key, {
                        "status": "error",
                        "error": str(exc),
                    })
                    print(f"❌ [QUEUE] Ingest failed for {game_key}: {exc}")

        except Exception:
            manual_ingest_worker_running = False
            raise

    with manual_ingest_queue_lock:
        if manual_ingest_worker_running:
            return
        manual_ingest_worker_running = True
    thread = threading.Thread(target=worker, daemon=True, name="ManualIngestWorker")
    thread.start()