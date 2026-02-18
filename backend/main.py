from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import time
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests

# Import services
from config import GAME_CONFIGS, GAME_TITLES, resolve_game_key
from services.gemini_client import gemini_client, LM_UNAVAILABLE_PREFIX
from services.chroma_client import chroma_client
from experiments.store import ExperimentStore
from services.ingest import ingest_service
from services.lm_router import lm_router
from services.rag_service import rag_service

# --- Global startup state tracking for initialization ---
startup_state = {
    "status": "ready",
    "progress": 0.0,
    "total": len(GAME_CONFIGS),
    "current_game": None,
    "current_task": None,
    "current_game_rows_fetched": 0,
    "current_game_rows_total": 0,
    "games": {game: {"status": "pending", "error": None} for game in GAME_CONFIGS.keys()},
    "started_at": None,
    "completed_at": None,
}

# Track manual ingestion progress globally
manual_ingest_state = {}

_ingestion_started = False


def _reset_startup_state_for_new_run():
    startup_state["status"] = "ready"
    startup_state["progress"] = 0.0
    startup_state["total"] = len(GAME_CONFIGS)
    startup_state["current_game"] = None
    startup_state["current_task"] = None
    startup_state["current_game_rows_fetched"] = 0
    startup_state["current_game_rows_total"] = 0
    startup_state["games"] = {game: {"status": "pending", "error": None} for game in GAME_CONFIGS.keys()}
    startup_state["started_at"] = None
    startup_state["completed_at"] = None

def start_background_ingestion():
    """Start non-blocking background ingestion in a daemon thread."""
    def ingest_all():
        global _ingestion_started
        startup_state["started_at"] = time.time()
        startup_state["status"] = "ingesting"

        for i, game in enumerate(GAME_CONFIGS.keys(), 1):
            try:
                startup_state["current_game"] = game
                startup_state["current_task"] = "fetching"
                startup_state["progress"] = float(i - 1)
                startup_state["current_game_rows_fetched"] = 0
                startup_state["current_game_rows_total"] = 0
                startup_state["games"][game]["status"] = "ingesting"
                startup_state["games"][game]["error"] = None

                def update_game_progress(rows_fetched, total_rows):
                    startup_state["current_game_rows_fetched"] = rows_fetched
                    startup_state["current_game_rows_total"] = total_rows
                    if total_rows and total_rows > 0:
                        fraction = rows_fetched / max(total_rows, 1)
                        fraction = max(0.0, min(1.0, fraction))
                        startup_state["progress"] = float(i - 1) + fraction
                    else:
                        startup_state["progress"] = float(i - 1)

                ingest_service.fetch_and_sync(game, progress_callback=update_game_progress)

                startup_state["games"][game]["status"] = "completed"
                startup_state["games"][game]["error"] = None
                startup_state["progress"] = float(i)
                startup_state["current_game_rows_fetched"] = 0
                startup_state["current_game_rows_total"] = 0

            except Exception as e:
                startup_state["games"][game]["status"] = "failed"
                startup_state["games"][game]["error"] = str(e)
                startup_state["progress"] = float(i)

        startup_state["status"] = "completed"
        startup_state["current_game"] = None
        startup_state["current_task"] = None
        startup_state["completed_at"] = time.time()
        _ingestion_started = False

    thread = threading.Thread(target=ingest_all, daemon=True, name="BackgroundIngestion")
    thread.start()

app = FastAPI()


@app.on_event("startup")
async def audit_lm_connections_on_startup():
    try:
        snapshot = await lm_router.audit_connections(force=True)
        ordered = snapshot.get("ordered_available", [])
        print(f"LM audit complete. Available providers (fastest first): {ordered}")
    except Exception as exc:
        print(f"LM audit failed at startup: {exc}")

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Models ---
class ChatRequest(BaseModel):
    text: str
    game: str = None
    use_rag: bool = True
    lm_provider: str = "auto"
    tool: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    sources: list = []
    context_used: bool = False
    sources_count: int = 0
    lm_provider: str = None
    tool_name: str = None
    tool_result: dict = None

class IngestRequest(BaseModel):
    game: str
    force: bool = False

class TrainRequest(BaseModel):
    game: str

class PredictRequest(BaseModel):
    game: str
    recent_k: int = 10

class GameSummaryResponse(BaseModel):
    game: str
    draw_count: int


def _require_game_key(raw_game: str) -> str:
    game_key = resolve_game_key(raw_game)
    if not game_key:
        available = sorted([GAME_TITLES.get(g, g) for g in GAME_CONFIGS.keys()])
        raise ValueError(
            f"Unknown game '{raw_game}'. Supported games: {', '.join(available)}"
        )
    return game_key


def _workspace_roots() -> list[Path]:
    candidates = [
        Path(os.getcwd()),
        Path("/app"),
        Path("/data"),
    ]
    return [path.resolve() for path in candidates if path.exists()]


def _resolve_safe_path(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("Path is required")

    p = Path(raw_path)
    roots = _workspace_roots()
    if not roots:
        raise ValueError("No accessible workspace roots are available")

    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = (roots[0] / p).resolve()

    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue

    raise ValueError("Path is outside allowed workspace roots")


def _tool_list_files(params: Dict[str, Any]) -> Dict[str, Any]:
    directory = _resolve_safe_path(params.get("path", "."))
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"Directory not found: {directory}")

    entries = []
    for child in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))[:300]:
        entries.append({
            "name": child.name,
            "type": "dir" if child.is_dir() else "file",
            "size": child.stat().st_size if child.is_file() else None,
        })

    return {
        "path": str(directory),
        "count": len(entries),
        "entries": entries,
    }


def _tool_read_file(params: Dict[str, Any]) -> Dict[str, Any]:
    file_path = _resolve_safe_path(params.get("path"))
    if not file_path.exists() or not file_path.is_file():
        raise ValueError(f"File not found: {file_path}")

    text = file_path.read_text(encoding="utf-8", errors="replace")
    start_line = max(1, int(params.get("start_line", 1)))
    end_line = int(params.get("end_line", 0))
    lines = text.splitlines()
    if end_line <= 0:
        end_line = min(start_line + 199, len(lines))
    end_line = min(end_line, len(lines))

    selected = lines[start_line - 1:end_line]
    return {
        "path": str(file_path),
        "start_line": start_line,
        "end_line": end_line,
        "content": "\n".join(selected),
        "total_lines": len(lines),
    }


def _tool_write_file(params: Dict[str, Any]) -> Dict[str, Any]:
    file_path = _resolve_safe_path(params.get("path"))
    content = params.get("content", "")
    mode = str(params.get("mode", "overwrite")).lower()

    file_path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "append" and file_path.exists():
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(content)
    else:
        file_path.write_text(content, encoding="utf-8")

    return {
        "path": str(file_path),
        "bytes_written": len(content.encode("utf-8")),
        "mode": mode,
    }


def _tool_internet_search(params: Dict[str, Any]) -> Dict[str, Any]:
    query = str(params.get("query", "")).strip()
    if not query:
        raise ValueError("Search query is required")

    url = "https://api.duckduckgo.com/"
    response = requests.get(
        url,
        params={
            "q": query,
            "format": "json",
            "no_html": 1,
            "no_redirect": 1,
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()

    results = []
    abstract = payload.get("AbstractText")
    if abstract:
        results.append({
            "title": payload.get("Heading") or query,
            "snippet": abstract,
            "url": payload.get("AbstractURL"),
        })

    for item in payload.get("RelatedTopics", [])[:6]:
        if isinstance(item, dict) and item.get("Text"):
            results.append({
                "title": item.get("Text", "")[:80],
                "snippet": item.get("Text"),
                "url": item.get("FirstURL"),
            })

    return {
        "query": query,
        "results": results[:8],
        "result_count": len(results[:8]),
    }


def _tool_self_diagnostics(params: Dict[str, Any]) -> Dict[str, Any]:
    game_names = list(GAME_CONFIGS.keys())
    collections = chroma_client.get_collections_snapshot(game_names)
    chroma_status = chroma_client.get_chroma_status()

    models_dir = Path(os.environ.get("DATA_DIR", "/data")) / "models"
    model_files = []
    if models_dir.exists():
        for model_file in sorted(models_dir.glob("*_model.joblib")):
            model_files.append({
                "name": model_file.name,
                "bytes": model_file.stat().st_size,
                "is_valid": model_file.stat().st_size > 0,
            })

    return {
        "api": {"status": "healthy", "timestamp": time.time()},
        "startup": {
            "status": startup_state.get("status"),
            "progress": startup_state.get("progress"),
            "total": startup_state.get("total"),
            "current_game": startup_state.get("current_game"),
        },
        "chroma": {
            "status": chroma_status,
            "collections": collections,
            "expected_games": len(game_names),
        },
        "models": {
            "path": str(models_dir),
            "count": len(model_files),
            "files": model_files,
        },
        "manual_ingest": manual_ingest_state,
    }


def _run_chat_tool(tool_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tool_payload, dict):
        raise ValueError("tool payload must be an object")

    name = str(tool_payload.get("name", "")).strip().lower()
    params = tool_payload.get("params", {}) or {}

    handlers = {
        "list_files": _tool_list_files,
        "read_file": _tool_read_file,
        "write_file": _tool_write_file,
        "internet_search": _tool_internet_search,
        "self_diagnostics": _tool_self_diagnostics,
    }

    if name not in handlers:
        raise ValueError(f"Unknown tool '{name}'. Available: {', '.join(sorted(handlers.keys()))}")

    return {"name": name, "result": handlers[name](params)}


def _render_tool_response(tool_name: str, tool_result: Dict[str, Any]) -> str:
    pretty = json.dumps(tool_result, indent=2, ensure_ascii=False)
    return (
        f"✅ Tool executed: **{tool_name}**\n\n"
        "I ran your requested tool and returned structured output below:\n\n"
        f"```json\n{pretty}\n```"
    )

def _parse_datetime(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None

    for converter in (
        lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")),
        lambda v: datetime.strptime(v, "%Y-%m-%d"),
        lambda v: datetime.strptime(v, "%m/%d/%Y"),
        lambda v: datetime.strptime(v, "%Y/%m/%d"),
        lambda v: datetime.strptime(v, "%m-%d-%Y"),
    ):
        try:
            return converter(text)
        except Exception:
            continue

    return None


def _extract_metadata_value(metadata: dict, preferred_tokens: list[str]) -> Optional[str]:
    if not isinstance(metadata, dict):
        return None

    for key, value in metadata.items():
        key_lower = str(key).lower()
        if all(token in key_lower for token in preferred_tokens):
            return str(value)

    return None


def _latest_game_snapshot(game: str, sample_size: int = 200) -> Optional[dict]:
    try:
        collection = chroma_client.client.get_collection(game)
        count = int(collection.count() or 0)
        if count <= 0:
            return {
                "game": game,
                "draw_count": 0,
                "latest_draw_date": None,
                "latest_numbers": None,
            }

        payload = collection.get(limit=min(sample_size, count), include=["metadatas"])
        metadatas = payload.get("metadatas") if isinstance(payload, dict) else []

        candidates = []
        for metadata in metadatas or []:
            draw_date = _extract_metadata_value(metadata, ["date"])
            winning_numbers = _extract_metadata_value(metadata, ["winning", "number"])
            if not winning_numbers:
                winning_numbers = _extract_metadata_value(metadata, ["numbers"])
            candidates.append({
                "draw_date": draw_date,
                "winning_numbers": winning_numbers,
                "parsed_date": _parse_datetime(draw_date),
            })

        candidates_with_date = [item for item in candidates if item.get("parsed_date") is not None]
        if candidates_with_date:
            latest = max(candidates_with_date, key=lambda item: item["parsed_date"])
        elif candidates:
            latest = candidates[0]
        else:
            latest = {"draw_date": None, "winning_numbers": None}

        return {
            "game": game,
            "draw_count": count,
            "latest_draw_date": latest.get("draw_date"),
            "latest_numbers": latest.get("winning_numbers"),
        }
    except Exception:
        return {
            "game": game,
            "draw_count": 0,
            "latest_draw_date": None,
            "latest_numbers": None,
        }


def _draw_schedule_fallback_context(raw_game: Optional[str]) -> list[dict]:
    if raw_game:
        resolved = resolve_game_key(raw_game)
        target_games = [resolved] if resolved else []
    else:
        target_games = list(GAME_CONFIGS.keys())

    snapshots = []
    for game in target_games:
        if not game:
            continue
        snapshot = _latest_game_snapshot(game)
        if snapshot is not None:
            snapshots.append(snapshot)

    return snapshots


def _chat_fallback_for_lm_unavailable(user_text: str, lm_response: str, raw_game: Optional[str] = None) -> str:
    raw_text = str(user_text or "")
    normalized = raw_text.lower()

    reason = "api_error"
    if isinstance(lm_response, str) and lm_response.startswith(LM_UNAVAILABLE_PREFIX):
        parts = lm_response.split(":", 2)
        if len(parts) >= 2:
            reason = parts[1]

    reason_message = {
        "missing_key": "LM key is not configured on the backend.",
        "rate_limited": "LM quota is currently exhausted/rate-limited.",
        "api_error": "LM provider returned an API error.",
    }.get(reason, "LM provider is temporarily unavailable.")

    if "next" in normalized and ("drawing" in normalized or "draw" in normalized):
        snapshots = _draw_schedule_fallback_context(raw_game)
        if snapshots:
            lines = []
            for item in snapshots:
                game = str(item.get("game", "")).upper()
                draw_count = int(item.get("draw_count") or 0)
                latest_date = item.get("latest_draw_date") or "unknown"
                latest_numbers = item.get("latest_numbers") or "unknown"
                lines.append(
                    f"- {game}: latest known draw date={latest_date}, latest known numbers={latest_numbers}, stored draws={draw_count}"
                )

            return (
                f"I can’t compute official next drawing schedule via LM right now because {reason_message} "
                "Here is the latest available draw data in your database:\n"
                + "\n".join(lines)
                + "\nFor official next drawing times, verify on the NY Lottery site."
            )

        return (
            f"I can’t answer draw-schedule questions from the LM right now because {reason_message} "
            "For official next drawing times, check the NY Lottery site for your game. "
            "You can still use this app for ingestion, training, and predictions while LM access is down."
        )

    return (
        f"I can’t use the LM right now because {reason_message} "
        "Please retry shortly, or update backend LM quota/key configuration."
    )


# --- API Endpoints ---
@app.get("/api")
async def root():
    return {"message": "Mensa Lottery Backend - Manual Ingestion Mode"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint to interact with the Gemini Chatbot.
    Supports both RAG-augmented and standard responses.
    """
    try:
        if request.tool:
            executed = _run_chat_tool(request.tool)
            return ChatResponse(
                response=_render_tool_response(executed["name"], executed["result"]),
                sources=[],
                context_used=False,
                sources_count=0,
                tool_name=executed["name"],
                tool_result=executed["result"],
            )

        concierge_prefix = (
            "You are Mensa Concierge: friendly, personable, very helpful, and an expert Python/React/ChromaDB RAG developer. "
            "Be concise, practical, and provide actionable steps."
        )

        if request.use_rag:
            result = await rag_service.query_with_rag(
                user_query=f"{concierge_prefix}\n\nUser request: {request.text}",
                game=request.game,
                use_all_games=request.game is None,
                lm_client=lm_router,
                lm_provider=request.lm_provider,
            )
            response_text = result.get("response", "")
            if not (isinstance(response_text, str) and response_text.startswith(LM_UNAVAILABLE_PREFIX)):
                provider_name = result.get("lm_provider") or "auto"
                return ChatResponse(
                    response=response_text,
                    sources=result.get("sources", []),
                    context_used=True,
                    sources_count=result.get("context_count", 0),
                    lm_provider=provider_name,
                )

            fallback_text = _chat_fallback_for_lm_unavailable(
                request.text,
                response_text or f"{LM_UNAVAILABLE_PREFIX}:api_error:All configured LM providers are unavailable",
                request.game,
            )
            return ChatResponse(
                response=fallback_text,
                sources=[],
                context_used=True,
                sources_count=0,
                lm_provider="fallback",
            )

        lm_result = await lm_router.generate_with_provider(
            f"{concierge_prefix}\n\nUser request: {request.text}",
            preferred_provider=request.lm_provider,
        )
        response_text = lm_result.get("response", "")
        provider_name = lm_result.get("provider")
        if not (isinstance(response_text, str) and response_text.startswith(LM_UNAVAILABLE_PREFIX)):
            return ChatResponse(response=response_text, lm_provider=provider_name)

        fallback_text = _chat_fallback_for_lm_unavailable(
            request.text,
            response_text or f"{LM_UNAVAILABLE_PREFIX}:api_error:All configured LM providers are unavailable",
            request.game,
        )
        return ChatResponse(response=fallback_text, lm_provider="fallback")
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return ChatResponse(response=f"Error: {str(e)}", tool_result={"error": str(e)})

# --- Placeholder Endpoints ---
# These endpoints are placeholders and need to be implemented.

@app.get("/api/predictions/all")
async def get_all_predictions():
    return {"message": "Endpoint not implemented yet."}

@app.get("/api/chroma/status")
async def get_chroma_status():
    return chroma_client.get_chroma_status()

@app.get("/api/chroma/collections")
async def get_chroma_collections():
    """Return resilient Chroma collection snapshot with metadata and stable record index."""
    game_names = list(GAME_CONFIGS.keys())
    try:
        results = chroma_client.get_collections_snapshot(game_names)
        status = chroma_client.get_chroma_status()
        return {
            "status": status.get("status", "unknown"),
            "collections": results,
            "meta": {
                "record_index_basis": "GAME_CONFIGS order",
                "total_expected": len(game_names),
                "resolved": len(results),
                "has_partial_errors": any(item.get("state") in {"error", "timeout"} for item in results),
            }
        }
    except Exception as e:
        # Normalize error shape for frontend
        fallback = [
            {
                "name": name,
                "record_index": idx + 1,
                "count": 0,
                "metadata": {},
                "state": "error",
                "error": "Fallback snapshot due to endpoint failure",
            }
            for idx, name in enumerate(game_names)
        ]
        return {
            "status": "error",
            "error": str(e),
            "collections": fallback,
            "meta": {
                "record_index_basis": "GAME_CONFIGS order",
                "total_expected": len(game_names),
                "resolved": len(fallback),
                "has_partial_errors": True,
            },
        }

@app.post("/api/ingest")
async def ingest_data(request: IngestRequest):
    """
    Manual ingestion endpoint triggered from dashboard.
    Ingests data for a single game asynchronously with progress tracking.
    """
    try:
        game_key = _require_game_key(request.game)
    except ValueError as e:
        return {
            "status": "error",
            "game": request.game,
            "message": str(e)
        }

    def progress_callback(rows_fetched, total_rows):
        """Callback to track ingestion progress."""
        manual_ingest_state[game_key] = {
            "status": "ingesting",
            "rows_fetched": rows_fetched,
            "total_rows": total_rows,
            "progress": (rows_fetched / total_rows * 100) if total_rows > 0 else 0
        }
    
    try:
        print(f"📥 Manual ingestion started for {game_key}")
        manual_ingest_state[game_key] = {
            "status": "ingesting",
            "rows_fetched": 0,
            "total_rows": 0,
            "progress": 0
        }
        
        result = ingest_service.fetch_and_sync(
            game_key,
            progress_callback=progress_callback,
            force=request.force,
        )
        
        manual_ingest_state[game_key] = {
            "status": "completed",
            "rows_fetched": result.get("total", 0),
            "total_rows": result.get("total", 0),
            "progress": 100,
            "added": result.get("added", 0)
        }
        print(f"✅ Manual ingestion completed for {game_key}")
        skipped_existing = bool(result.get("skipped_existing", False))
        response_message = (
            f"Skipped ingest for {game_key}: records already exist"
            if skipped_existing
            else f"Successfully ingested {game_key}"
        )
        return {
            "status": "completed",
            "game": game_key,
            "added": result.get("added", 0),
            "total": result.get("total", 0),
            "processed": result.get("processed", 0),
            "skipped_existing": skipped_existing,
            "message": response_message,
        }
    except Exception as e:
        manual_ingest_state[game_key] = {
            "status": "error",
            "error": str(e)
        }
        print(f"❌ Manual ingestion failed for {game_key}: {str(e)}")
        return {
            "status": "error",
            "game": game_key,
            "message": str(e)
        }

@app.get("/api/ingest_progress")
async def get_ingest_progress(game: str = None):
    """
    Get current manual ingestion progress.
    If game specified, return progress for that game.
    Otherwise, return all ongoing ingestions.
    """
    if game:
        game_key = resolve_game_key(game) or game
        return manual_ingest_state.get(game_key, {"status": "idle"})
    return manual_ingest_state

@app.post("/api/train")
async def train_model(request: TrainRequest):
    """
    Manual training endpoint triggered from dashboard.
    Trains model for a single game.
    """
    try:
        game_key = _require_game_key(request.game)
        # Lazy import to avoid TensorFlow overhead during app startup
        from services.trainer import trainer_service
        data_dir = os.environ.get('DATA_DIR', '/data')
        store_path = os.path.join(data_dir, 'experiments', "experiments.json")
        exp_store = ExperimentStore(store_path)
        timestamp = time.time()

        print(f"🎯 Training started for {game_key}")
        result = trainer_service.train_model(game_key)
        if result.get("status") != "success":
            print(f"❌ Training failed for {game_key}: {result.get('message', 'unknown error')}")
            failed_description = (
                f"Training failed for {game_key}. "
                f"Reason: {result.get('message', 'unknown error')}"
            )
            exp_store.save_experiment({
                "experiment_id": f"train-{game_key}-{int(timestamp)}",
                "game": game_key,
                "score": 0,
                "timestamp": timestamp,
                "status": "FAILED",
                "type": "training",
                "error": result.get("message", "unknown error"),
                "description": failed_description,
            })
            return {
                **result,
                "status": "error",
                "game": game_key,
                "message": result.get("message", "Training failed"),
            }

        print(f"✅ Training completed for {game_key}")

        success_description = (
            f"Random Forest training completed for {game_key}. "
            f"Accuracy={result.get('accuracy', 0):.4f}, "
            f"MAE={result.get('mae', 0):.4f}, "
            f"Samples={result.get('samples', 0)}"
        )

        exp_store.save_experiment({
            "experiment_id": f"train-{game_key}-{int(timestamp)}",
            "game": game_key,
            "score": result.get("accuracy", 0),
            "timestamp": timestamp,
            "status": "COMPLETED",
            "type": "training",
            "description": success_description,
        })

        return {
            **result,
            "status": "COMPLETED",
            "game": game_key,
            "message": f"Successfully trained model for {game_key}",
            "experiment_id": f"train-{game_key}-{int(timestamp)}",
            "score": result.get("accuracy", 0),
        }
    except Exception as e:
        print(f"❌ Training failed for {request.game}: {str(e)}")
        return {
            "status": "error",
            "game": request.game,
            "message": str(e)
        }

@app.get("/api/experiments")
async def get_experiments():
    data_dir = os.environ.get('DATA_DIR', '/data')
    store_path = os.path.join(data_dir, 'experiments', "experiments.json")
    exp_store = ExperimentStore(store_path)
    experiments = exp_store.list_experiments()
    return {
        "experiments": experiments,
    }

@app.post("/api/predict")
async def predict(request: PredictRequest):
    """
    Prediction endpoint for a specific game.
    """
    try:
        game_key = _require_game_key(request.game)
        # Lazy import to avoid TensorFlow overhead during app startup
        from services.predictor import predictor_service
        data_dir = os.environ.get('DATA_DIR', '/data')
        store_path = os.path.join(data_dir, 'experiments', "experiments.json")
        exp_store = ExperimentStore(store_path)
        timestamp = time.time()

        result = predictor_service.predict_next_draw(game_key, request.recent_k)
        exp_store.save_experiment({
            "experiment_id": f"predict-{game_key}-{int(timestamp)}",
            "game": game_key,
            "timestamp": timestamp,
            "status": "COMPLETED",
            "type": "prediction",
            "recent_k": request.recent_k,
            "prediction": result
        })
        return {
            **result,
            "status": "COMPLETED",
            "game": game_key,
        }
    except Exception as e:
        return {
            "status": "error",
            "game": request.game,
            "message": str(e)
        }

@app.get("/api/games")
async def get_games():
    """
    Returns list of available games for ingestion.
    """
    game_names = list(GAME_CONFIGS.keys())
    return {
        "games": game_names,
        "titles": {game: GAME_TITLES.get(game, game) for game in game_names},
    }

@app.get("/api/games/{game}/summary", response_model=GameSummaryResponse)
async def get_game_summary(game: str):
    """
    Get summary statistics for a specific game.
    """
    game_key = _require_game_key(game)
    draw_count = chroma_client.count_documents(game_key)
    return GameSummaryResponse(game=game_key, draw_count=draw_count)

@app.get("/api/startup_status")
async def get_startup_status():
    """
    Returns initialization status for UI progress tracking.
    """
    elapsed = None
    if startup_state["started_at"]:
        elapsed = (startup_state["completed_at"] or time.time()) - startup_state["started_at"]

    games_snapshot = {
        game: {
            "status": game_data.get("status"),
            "error": game_data.get("error"),
        }
        for game, game_data in (startup_state.get("games") or {}).items()
    }

    return {
        "status": startup_state.get("status"),
        "progress": float(startup_state.get("progress") or 0),
        "total": int(startup_state.get("total") or 0),
        "current_game": startup_state.get("current_game"),
        "current_task": startup_state.get("current_task"),
        "current_game_rows_fetched": int(startup_state.get("current_game_rows_fetched") or 0),
        "current_game_rows_total": int(startup_state.get("current_game_rows_total") or 0),
        "games": games_snapshot,
        "started_at": startup_state.get("started_at"),
        "completed_at": startup_state.get("completed_at"),
        "elapsed_s": elapsed,
        "available_games": list(GAME_CONFIGS.keys()),
        "manual_mode": True,
    }

@app.post("/api/startup_init")
async def start_initialization():
    """
    Trigger background initialization/ingestion.
    """
    global _ingestion_started
    if _ingestion_started and startup_state.get("status") == "ingesting":
        return {
            "status": startup_state["status"],
            "message": "Initialization already running",
            "available_games": list(GAME_CONFIGS.keys()),
        }

    _reset_startup_state_for_new_run()
    _ingestion_started = True
    start_background_ingestion()

    return {
        "status": startup_state["status"],
        "message": "Initialization started",
        "available_games": list(GAME_CONFIGS.keys()),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
