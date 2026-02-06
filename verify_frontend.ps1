#!/usr/bin/env pwsh
# Frontend Verification Script

Write-Host "`n=== MENSA PROJECT FRONTEND VERIFICATION ===" -ForegroundColor Cyan

# Test 1: Check containers running
Write-Host "`n[1] Checking containers..." -ForegroundColor Yellow
$containers = docker ps --filter "name=mensa" --format "{{.Names}}:{{.Status}}"
foreach ($c in $containers) {
    if ($c -match "unhealthy") {
        Write-Host "    ⚠️  $c" -ForegroundColor Yellow
    } else {
        Write-Host "    ✓ $c" -ForegroundColor Green
    }
}

# Test 2: API Health endpoint
Write-Host "`n[2] Testing /api/health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        $body = $response.Content | ConvertFrom-Json
        Write-Host "    ✓ Health OK: $($body.status)" -ForegroundColor Green
    } else {
        Write-Host "    ✗ Unexpected status: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "    ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: API Games endpoint
Write-Host "`n[3] Testing /api/games endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/games" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        $body = $response.Content | ConvertFrom-Json
        Write-Host "    ✓ Games loaded: $($body.Count) games" -ForegroundColor Green
        $body | ForEach-Object { Write-Host "       - $_" }
    } else {
        Write-Host "    ✗ Unexpected status: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "    ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Startup Status endpoint
Write-Host "`n[4] Testing /api/startup_status endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/startup_status" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        $body = $response.Content | ConvertFrom-Json
        Write-Host "    ✓ Status: $($body.status)" -ForegroundColor Green
        Write-Host "       Progress: $($body.progress)/$($body.total)" -ForegroundColor Cyan
    } else {
        Write-Host "    ✗ Unexpected status: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "    ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Chroma Collections endpoint
Write-Host "`n[5] Testing /api/chroma/collections endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/chroma/collections" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        $body = $response.Content | ConvertFrom-Json
        Write-Host "    ✓ Collections loaded: $($body.collections.Count) collections" -ForegroundColor Green
    } else {
        Write-Host "    ✗ Unexpected status: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "    ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: Check frontend HTML loads
Write-Host "`n[6] Testing frontend HTML..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        if ($response.Content -match 'root') {
            Write-Host "    ✓ React app HTML loads" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  HTML loads but missing React root element" -ForegroundColor Yellow
        }
    } else {
        Write-Host "    ✗ Unexpected status: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "    ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== VERIFICATION COMPLETE ===" -ForegroundColor Cyan
Write-Host "Open browser to: http://localhost:3000" -ForegroundColor Green
Write-Host "Test workflows:" -ForegroundColor Green
Write-Host "  1. Dashboard loads without errors" -ForegroundColor Gray
Write-Host "  2. Game selector shows all 8 games" -ForegroundColor Gray
Write-Host "  3. ChromaDB Collections Status panel loads" -ForegroundColor Gray
Write-Host "  4. Click 'Start Initialization' to begin data ingestion" -ForegroundColor Gray
Write-Host "`n"
