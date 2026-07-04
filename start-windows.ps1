#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Reliable Windows startup for the Mensa Docker stack.

.DESCRIPTION
  - Binds published ports to 127.0.0.1 (see DOCKER_BIND_HOST in .env)
  - Staged compose up: chroma -> backend -> frontend
  - Verifies HTTP from the Windows host and retries on Docker port-forward glitches

.EXAMPLE
  .\start-windows.ps1
  .\start-windows.ps1 -Build
  .\start-windows.ps1 -Recreate
#>
param(
    [switch]$Build,
    [switch]$Recreate,
    [switch]$OpenBrowser,
    [int]$MaxPortWaitSec = 120
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Read-DotEnvValue([string]$Name, [string]$Default) {
    $envPath = Join-Path $PSScriptRoot ".env"
    if (-not (Test-Path $envPath)) { return $Default }
    foreach ($line in Get-Content $envPath) {
        if ($line -match "^\s*$([regex]::Escape($Name))\s*=\s*(.+?)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $Default
}

function Wait-DockerDaemon([int]$MaxSeconds = 180) {
    Write-Step "Waiting for Docker Desktop"
    $elapsed = 0
    while ($elapsed -lt $MaxSeconds) {
        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Docker ready (${elapsed}s)" -ForegroundColor Green
            return $true
        }
        if ($elapsed -eq 30) {
            Write-Host "  Starting Docker Desktop..." -ForegroundColor Yellow
            Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 5
        $elapsed += 5
    }
    throw "Docker daemon not reachable after ${MaxSeconds}s. Open Docker Desktop manually."
}

function Invoke-Compose([string[]]$ComposeArgs) {
    docker compose @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed ($LASTEXITCODE): $($ComposeArgs -join ' ')"
    }
}

function Repair-PortForwarding {
    Write-Step "Repairing Docker port forwarding (Windows)"
    Invoke-Compose @("restart", "backend", "frontend")
    Start-Sleep -Seconds 12
    Invoke-Compose @("up", "-d", "--force-recreate", "frontend")
    Start-Sleep -Seconds 10
}

$bindHost = Read-DotEnvValue "DOCKER_BIND_HOST" "127.0.0.1"
$frontendPort = [int](Read-DotEnvValue "FRONTEND_HOST_PORT" "3000")
$backendPort = [int](Read-DotEnvValue "BACKEND_HOST_PORT" "5001")
$chromaPort = [int](Read-DotEnvValue "CHROMA_HOST_PORT" "8001")

if ([string]::IsNullOrWhiteSpace($bindHost)) { $bindHost = "127.0.0.1" }

Write-Host "Mensa Windows Start" -ForegroundColor White
Write-Host "  bind host : $bindHost"
Write-Host "  ports     : frontend=$frontendPort backend=$backendPort chroma=$chromaPort"
Write-Host "  app URL   : http://${bindHost}:${frontendPort}/" -ForegroundColor Green

. (Join-Path $PSScriptRoot "scripts\Wait-MensaPorts.ps1")

Wait-DockerDaemon | Out-Null

if ($Recreate) {
    Write-Step "Recreating stack"
    Invoke-Compose @("down", "--timeout", "15")
    Start-Sleep -Seconds 2
}

if ($Build) {
    Write-Step "Building images"
    $env:DOCKER_BUILDKIT = "0"
    $env:COMPOSE_DOCKER_CLI_BUILD = "0"
    Invoke-Compose @("build")
}

Write-Step "Starting services (staged)"
Invoke-Compose @("up", "-d", "--force-recreate", "chroma")
Start-Sleep -Seconds 8
Invoke-Compose @("up", "-d", "--force-recreate", "backend")
Start-Sleep -Seconds 15
Invoke-Compose @("up", "-d", "--force-recreate", "frontend")

Write-Step "Verifying host connectivity"
$result = Wait-MensaPorts -FrontendPort $frontendPort -BackendPort $backendPort -BindHost $bindHost -MaxWaitSec $MaxPortWaitSec

if (-not $result.Ok) {
    Repair-PortForwarding
    $result = Wait-MensaPorts -FrontendPort $frontendPort -BackendPort $backendPort -BindHost $bindHost -MaxWaitSec 60
}

if (-not $result.Ok) {
    Write-Host "`nPort forwarding still failing from Windows." -ForegroundColor Red
    Write-Host "Try:" -ForegroundColor Yellow
    Write-Host "  1. Restart Docker Desktop (tray icon -> Restart)"
    Write-Host "  2. Re-run: .\start-windows.ps1 -Recreate"
    Write-Host "  3. Open: http://${bindHost}:${frontendPort}/  (not localhost if IPv6 conflicts)"
    docker compose ps
    exit 1
}

Write-Step "Stack healthy"
docker compose ps
Write-Host "`nApp ready: $($result.FrontendUrl)" -ForegroundColor Green
Write-Host "Use http://${bindHost}:${frontendPort}/ (not localhost) if you see timeouts on Windows." -ForegroundColor Gray

if ($OpenBrowser) {
    Start-Process $result.FrontendUrl
}

exit 0