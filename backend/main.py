from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
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
    "progress": 0,
    "total": len(GAME_CONFIGS),
    "current_game": None,
    "current_task": None,
    "games": {game: "pending" for game in GAME_CONFIGS.keys()},
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
                startup_state["progress"] = i
                
                print(f"[{i}/{startup_state['total']}] Ingesting {game}...")
                
                # Run async ingestion in new event loop within thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(ingest_service.fetch_and_sync(game))
                loop.close()
                
                startup_state["games"][game] = "completed"
                print(f"✓ {game} ingested successfully")
                
            except Exception as e:
                startup_state["games"][game] = f"failed: {str(e)}"
                print(f"⚠ Failed to ingest {game}: {str(e)}")
        
        startup_state["status"] = "completed"
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
    # In Chroma v0.6.0, list_collections only returns collection names (strings).
    # We need to get each collection by its name to access its attributes.
    collection_names = chroma_client.list_collections() # This now returns a list of strings
    collections_with_details = []
    for collection_name in collection_names: # Iterate directly over names
        collection = chroma_client.client.get_collection(collection_name)
        collections_with_details.append({
            "name": collection.name,
            "id": collection.id,
            "metadata": collection.metadata,
            "count": collection.count()
        })
    return collections_with_details

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
    uvicorn.run(app, host="0.0.0.0", port=5000)
