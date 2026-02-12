#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Mensa Project Startup Script (PowerShell)
.DESCRIPTION
    Comprehensive startup script for Windows with Docker Desktop diagnostics
.PARAMETER Build
    Force rebuild of Docker images
.PARAMETER Prune
    Prune unused Docker resources before starting
.PARAMETER NoBuild
    Skip build and use existing images
.PARAMETER Monitor
    Show detailed progress monitoring
#>

param(
    [switch]$Build,
    [switch]$Prune,
    [switch]$NoBuild,
    [switch]$Monitor
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

# Colors
function Write-Success { param($Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Error { param($Message) Write-Host "✗ $Message" -ForegroundColor Red }
function Write-Warning { param($Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Info { param($Message) Write-Host "→ $Message" -ForegroundColor Cyan }
function Write-Header { param($Message) Write-Host "`n$('='*70)`n$Message`n$('='*70)" -ForegroundColor Blue }

# Check Docker availability
function Test-DockerDaemon {
    Write-Header "Checking Docker Daemon"
    
    Write-Info "Checking if Docker command is available..."
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker command not found"
        Write-Host "`nPlease install Docker Desktop from:"
        Write-Host "https://www.docker.com/products/docker-desktop" -ForegroundColor Cyan
        return $false
    }
    Write-Success "Docker command found"
    
    Write-Info "Pinging Docker daemon..."
    $startTime = Get-Date
    try {
        $null = docker version --format '{{.Server.Version}}' 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Docker daemon not responding"
        }
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        Write-Success "Docker daemon is responsive ($([math]::Round($elapsed, 1))s)"
        return $true
    }
    catch {
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        Write-Error "Docker daemon not responding (timeout after $([math]::Round($elapsed, 1))s)"
        Write-Host "`n" -NoNewline
        Write-Warning "Docker Desktop may not be running or is stuck"
        Write-Host "`nTroubleshooting steps:"
        Write-Host "1. Open Docker Desktop application"
        Write-Host "2. Wait for it to fully start (icon in system tray should be green)"
        Write-Host "3. If stuck, restart Docker Desktop:"
        Write-Host "   - Right-click Docker icon in tray → Quit Docker Desktop"
        Write-Host "   - Wait 10 seconds"
        Write-Host "   - Start Docker Desktop again"
        Write-Host "4. If still failing, restart your computer"
        return $false
    }
}

# Check if Docker Compose is available
function Get-ComposeCommand {
    if (docker compose version 2>$null) {
        if ($LASTEXITCODE -eq 0) {
            return "docker compose"
        }
    }
    
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        return "docker-compose"
    }
    
    Write-Error "Neither 'docker compose' nor 'docker-compose' found"
    return $null
}

# Main startup
function Start-MensaProject {
    $totalStart = Get-Date
    
    Clear-Host
    Write-Host "`n"
    Write-Host "╔════════════════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║       MENSA PROJECT - STARTUP SCRIPT              ║" -ForegroundColor Blue
    Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
    
    # Step 1: Check Docker
    if (-not (Test-DockerDaemon)) {
        Write-Host "`n"
        Write-Error "Cannot start - Docker is not available"
        exit 1
    }
    
    # Get compose command
    Write-Info "Detecting Docker Compose command..."
    $composeCmd = Get-ComposeCommand
    if (-not $composeCmd) {
        Write-Error "Docker Compose not found"
        exit 1
    }
    Write-Success "Using: $composeCmd"
    Write-Host ""
    
    # Step 2: Prune if requested
    if ($Prune) {
        Write-Header "Pruning Docker Resources"
        Write-Info "Removing unused containers, networks, images..."
        
        docker system prune -f 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Pruned successfully"
        } else {
            Write-Warning "Prune had issues (continuing anyway)"
        }
        Write-Host ""
    }
    
    # Step 3: Stop old containers
    Write-Header "Stopping Old Containers"
    Write-Info "Running: $composeCmd down --remove-orphans"
    
    $downOutput = & $composeCmd.Split() down --remove-orphans 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Old containers stopped"
    } else {
        Write-Warning "Error stopping containers (might be none running)"
        Write-Host $downOutput -ForegroundColor DarkGray
    }
    Write-Host ""
    
    # Step 4: Build and start
    Write-Header "Building and Starting Services"
    
    $buildArgs = @("up", "-d")
    if ($Build -and -not $NoBuild) {
        $buildArgs += "--build"
        Write-Info "Build mode: Forcing rebuild"
    } elseif (-not $NoBuild) {
        $buildArgs += "--build"
        Write-Info "Build mode: Build if needed"
    } else {
        Write-Info "Build mode: Using existing images"
    }
    
    Write-Info "Running: $composeCmd $($buildArgs -join ' ')"
    Write-Host ""
    
    $buildStart = Get-Date
    
    if ($Monitor) {
        # Show output in real-time
        & $composeCmd.Split() @buildArgs
    } else {
        # Capture output
        $output = & $composeCmd.Split() @buildArgs 2>&1
        $output | ForEach-Object {
            $line = $_.ToString()
            if ($line -match "error|fail|fatal") {
                Write-Host $line -ForegroundColor Red
            } elseif ($line -match "warning|warn") {
                Write-Host $line -ForegroundColor Yellow
            } elseif ($line -match "Building|Pulling|Starting") {
                Write-Host $line -ForegroundColor Cyan
            } else {
                Write-Host $line -ForegroundColor DarkGray
            }
        }
    }
    
    $buildElapsed = ((Get-Date) - $buildStart).TotalSeconds
    Write-Host ""
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Build/start failed after $([math]::Round($buildElapsed, 1))s"
        Write-Host "`nShowing container logs for debugging:" -ForegroundColor Yellow
        Write-Host ""
        
        @("mensa_backend", "mensa_chroma", "mensa_frontend") | ForEach-Object {
            $container = $_
            Write-Host "--- $container ---" -ForegroundColor Cyan
            docker logs $container --tail 20 2>&1 | Out-String | Write-Host
            Write-Host ""
        }
        
        exit 1
    }
    
    Write-Success "Containers started in $([math]::Round($buildElapsed, 1))s"
    Write-Host ""
    
    # Step 5: Check container status
    Write-Header "Verifying Container Status"
    Write-Host ""
    
    & $composeCmd.Split() ps
    
    Write-Host ""
    
    # Summary
    $totalElapsed = ((Get-Date) - $totalStart).TotalSeconds
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║            STARTUP COMPLETE                        ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "Total time: $([math]::Round($totalElapsed, 1))s" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Access your application:" -ForegroundColor White
    Write-Host "  Frontend: " -NoNewline; Write-Host "http://localhost:3000" -ForegroundColor Cyan
    Write-Host "  Backend:  " -NoNewline; Write-Host "http://localhost:5000/api" -ForegroundColor Cyan
    Write-Host "  Chroma:   " -NoNewline; Write-Host "http://localhost:8000" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "View logs:" -ForegroundColor White
    Write-Host "  $composeCmd logs -f" -ForegroundColor Gray
    Write-Host ""
}

# Run
Start-MensaProject
