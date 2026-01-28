from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import time

# Import your Gemini client
from config import GAME_CONFIGS
from services.gemini_client import gemini_client
from services.chroma_client import chroma_client
from experiments.store import ExperimentStore
from services.ingest import ingest_service
from services.trainer import trainer_service
from services.predictor import predictor_service
import os

app = FastAPI()

# --- Global startup state tracking for monitoring ---
startup_state = {
    "status": "initializing",
    "progress": 0.0,  # Can be fractional (e.g., 1.5 of 7)
    "total": len(GAME_CONFIGS),
    "current_game": None,
    "current_task": None,
    "current_game_rows_fetched": 0,  # Track rows fetched in current game
    "current_game_rows_total": 0,    # Expected total rows (if known)
    "games": {game: {"status": "pending", "error": None} for game in GAME_CONFIGS.keys()},
    "started_at": None,
    "completed_at": None
}

def start_background_ingestion():
    """Start non-blocking background ingestion in a daemon thread.
    
    This allows the server to become responsive immediately while data ingestion
    happens in the background. Non-blocking pattern for fast startup.
    """
    def ingest_all():
        startup_state["started_at"] = time.time()
        startup_state["status"] = "ingesting"
        
        for i, game in enumerate(GAME_CONFIGS.keys(), 1):
            try:
                startup_state["current_game"] = game
                startup_state["current_task"] = "fetching"
                startup_state["progress"] = float(i - 1)  # Mark as in-progress before starting
                startup_state["current_game_rows_fetched"] = 0
                startup_state["current_game_rows_total"] = 0
                startup_state["games"][game]["status"] = "ingesting"
                startup_state["games"][game]["error"] = None
                
                print(f"[{i}/{startup_state['total']}] Ingesting {game}...")
                
                # Define progress callback for this game
                def update_game_progress(rows_fetched, total_rows):
                    startup_state["current_game_rows_fetched"] = rows_fetched
                    startup_state["current_game_rows_total"] = total_rows
                    # Update overall progress with fractional value
                    # e.g., if on game 1 and have fetched 500 of 1000 rows, progress = 0.5
                    if total_rows and total_rows > 0:
                        startup_state["progress"] = float(i - 1) + (rows_fetched / total_rows)
                    else:
                        # Fallback for unknown total, advance based on game number
                        startup_state["progress"] = float(i - 1)
                
                # Call the synchronous ingest service with progress callback
                ingest_service.fetch_and_sync(game, progress_callback=update_game_progress)
                
                startup_state["games"][game]["status"] = "completed"
                startup_state["games"][game]["error"] = None
                startup_state["progress"] = float(i)  # Mark as complete
                startup_state["current_game_rows_fetched"] = 0
                startup_state["current_game_rows_total"] = 0
                print(f"✓ {game} ingested successfully")
                
            except Exception as e:
                startup_state["games"][game]["status"] = "failed"
                startup_state["games"][game]["error"] = str(e)
                startup_state["progress"] = i  # Still count this in progress even if failed
                print(f"⚠ Failed to ingest {game}: {str(e)}")
        
        startup_state["status"] = "completed"
        startup_state["current_game"] = None
        startup_state["current_task"] = None
        startup_state["completed_at"] = time.time()
        elapsed = startup_state["completed_at"] - startup_state["started_at"]
        print(f"\n✓ Background ingestion completed in {elapsed:.1f}s")
    
    # Daemon thread ensures it won't block shutdown
    thread = threading.Thread(target=ingest_all, daemon=True, name="BackgroundIngestion")
    thread.start()

# Track if ingestion has been started
_ingestion_started = False

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

class ChatResponse(BaseModel):
    response: str

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
    return {"message": "Mensa-JE Backend is running"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint to interact with the Gemini Chatbot.
    """
    response_text = await gemini_client.generate_text(request.text)
    return ChatResponse(response=response_text)

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
    return ingest_service.fetch_and_sync(request.game)

@app.post("/api/train")
async def train_model(request: TrainRequest):
    return trainer_service.train_model(request.game)

@app.get("/api/experiments")
async def get_experiments():
    data_dir = os.environ.get('DATA_DIR', '/data')
    store_path = os.path.join(data_dir, 'experiments', "experiments.json")
    exp_store = ExperimentStore(store_path)
    return exp_store.list_experiments()

@app.post("/api/predict")
async def predict(request: PredictRequest):
    return predictor_service.predict_next_draw(request.game, request.recent_k)

@app.get("/api/games")
async def get_games():
    game_names = list(GAME_CONFIGS.keys())
    return {"games": game_names}

@app.get("/api/games/{game}/summary", response_model=GameSummaryResponse)
async def get_game_summary(game: str):
    draw_count = chroma_client.count_documents(game)
    return GameSummaryResponse(game=game, draw_count=draw_count)

@app.get("/api/startup_status")
async def get_startup_status():
    """Get current startup status and trigger ingestion if not started."""
    global _ingestion_started
    
    if not _ingestion_started:
        _ingestion_started = True
        start_background_ingestion()
    
    return {
        "status": startup_state["status"],
        "progress": startup_state["progress"],
        "total": startup_state["total"],
        "current_game": startup_state["current_game"],
        "current_task": startup_state["current_task"],
        "games": startup_state["games"],
        "elapsed_s": round(time.time() - startup_state["started_at"], 1) if startup_state["started_at"] else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
