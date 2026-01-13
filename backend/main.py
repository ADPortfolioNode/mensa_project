from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import your Gemini client
from services.gemini_client import gemini_client
from services.chroma_client import chroma_client
from experiments.store import ExperimentStore
from services.ingest import ingest_service
from services.trainer import trainer_service
from services.predictor import predictor_service
import os

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
    return chroma_client.list_collections()

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

@app.get("/api/games/{game}/summary", response_model=GameSummaryResponse)
async def get_game_summary(game: str):
    draw_count = chroma_client.count_documents(game)
    return GameSummaryResponse(game=game, draw_count=draw_count)

@app.get("/api/startup_status")
async def get_startup_status():
    return {"status": "completed", "progress": 100, "total": 0, "current_game": None, "current_task": None, "games": {}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
