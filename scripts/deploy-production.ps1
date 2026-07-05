# Deploy Mensa on Windows Server (or dev) using production distribution compose.
param(
    [ValidateSet("tls", "direct")]
    [string]$Mode = "tls",
    [switch]$BuildLocal
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$EnvFile = ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item ".env.production.example" $EnvFile
    Write-Host "Created $EnvFile — edit DOMAIN, ACME_EMAIL, API keys, then re-run."
    exit 1
}

# Load .env for validation (simple KEY=VALUE parser)
$EnvVars = @{}
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line -match '^([^=]+)=(.*)$') {
        $EnvVars[$Matches[1]] = $Matches[2]
    }
}

$CaddyProfile = if ($EnvVars["CADDY_PROFILE"]) { $EnvVars["CADDY_PROFILE"] } else { "tls" }
$Domain = $EnvVars["DOMAIN"]
$BasicAuthHash = $EnvVars["BASIC_AUTH_HASH"]

$ComposeArgs = @("-f", "docker-compose.distribution.yml")
$BuildLocal = $BuildLocal -or ($EnvVars["BUILD_LOCAL"] -eq "1")
if ($BuildLocal) {
    $ComposeArgs += @("-f", "docker-compose.distribution.build.yml")
    Write-Host "Local build mode (images built on this server)"
}
if ($Mode -eq "direct") {
    $ComposeArgs += @("-f", "docker-compose.direct.yml")
    $Bind = if ($EnvVars["FRONTEND_BIND"]) { $EnvVars["FRONTEND_BIND"] } else { "127.0.0.1" }
    $Port = if ($EnvVars["FRONTEND_PORT"]) { $EnvVars["FRONTEND_PORT"] } else { "3000" }
    Write-Host "Direct HTTP mode (no Caddy). Frontend: http://${Bind}:${Port}"
} else {
    $ComposeArgs += @("--profile", "tls")
    if (-not $Domain) {
        Write-Host "ERROR: DOMAIN is required for TLS mode. Set it in .env"
        exit 1
    }
    if ($CaddyProfile -eq "subscribers" -and -not $BasicAuthHash) {
        Write-Host "ERROR: CADDY_PROFILE=subscribers requires BASIC_AUTH_HASH in .env"
        Write-Host "Generate: docker run --rm caddy:2-alpine caddy hash-password --plaintext 'your-password'"
        exit 1
    }
    $CaddyFile = "deploy/caddy/Caddyfile.$CaddyProfile"
    if (-not (Test-Path $CaddyFile)) {
        Write-Host "ERROR: $CaddyFile not found"
        exit 1
    }
    Write-Host "TLS mode — https://$Domain (Caddy profile: $CaddyProfile)"
}

$Registry = if ($EnvVars["MENSA_REGISTRY"]) { $EnvVars["MENSA_REGISTRY"] } else { "ghcr.io/adportfolionode" }
$Version = if ($EnvVars["MENSA_VERSION"]) { $EnvVars["MENSA_VERSION"] } else { "latest" }
if ($BuildLocal) {
    Write-Host "Building images locally..."
    docker compose @ComposeArgs build
} else {
    Write-Host "Pulling images (registry=$Registry, version=$Version)..."
    docker compose @ComposeArgs pull
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "WARN: Registry pull failed (private GHCR or no release yet)."
        Write-Host "      Retry with: .\scripts\deploy-production.ps1 -BuildLocal"
        exit 1
    }
}

docker compose @ComposeArgs up -d
docker compose @ComposeArgs ps

if ($Mode -eq "direct") {
    $Bind = if ($EnvVars["FRONTEND_BIND"]) { $EnvVars["FRONTEND_BIND"] } else { "127.0.0.1" }
    $Port = if ($EnvVars["FRONTEND_PORT"]) { $EnvVars["FRONTEND_PORT"] } else { "3000" }
    Write-Host ""
    Write-Host "Health: curl -fsS http://${Bind}:${Port}/api/health"
} else {
    Write-Host ""
    Write-Host "Health: curl -fsS https://$Domain/api/health"
}