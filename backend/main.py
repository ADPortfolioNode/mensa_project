from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import your Gemini client
from services.gemini_client import gemini_client

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
    return {"message": "Endpoint not implemented yet."}

@app.post("/api/ingest")
async def ingest_data():
    return {"message": "Endpoint not implemented yet."}

@app.post("/api/train")
async def train_model():
    return {"message": "Endpoint not implemented yet."}

@app.get("/api/experiments")
async def get_experiments():
    return {"message": "Endpoint not implemented yet."}

@app.get("/api/games/{game}/prediction")
async def get_game_prediction(game: str):
    return {"message": f"Endpoint for game {game} not implemented yet."}

@app.get("/api/games/{game}/summary")
async def get_game_summary(game: str):
    return {"message": f"Endpoint for game {game} not implemented yet."}

@app.get("/api/startup_status")
async def get_startup_status():
    return {"status": "completed", "progress": 100, "total": 0, "current_game": None, "current_task": None, "games": {}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
