"""
Mensa Project - FastAPI Application Bootstrap
Simplified main.py for application initialization and route registration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import routes
from routes import health, games, models, chroma, ingestion, predictions, training, experiments, chat
# Import middleware
from middleware.rate_limit import rate_limit_middleware
# Import state management
from state.ingestion_worker import start_background_ingestion


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    print("🚀 Mensa Project backend starting up...")
    
    # Audit LM connections on startup
    try:
        from services.lm_router import lm_router
        snapshot = await lm_router.audit_connections(force=True)
        ordered = snapshot.get("ordered_available", [])
        print(f"LM audit complete. Available providers (fastest first): {ordered}")
    except Exception as exc:
        print(f"LM audit failed at startup: {exc}")
    
    yield
    
    # Shutdown
    print("👋 Mensa Project backend shutting down...")


# Create FastAPI application
app = FastAPI(lifespan=lifespan)


# Register middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(rate_limit_middleware)


# Register routes
app.include_router(health.router)
app.include_router(games.router)
app.include_router(models.router)
app.include_router(chroma.router)
app.include_router(ingestion.router)
app.include_router(predictions.router)
app.include_router(training.router)
app.include_router(experiments.router)
app.include_router(chat.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)