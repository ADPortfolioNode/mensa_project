"""
Updated main.py with RAG-enabled chat and new endpoints
"""

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
from services.rag_service import rag_service
from services.visualization import visualization_service
from experiments.store import ExperimentStore
from services.ingest import ingest_service
from services.trainer import trainer_service
from services.predictor import predictor_service

app = FastAPI()

# --- Global startup state tracking for monitoring ---
startup_state = {
    "status": "initializing",
    "progress": 0.0,
    "total": len(GAME_CONFIGS),
    "current_game": None,
    "current_task": None,
    "current_game_rows_fetched": 0,
    "current_game_rows_total": 0,
    "games": {game: {"status": "pending", "error": None} for game in GAME_CONFIGS.keys()},
    "started_at": None,
    "completed_at": None
}

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
                
                print(f"[{i}/{startup_state['total']}] Ingesting {game}...")
                
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
                print(f"✓ {game} ingested successfully")
                
            except Exception as e:
                startup_state["games"][game]["status"] = "failed"
                startup_state["games"][game]["error"] = str(e)
                startup_state["progress"] = i
                print(f"⚠ Failed to ingest {game}: {str(e)}")
        
        startup_state["status"] = "completed"
        startup_state["current_game"] = None
        startup_state["current_task"] = None
        startup_state["completed_at"] = time.time()
        elapsed = startup_state["completed_at"] - startup_state["started_at"]
        print(f"\n✓ Background ingestion completed in {elapsed:.1f}s")
    
    thread = threading.Thread(target=ingest_all, daemon=True, name="BackgroundIngestion")
    thread.start()

_ingestion_started = False

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
    game: str = None  # Optional: specific game context
    use_rag: bool = True  # Enable/disable RAG

class ChatResponse(BaseModel):
    response: str
    sources_count: int = 0
    sources: list = []
    context_used: bool = False

class RAGQueryRequest(BaseModel):
    query: str
    game: str = None
    use_all_games: bool = False
    top_k: int = 5

class RAGQueryResponse(BaseModel):
    response: str
    sources: list
    context_count: int
    game: str = None

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
    return {"message": "Mensa Lottery Backend with RAG is running"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    RAG-enabled chat endpoint.
    Uses ChromaDB context to augment Gemini responses.
    
    Args:
        text: User's question
        game: Optional specific game context
        use_rag: Enable/disable RAG (default: True)
    
    Returns:
        ChatResponse with response text and sources
    """
    try:
        if request.use_rag:
            # Use RAG for context-aware response
            rag_result = await rag_service.query_with_rag(
                user_query=request.text,
                game=request.game,
                use_all_games=(request.game is None)
            )
            
            return ChatResponse(
                response=rag_result['response'],
                sources_count=rag_result['context_count'],
                sources=[
                    {
                        "game": s.get('game'),
                        "content": s.get('content')[:200] + "..." if len(s.get('content', '')) > 200 else s.get('content'),
                        "distance": s.get('distance')
                    } 
                    for s in rag_result.get('sources', [])
                ],
                context_used=True
            )
        else:
            # Standard LLM response without RAG
            response_text = await gemini_client.generate_text(request.text)
            return ChatResponse(
                response=response_text,
                sources_count=0,
                sources=[],
                context_used=False
            )
    
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return ChatResponse(
            response=f"Error: {str(e)}",
            sources_count=0,
            sources=[],
            context_used=False
        )

@app.post("/api/rag/query", response_model=RAGQueryResponse)
async def rag_query_endpoint(request: RAGQueryRequest):
    """
    Direct RAG query endpoint for explicit context retrieval and generation.
    Useful for detailed queries with specific context requirements.
    
    Args:
        query: The question to ask
        game: Optional specific game to search
        use_all_games: Search across all games
        top_k: Number of context documents to retrieve
    
    Returns:
        RAGQueryResponse with response and sources
    """
    try:
        # Update top_k if specified
        rag_service.top_k = request.top_k
        
        rag_result = await rag_service.query_with_rag(
            user_query=request.query,
            game=request.game,
            use_all_games=request.use_all_games
        )
        
        return RAGQueryResponse(
            response=rag_result['response'],
            sources=rag_result['sources'],
            context_count=rag_result['context_count'],
            game=rag_result['game']
        )
    
    except Exception as e:
        print(f"Error in RAG query endpoint: {e}")
        return RAGQueryResponse(
            response=f"Error: {str(e)}",
            sources=[],
            context_count=0
        )

@app.get("/api/rag/summary/{game}")
async def rag_game_summary(game: str):
    """
    Generate an AI summary of a specific game's lottery data using RAG.
    """
    try:
        summary = await rag_service.generate_summary(game)
        return {
            "game": game,
            "summary": summary,
            "generated_at": time.time()
        }
    except Exception as e:
        print(f"Error generating summary for {game}: {e}")
        return {
            "game": game,
            "summary": f"Error: {str(e)}",
            "error": True
        }

@app.get("/api/rag/comparison")
async def rag_game_comparison():
    """
    Generate a comparison across all games using RAG.
    """
    try:
        comparison = await rag_service.generate_game_comparison()
        return {
            "comparison": comparison,
            "generated_at": time.time()
        }
    except Exception as e:
        print(f"Error generating comparison: {e}")
        return {
            "comparison": f"Error: {str(e)}",
            "error": True
        }

# --- Existing Endpoints ---

@app.get("/api/predictions/all")
async def get_all_predictions():
    return {"message": "Endpoint not fully implemented yet."}

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
