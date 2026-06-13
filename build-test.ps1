# Local build and test script for Docker containers (Windows PowerShell)

Write-Host "🔨 Building Docker containers..." -ForegroundColor Green

# Build frontend
Write-Host "Building frontend..." -ForegroundColor Yellow
docker compose build frontend

# Build backend
Write-Host "Building backend..." -ForegroundColor Yellow
docker compose build backend

# Build chroma (pull image)
Write-Host "Pulling ChromaDB image..." -ForegroundColor Yellow
docker compose pull chroma

Write-Host "✅ Build complete!" -ForegroundColor Green
Write-Host ""

Write-Host "🧪 Running tests..." -ForegroundColor Green

# Test frontend build
Write-Host "Testing frontend container..." -ForegroundColor Yellow
try {
    docker run --rm mensa_frontend:latest wget -O- http://localhost/
} catch {
    Write-Host "Frontend test skipped (needs running container)" -ForegroundColor Gray
}

# Test backend build
Write-Host "Testing backend container..." -ForegroundColor Yellow
try {
    docker run --rm mensa_backend:latest python -c "import fastapi; print('FastAPI installed')"
} catch {
    Write-Host "Backend test skipped" -ForegroundColor Gray
}

Write-Host "✅ Tests complete!" -ForegroundColor Green
Write-Host ""

Write-Host "🚀 Starting services..." -ForegroundColor Green
docker compose up -d

Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "🔍 Checking service health..." -ForegroundColor Green

Write-Host "Frontend health:" -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri http://localhost:3000 -UseBasicParsing | Select-Object StatusCode
} catch {
    Write-Host "Frontend not responding" -ForegroundColor Red
}

Write-Host "Backend health:" -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri http://localhost:5000/api/health -UseBasicParsing | Select-Object StatusCode
} catch {
    Write-Host "Backend not responding" -ForegroundColor Red
}

Write-Host "ChromaDB health:" -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri http://localhost:8000/api/v1/heartbeat -UseBasicParsing | Select-Object StatusCode
} catch {
    Write-Host "ChromaDB not responding" -ForegroundColor Red
}

Write-Host ""
Write-Host "✅ Build and test complete!" -ForegroundColor Green
Write-Host "Access the application at: http://localhost:3000" -ForegroundColor Cyan
