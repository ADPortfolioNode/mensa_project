from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import time
import os

# Import services
from config import GAME_CONFIGS
from services.gemini_client import gemini_client
from services.chroma_client import chroma_client
from experiments.store import ExperimentStore
from services.ingest import ingest_service
from services.trainer import trainer_service
from services.predictor import predictor_service
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
async def get_all_predictions():
    return {"message": "Endpoint not implemented yet."}

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
        print(f"🎯 Training started for {request.game}")
        result = trainer_service.train_model(request.game)
        print(f"✅ Training completed for {request.game}")
        return {
            "status": "COMPLETED",
            "game": request.game,
            "message": f"Successfully trained model for {request.game}",
            "experiment_id": request.game,
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
        result = predictor_service.predict_next_draw(request.game, request.recent_k)
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
