"""
Rate limiting middleware for API endpoints.
"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException


_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 100  # per window per IP


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware that limits requests per IP address.
    Skips rate limiting for health checks, status polling, and game summary endpoints.
    """
    # Skip rate limiting for health checks, status polling, and game data endpoints
    skip_paths = [
        "/api/health",
        "/api/startup_status",
        "/api/experiments",
        "/api/ingest_stream",
        "/api/games",
        "/api/games/summaries",
    ]
    # Also skip paths that start with certain prefixes
    skip_prefixes = ["/api/games/"]
    
    if request.url.path in skip_paths or any(request.url.path.startswith(prefix) for prefix in skip_prefixes):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old entries
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if t > window_start
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Limit: {RATE_LIMIT_MAX_REQUESTS} per {RATE_LIMIT_WINDOW}s",
                "retry_after_seconds": int(RATE_LIMIT_WINDOW),
            },
        )

    _rate_limit_store[client_ip].append(now)
    response = await call_next(request)
    return response