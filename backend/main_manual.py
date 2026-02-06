from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

app = FastAPI()

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    return {"message": "Mensa Lottery Backend - Manual Ingestion Mode"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint to interact with the Gemini Chatbot.
    """
    response_text = await gemini_client.generate_text(request.text)
    return ChatResponse(response=response_text)

@app.get("/api/predictions/all")
async def get_all_predictions():
    return {"message": "Endpoint not implemented yet."}

@app.get("/api/chroma/status")
async def get_chroma_status():
    return chroma_client.get_chroma_status()

@app.get("/api/chroma/collections")
async def get_chroma_collections():
    """Return a safe list of collections with counts."""
    results = []
    try:
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
        return {"status": "error", "error": str(e), "collections": results}

@app.post("/api/ingest")
async def ingest_data(request: IngestRequest):
    """
    Manual ingestion endpoint triggered from dashboard.
    Ingests data for a single game.
    """
    try:
        print(f"📥 Manual ingestion started for {request.game}")
        result = ingest_service.fetch_and_sync(request.game)
        print(f"✅ Manual ingestion completed for {request.game}")
        return {
            "status": "success",
            "game": request.game,
            "added": result.get("added", 0),
            "total": result.get("total", 0),
            "message": f"Successfully ingested {request.game}"
        }
    except Exception as e:
        print(f"❌ Manual ingestion failed for {request.game}: {str(e)}")
        return {
            "status": "error",
            "game": request.game,
            "message": str(e)
        }

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
            "status": "success",
            "game": request.game,
            "message": f"Successfully trained model for {request.game}",
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
    Returns ready status. No automatic ingestion.
    User must manually trigger ingestion from dashboard.
    """
    return {
        "status": "ready",
        "message": "Backend ready. Use dashboard to manually ingest data.",
        "manual_mode": True,
        "available_games": list(GAME_CONFIGS.keys())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
