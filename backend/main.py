from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import time
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests

# Import services
from config import GAME_CONFIGS
from services.gemini_client import gemini_client
from services.chroma_client import chroma_client
from experiments.store import ExperimentStore
from services.ingest import ingest_service
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

def start_background_ingestion():
    """Start non-blocking background ingestion in a daemon thread."""
    def ingest_all():
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
                        startup_state["progress"] = float(i - 1) + (rows_fetched / total_rows)
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

    thread = threading.Thread(target=ingest_all, daemon=True, name="BackgroundIngestion")
    thread.start()

app = FastAPI()

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
    tool: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    sources: list = []
    context_used: bool = False
    sources_count: int = 0
    tool_name: str = None
    tool_result: dict = None

class IngestRequest(BaseModel):
    game: str

class TrainRequest(BaseModel):
    game: str

class PredictRequest(BaseModel):
    game: str
    recent_k: int = 10

class GameSummaryResponse(BaseModel):
    game: str
    draw_count: int


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


def _build_non_rag_fallback(user_text: str) -> str:
    return (
        "Gemini is currently unavailable, but core workflows are online.\n\n"
        "Available actions right now:\n"
        "- Run ingestion for one game or all games\n"
        "- Train models and generate predictions\n"
        "- Inspect Chroma collections and experiments\n\n"
        f"Your message was: '{user_text}'. "
        "If you want, I can help with a concrete operation (for example: 'train take5')."
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
            # Use RAG service for context-aware responses
            result = await rag_service.query_with_rag(
                user_query=request.text,
                game=request.game,
                use_all_games=request.game is None
            )
            return ChatResponse(
                response=result.get("response", ""),
                sources=result.get("sources", []),
                context_used=True,
                sources_count=result.get("context_count", 0)
            )
        else:
            # Standard response without RAG
            response_text = await gemini_client.generate_text(
                f"{concierge_prefix}\n\nUser request: {request.text}"
            )
            if isinstance(response_text, str) and "trouble connecting to the Gemini API" in response_text:
                response_text = _build_non_rag_fallback(request.text)
            return ChatResponse(response=response_text)
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
    def progress_callback(rows_fetched, total_rows):
        """Callback to track ingestion progress."""
        manual_ingest_state[request.game] = {
            "status": "ingesting",
            "rows_fetched": rows_fetched,
            "total_rows": total_rows,
            "progress": (rows_fetched / total_rows * 100) if total_rows > 0 else 0
        }
    
    try:
        print(f"📥 Manual ingestion started for {request.game}")
        manual_ingest_state[request.game] = {
            "status": "ingesting",
            "rows_fetched": 0,
            "total_rows": 0,
            "progress": 0
        }
        
        result = ingest_service.fetch_and_sync(request.game, progress_callback=progress_callback)
        
        manual_ingest_state[request.game] = {
            "status": "completed",
            "rows_fetched": result.get("total", 0),
            "total_rows": result.get("total", 0),
            "progress": 100,
            "added": result.get("added", 0)
        }
        print(f"✅ Manual ingestion completed for {request.game}")
        return {
            "status": "completed",
            "game": request.game,
            "added": result.get("added", 0),
            "total": result.get("total", 0),
            "message": f"Successfully ingested {request.game}"
        }
    except Exception as e:
        manual_ingest_state[request.game] = {
            "status": "error",
            "error": str(e)
        }
        print(f"❌ Manual ingestion failed for {request.game}: {str(e)}")
        return {
            "status": "error",
            "game": request.game,
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
        return manual_ingest_state.get(game, {"status": "idle"})
    return manual_ingest_state

@app.post("/api/train")
async def train_model(request: TrainRequest):
    """
    Manual training endpoint triggered from dashboard.
    Trains model for a single game.
    """
    try:
        # Lazy import to avoid TensorFlow overhead during app startup
        from services.trainer import trainer_service
        data_dir = os.environ.get('DATA_DIR', '/data')
        store_path = os.path.join(data_dir, 'experiments', "experiments.json")
        exp_store = ExperimentStore(store_path)
        timestamp = time.time()

        print(f"🎯 Training started for {request.game}")
        result = trainer_service.train_model(request.game)
        if result.get("status") != "success":
            print(f"❌ Training failed for {request.game}: {result.get('message', 'unknown error')}")
            exp_store.save_experiment({
                "experiment_id": f"train-{request.game}-{int(timestamp)}",
                "game": request.game,
                "score": 0,
                "timestamp": timestamp,
                "status": "FAILED",
                "type": "training",
                "error": result.get("message", "unknown error")
            })
            return {
                "status": "error",
                "game": request.game,
                "message": result.get("message", "Training failed"),
                **result
            }

        print(f"✅ Training completed for {request.game}")

        exp_store.save_experiment({
            "experiment_id": f"train-{request.game}-{int(timestamp)}",
            "game": request.game,
            "score": result.get("accuracy", 0),
            "timestamp": timestamp,
            "status": "COMPLETED",
            "type": "training"
        })

        return {
            **result,
            "status": "COMPLETED",
            "game": request.game,
            "message": f"Successfully trained model for {request.game}",
            "experiment_id": f"train-{request.game}-{int(timestamp)}",
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
    return exp_store.list_experiments()

@app.post("/api/predict")
async def predict(request: PredictRequest):
    """
    Prediction endpoint for a specific game.
    """
    try:
        # Lazy import to avoid TensorFlow overhead during app startup
        from services.predictor import predictor_service
        data_dir = os.environ.get('DATA_DIR', '/data')
        store_path = os.path.join(data_dir, 'experiments', "experiments.json")
        exp_store = ExperimentStore(store_path)
        timestamp = time.time()

        result = predictor_service.predict_next_draw(request.game, request.recent_k)
        exp_store.save_experiment({
            "experiment_id": f"predict-{request.game}-{int(timestamp)}",
            "game": request.game,
            "timestamp": timestamp,
            "status": "COMPLETED",
            "type": "prediction",
            "recent_k": request.recent_k,
            "prediction": result
        })
        return {
            "status": "success",
            "game": request.game,
            **result
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
    return {"games": game_names}

@app.get("/api/games/{game}/summary", response_model=GameSummaryResponse)
async def get_game_summary(game: str):
    """
    Get summary statistics for a specific game.
    """
    draw_count = chroma_client.count_documents(game)
    return GameSummaryResponse(game=game, draw_count=draw_count)

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
    if not _ingestion_started:
        _ingestion_started = True
        start_background_ingestion()
    return {
        "status": startup_state["status"],
        "message": "Initialization started" if _ingestion_started else "Initialization already running",
        "available_games": list(GAME_CONFIGS.keys()),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
