from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os
import uuid
import logging

# Import services
from config import GAME_CONFIGS, settings
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
    "games": {game: {"status": "pending", "error": None, "rows_fetched": 0, "rows_total": 0} for game in GAME_CONFIGS.keys()},
    "started_at": None,
    "completed_at": None,
}

# Track manual ingestion progress globally
manual_ingest_state = {}

_ingestion_started = False
_startup_lock = threading.Lock()

def _recalculate_startup_progress():
    total_games = len(GAME_CONFIGS)
    progress = 0.0
    for game, data in startup_state["games"].items():
        if data["status"] == "completed":
            progress += 1.0
        elif data["status"] == "ingesting":
            rows_total = data.get("rows_total") or 0
            rows_fetched = data.get("rows_fetched") or 0
            if rows_total > 0:
                progress += min(rows_fetched / rows_total, 1.0)
    startup_state["progress"] = min(progress, float(total_games))

def start_background_ingestion():
    """Start non-blocking background ingestion in a daemon thread."""
    def ingest_all():
        with _startup_lock:
            startup_state["started_at"] = time.time()
            startup_state["status"] = "ingesting"

        max_workers = int(os.getenv("INGEST_MAX_CONCURRENT", "2"))

        def ingest_one(game):
            try:
                with _startup_lock:
                    startup_state["current_game"] = game
                    startup_state["current_task"] = "fetching"
                    startup_state["current_game_rows_fetched"] = 0
                    startup_state["current_game_rows_total"] = 0
                    startup_state["games"][game]["status"] = "ingesting"
                    startup_state["games"][game]["error"] = None

                def update_game_progress(rows_fetched, total_rows):
                    with _startup_lock:
                        startup_state["current_game"] = game
                        startup_state["current_task"] = "fetching"
                        startup_state["current_game_rows_fetched"] = rows_fetched
                        startup_state["current_game_rows_total"] = total_rows
                        startup_state["games"][game]["rows_fetched"] = rows_fetched
                        startup_state["games"][game]["rows_total"] = total_rows
                        _recalculate_startup_progress()

                ingest_service.fetch_and_sync(game, progress_callback=update_game_progress)

                with _startup_lock:
                    startup_state["games"][game]["status"] = "completed"
                    startup_state["games"][game]["error"] = None
                    startup_state["games"][game]["rows_fetched"] = startup_state["games"][game]["rows_total"]
                    _recalculate_startup_progress()
            except Exception as e:
                with _startup_lock:
                    startup_state["games"][game]["status"] = "failed"
                    startup_state["games"][game]["error"] = str(e)
                    _recalculate_startup_progress()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(ingest_one, game) for game in GAME_CONFIGS.keys()]
            for _ in as_completed(futures):
                pass

        with _startup_lock:
            startup_state["status"] = "completed"
            startup_state["current_game"] = None
            startup_state["current_task"] = None
            startup_state["completed_at"] = time.time()

    thread = threading.Thread(target=ingest_all, daemon=True, name="BackgroundIngestion")
    thread.start()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mensa")

app = FastAPI()

@app.middleware("http")
async def add_correlation_and_catch(request: Request, call_next):
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled error", extra={"path": request.url.path, "correlation_id": correlation_id})
        return JSONResponse(
            status_code=500,
            content={
                "path": request.url.path,
                "detail": "Internal server error",
                "category": "server_error",
                "correlation_id": correlation_id
            }
        )

    response.headers["X-Correlation-Id"] = correlation_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "path": request.url.path,
            "detail": exc.detail,
            "category": "http_error",
            "correlation_id": correlation_id
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=422,
        content={
            "path": request.url.path,
            "detail": exc.errors(),
            "category": "validation_error",
            "correlation_id": correlation_id
        }
    )

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    """Log startup information and verify critical connections."""
    print("="*80)
    print("MENSA BACKEND STARTUP")
    print("="*80)
    print(f"Chroma Host: {settings.CHROMA_HOST}")
    print(f"Chroma Port: {settings.CHROMA_PORT}")
    print(f"Gemini API Key: {'SET' if settings.GEMINI_API_KEY else 'NOT SET'}")
    print(f"Data Directory: {os.getenv('DATA_DIR', '/data')}")
    print("="*80)
    
    # Verify Chroma connection
    try:
        status = chroma_client.get_chroma_status()
        print(f"✓ ChromaDB Status: {status.get('status', 'unknown')}")
    except Exception as e:
        print(f"⚠ ChromaDB Connection Issue: {str(e)}")
        print("  (Retrying with lazy initialization)")
    
    print("✓ Backend startup complete - API ready on 0.0.0.0:5000")
    print("="*80)

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

class ChatResponse(BaseModel):
    response: str
    sources: list = []
    context_used: bool = False
    sources_count: int = 0

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
            response_text = await gemini_client.generate_text(request.text)
            return ChatResponse(response=response_text)
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return ChatResponse(response=f"Error: {str(e)}")

# --- Placeholder Endpoints ---
# These endpoints are placeholders and need to be implemented.

@app.get("/api/predictions/all")
async def get_all_predictions(recent_k: int = 10):
    """Legacy helper for all-games predictions."""
    try:
        from services.predictor import predictor_service
        game_names = list(GAME_CONFIGS.keys())
        predictions = predictor_service.predict_all_games(game_names, recent_k)
        return {
            "status": "success",
            "game": "all",
            "predictions": predictions,
            "games": game_names,
        }
    except Exception as e:
        return {
            "status": "error",
            "game": "all",
            "message": str(e)
        }

@app.get("/api/chroma/status")
async def get_chroma_status():
    return chroma_client.get_chroma_status()

@app.get("/api/chroma/collections")
async def get_chroma_collections():
    """Return a safe list of collections with counts without relying on Chroma's list_collections.
    This avoids client/server version mismatches (e.g., missing 'dimension' field).
    """
    results = []
    try:
        # Start with configured game names; avoid list_collections() due to server/client mismatches
        game_names = list(GAME_CONFIGS.keys())
        for name in game_names:
            try:
                count = chroma_client.count_documents(name)
                results.append({
                    "name": name,
                    "count": count,
                })
            except Exception as inner_e:
                print(f"Error counting documents for {name}: {inner_e}")
                results.append({
                    "name": name,
                    "count": 0,
                    "error": str(inner_e),
                })
        status = chroma_client.get_chroma_status()
        return {"status": status.get("status", "unknown"), "collections": results}
    except Exception as e:
        # Normalize error shape for frontend
        return {"status": "error", "error": str(e), "collections": results}

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

        if request.game == "all":
            game_names = list(GAME_CONFIGS.keys())
            results = {}
            for game in game_names:
                try:
                    print(f"🎯 Training started for {game}")
                    result = trainer_service.train_model(game)
                    print(f"✅ Training completed for {game}")
                    results[game] = result
                    exp_store.save_experiment({
                        "experiment_id": f"train-{game}-{int(timestamp)}",
                        "game": game,
                        "score": result.get("accuracy", 0),
                        "timestamp": timestamp,
                        "status": "COMPLETED",
                        "type": "training"
                    })
                except Exception as inner_e:
                    results[game] = {"status": "error", "message": str(inner_e)}
                    exp_store.save_experiment({
                        "experiment_id": f"train-{game}-{int(timestamp)}",
                        "game": game,
                        "score": 0,
                        "timestamp": timestamp,
                        "status": "error",
                        "type": "training",
                        "message": str(inner_e)
                    })

            exp_store.save_experiment({
                "experiment_id": f"train-all-{int(timestamp)}",
                "game": "all",
                "score": 0,
                "timestamp": timestamp,
                "status": "COMPLETED",
                "type": "training",
                "results": results
            })

            return {
                "status": "COMPLETED",
                "game": "all",
                "message": "Successfully trained models for all games",
                "experiment_id": f"train-all-{int(timestamp)}",
                "results": results
            }

        print(f"🎯 Training started for {request.game}")
        result = trainer_service.train_model(request.game)
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
            "status": "COMPLETED",
            "game": request.game,
            "message": f"Successfully trained model for {request.game}",
            "experiment_id": f"train-{request.game}-{int(timestamp)}",
            "score": result.get("accuracy", 0),
            **result
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

        if request.game == "all":
            game_names = list(GAME_CONFIGS.keys())
            predictions = predictor_service.predict_all_games(game_names, request.recent_k)
            exp_store.save_experiment({
                "experiment_id": f"predict-all-{int(timestamp)}",
                "game": "all",
                "timestamp": timestamp,
                "status": "COMPLETED",
                "type": "prediction",
                "recent_k": request.recent_k,
                "predictions": predictions
            })
            return {
                "status": "success",
                "game": "all",
                "predictions": predictions,
                "games": game_names
            }

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
