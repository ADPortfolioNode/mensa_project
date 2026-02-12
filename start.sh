#!/usr/bin/env bash
set -euxo pipefail

# === Mensa Project Robust Start Script ===
# Performs a safe reset and robust startup for development.
# Usage: ./start.sh [--prune] [--yes] [--no-ingest-wait] [--build] [--diag] [--monitor-startup] [--monitor-progress]
#   --prune          : run `docker system prune -a -f` and `docker volume prune -f` before starting
#   --yes            : auto-confirm prune (implies --prune)
#   --no-ingest-wait : start containers but do not wait for data ingestion to complete.
#   --build          : force a rebuild of the docker images
#   --diag           : run a diagnostic-only startup, logging all output to 'diag_output.log'
#   --monitor-startup: run monitor_startup.sh when docker-compose is available
#   --monitor-progress: use monitor_progress.* after startup (prefers .sh, then .py, then .ps1)

# --- Helper Functions ---

choose_compose_command() {
    # Prefer 'docker compose' (v2) but fall back to 'docker-compose' (v1)
    if docker compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    else
        echo "ERROR: Neither 'docker compose' nor 'docker-compose' commands are available." >&2
        echo "Install Docker Compose (v2 is recommended) or ensure it's on PATH." >&2
        exit 1
    fi
    echo "Using compose command: ${COMPOSE_CMD}"
}

check_docker_version() {
    echo "Checking Docker environment..."
    
    if ! command -v docker &> /dev/null; then
        echo "ERROR: 'docker' command not found." >&2
        echo "Please ensure Docker is installed and that the 'docker' command is in your system's PATH." >&2
        exit 1
    fi

    echo "Pinging Docker daemon..."
    if ! docker info >/dev/null 2>&1; then
        echo "ERROR: Could not connect to the Docker daemon." >&2
        echo "Please ensure the Docker Desktop application is running." >&2
        exit 1
    fi
    echo "✓ Docker daemon is responsive."

    local client_ver server_ver
    client_ver=$(docker version --format '{{.Client.APIVersion}}' 2>/dev/null)
    server_ver=$(docker version --format '{{.Server.APIVersion}}' 2>/dev/null)

    if [ -z "${client_ver}" ] || [ -z "${server_ver}" ]; then
        echo "WARNING: Could not determine Docker client/server API version."
        echo "This can happen if Docker is not running or is not installed correctly."
        echo "The script will attempt to continue, but may fail."
        echo ""
        return
    fi

    local client_major server_major
    client_major=$(echo "$client_ver" | cut -d. -f1-2)
    server_major=$(echo "$server_ver" | cut -d. -f1-2)

    if [ "$client_major" != "$server_major" ]; then
        echo "ERROR: Docker client and server API versions are mismatched."
        echo "  Client API: $client_ver"
        echo "  Server API: $server_ver"
        echo "This can cause unexpected errors. Please see TROUBLESHOOTING_DOCKER_ERROR.txt for instructions on how to resolve this."
        exit 1
    fi
    echo "✓ Docker version check passed (Client: $client_ver, Server: $server_ver)."
}

run_compose_up_with_retries() {
    local attempts=3
    local delay=20 # Increased delay
    for i in $(seq 1 ${attempts}); do
        echo "Attempt ${i}/${attempts}: bring up compose stack"

        # If BUILD requested, run an explicit build step first (supports --no-cache)
        if [ "${BUILD}" = true ]; then
            echo "Building images (no-cache)..."
            if ! eval "${COMPOSE_CMD} build --no-cache"; then
                echo "Compose build failed; retrying in ${delay}s..."
                sleep ${delay}
                delay=$((delay * 2))
                continue
            fi
        fi

        echo "Starting services..."
        if eval "${COMPOSE_CMD} up -d --force-recreate"; then
            return 0
        fi

        echo "Compose up failed; retrying in ${delay}s..."
        sleep ${delay}
        delay=$((delay * 2))
    done
    return 1
}

confirm_prune() {
    if [ "${AUTOMATIC_YES}" = true ]; then
        return 0
    fi
    read -r -p "This will remove ALL unused containers, networks, images, and volumes. Continue? [y/N] " answer
    case "${answer}" in
        [Yy]*) return 0 ;;
        *) return 1 ;;
    esac
}

run_prune() {
    echo "Pruning system images and volumes..."
    if ! docker system prune -a -f; then
        echo "WARNING: 'docker system prune' failed. This might be due to a Docker API error."
        echo "See TROUBLESHOOTING_DOCKER_ERROR.txt for help."
        echo "Continuing with startup..."
    fi
    if ! docker volume prune -f; then
        echo "WARNING: 'docker volume prune' failed. This might be due to a Docker API error."
        echo "See TROUBLESHOOTING_DOCKER_ERROR.txt for help."
        echo "Continuing with startup..."
    fi
}

# --- Main Script ---

PRUNE=false
AUTOMATIC_YES=false
WAIT_FOR_INGEST=true
BUILD=false
DIAG_RUN=false
MONITOR_STARTUP=false
MONITOR_PROGRESS=false

while [[ ${#} -gt 0 ]]; do
    case "$1" in
        --prune) PRUNE=true; shift ;;
        --yes) PRUNE=true; AUTOMATIC_YES=true; shift ;;
        --no-ingest-wait) WAIT_FOR_INGEST=false; shift ;;
        --build) BUILD=true; shift ;;
        --diag) DIAG_RUN=true; shift ;;
        --monitor-startup) MONITOR_STARTUP=true; shift ;;
        --monitor-progress) MONITOR_PROGRESS=true; shift ;;
        -h|--help) echo "Usage: $0 [--prune] [--yes] [--no-ingest-wait] [--build] [--diag]"; exit 0 ;;
        *) echo "Unknown arg: $1"; echo "Usage: $0 [--prune] [--yes] [--no-ingest-wait] [--build] [--diag]"; exit 2 ;;
    esac
done

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

run_external_progress_monitor() {
    if [ -f "./monitor_progress.sh" ] && command_exists curl; then
        ./monitor_progress.sh
        return $?
    fi

    if [ -f "./monitor_progress.py" ]; then
        if command_exists python3; then
            python3 ./monitor_progress.py
            return $?
        fi
        if command_exists python; then
            python ./monitor_progress.py
            return $?
        fi
    fi

    if [ -f "./monitor_progress.ps1" ] && command_exists pwsh; then
        pwsh -File ./monitor_progress.ps1
        return $?
    fi

    echo "WARNING: No compatible progress monitor found; using built-in monitor." >&2
    monitor_ingestion_progress
}

# --- Execution Flow ---

if [ "${MONITOR_STARTUP}" = true ]; then
    check_docker_version
    if [ -f "./monitor_startup.sh" ]; then
        export COMPOSE_CMD
        if ! ./monitor_startup.sh; then
            echo ""
            echo "ERROR: Startup monitor failed. Try manual startup:" >&2
            echo "  docker compose up --build" >&2
            echo ""
            echo "To see detailed errors:" >&2
            echo "  docker compose logs --tail=100" >&2
            exit 1
        fi
        exit 0
    else
        echo "ERROR: monitor_startup.sh not found in root directory" >&2
        exit 1
    fi
fi

echo "Starting Mensa Project (robust mode)..."
echo ""

if [ -f "./diag_output.log" ]; then
    echo "NOTE: A 'diag_output.log' file was found. If you are having issues,"
    echo "check this file for errors from the last diagnostic run."
    echo ""
fi

# 1. Check Docker environment first
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1/5: Checking Docker environment..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_docker_version
choose_compose_command
echo ""

# 2. Prune if requested
if [ "${PRUNE}" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Step 2/5: Pruning old containers and images..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if confirm_prune; then
        run_prune
    else
        echo "Skipping prune."
    fi
    echo ""
else
    echo "Step 2/5: Skipping prune (--no-prune)"
    echo ""
fi

if [ "${DIAG_RUN}" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Diagnostic Mode Requested"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    export COMPOSE_CMD
    if [ -f "./diag_start.sh" ]; then
        exec bash ./diag_start.sh
    else
        echo "ERROR: diag_start.sh not found. Cannot run diagnostics." >&2
        exit 1
    fi
fi

# 3. Install frontend dependencies on the host (only when useful)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3/5: Checking frontend dependencies..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "frontend" ]; then
    # If we are rebuilding images, the Docker build will handle frontend; skip host npm install.
    if [ "${BUILD}" = true ]; then
        echo "BUILD requested: skipping host 'npm' install; Docker build will handle frontend.";
    else
        if [ -d "frontend/build" ]; then
            echo "Frontend build exists (frontend/build). Skipping host 'npm' install."
        else
            echo "No frontend build found — running 'npm ci' in frontend/ to speed local dev iteration."
            if (cd frontend && npm ci); then
                echo "✓ Frontend dependencies installed (host)."
            else
                echo "WARNING: 'npm ci' in frontend/ failed. Continuing; you can run 'npm ci' manually." >&2
            fi
        fi
    fi
fi
echo ""

# 4. Stop and remove old containers and orphans
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4/5: Stopping old containers..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Stopping and removing any old containers..."
eval "${COMPOSE_CMD} down --remove-orphans" || true
echo ""

# 4. Build and start services
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5/5: Building and starting services..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "This may take a few minutes on first run..."
if ! run_compose_up_with_retries; then
    echo ""
    echo "ERROR: docker-compose failed after retries. This is often a Docker environment issue." >&2
    echo "Suggestion: Restart Docker Desktop and try again." >&2
    echo "For a detailed error log, run this script with the --diag flag: ./start.sh --diag" >&2
    exit 1
fi
echo ""

# Helper to check a service readiness
wait_for_service() {
    local svc_name="$1"
    local container_name="mensa_${svc_name}"
    local max_checks=${2:-30}
    local interval=${3:-5}
    echo "Waiting for ${svc_name} to be running/healthy (timeout ${max_checks}*${interval}s)..."
    
    for i in $(seq 1 ${max_checks}); do
        local container
        container=$(docker ps -a --filter "name=${container_name}" --format "{{.Names}}" | head -n1 || true)
        if [ -z "${container}" ]; then
            echo "  ${svc_name} -> container not found yet..."
            sleep ${interval}
            continue
        fi

        local status
        status=$(docker ps -a --filter "name=${container}" --format "{{.Status}}" | head -n1 || true)

        if echo "${status}" | grep -qE "Exited|Dead"; then
            echo "✗ ERROR: ${svc_name} container (${container}) has exited unexpectedly." >&2
            echo "--- LOGS FOR ${container} ---" >&2
            docker logs "${container}" --tail 100 || true
            echo "--------------------------------" >&2
            return 1
        fi

        # Check health if present
        local health
        health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "${container}" 2>/dev/null || true)
        if [ -n "${health}" ]; then
            if [ "${health}" = "healthy" ]; then
                echo "✓ ${svc_name} -> ${container} is healthy."
                return 0
            fi
            echo "  ${svc_name} -> ${container} health is '${health}'..."
            sleep ${interval}
            continue
        fi

        # Fallback: consider 'Up' status as ready if no healthcheck
        if echo "${status}" | grep -iq "Up"; then
            echo "✓ ${svc_name} -> ${container} is Up (no healthcheck)."
            return 0
        fi

        echo "  ${svc_name} -> ${container} status is '${status}'..."
        sleep ${interval}
    done

    echo "✗ ERROR: Timed out waiting for ${svc_name} to become ready." >&2
    echo "--- STATUS OF ${container_name} ---" >&2
    docker ps -a --filter "name=${container_name}" >&2
    echo "--- LOGS FOR ${container_name} ---" >&2
    docker logs "${container_name}" --tail 100 || true
    echo "------------------------------------" >&2
    return 1
}


# --- Ingestion Monitoring ---

# Prints a progress bar. Args: progress, total
_print_progress_bar() {
    local progress=$1
    local total=$2
    local width=40
    
    if (( total <= 0 )); then
        local percentage=0
        local filled=0
    else
        local percentage=$((progress * 100 / total))
        local filled=$((progress * width / total))
    fi
    
    local empty=$((width - filled))
    printf "["
    printf "%.0s█" $(seq 1 $filled)
    printf "%.0s░" $(seq 1 $empty)
    printf "] %d/%d (%d%%)\n" "$progress" "$total" "$percentage"
}

# Polls the backend API for ingestion status
monitor_ingestion_progress() {
    local api_endpoint="http://127.0.0.1:5000/api/startup_status"
    local max_retries=15 # wait for ~30s for API to appear
    local retries=0
    echo ""
    echo "---"
    echo "Waiting for backend API..."

    # 1. Wait for the API to be available
    while ! curl -s -f "${api_endpoint}" > /dev/null; do
        if [[ ${retries} -ge ${max_retries} ]]; then
            echo "✗ ERROR: Timed out waiting for backend API at ${api_endpoint}" >&2
            echo "Run '${COMPOSE_CMD} logs backend' to investigate." >&2
            return 1
        fi
        retries=$((retries+1))
        sleep 2
    done
    echo "✓ Backend API is responsive. Starting ingestion monitoring."
    echo ""

    # 2. Poll for ingestion status
    local start_time
    start_time=$(date +%s)
    local printed_lines=0
    while true; do
        local response
        response=$(curl -s "${api_endpoint}")
        local status
        status=$(echo "${response}" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

        if [ -z "${status}" ]; then
            echo "WARNING: Could not parse status from API response. Retrying..."
            sleep 3
            continue
        fi

        # Clear previous lines and print new status
        if [[ ${printed_lines} -gt 0 ]]; then
          for i in $(seq 1 ${printed_lines}); do echo -e -n "\033[F\033[K"; done
        fi
        
        local progress total current_game current_task
        progress=$(echo "${response}" | grep -o '"progress":[0-9]*' | cut -d':' -f2 | sed 's/,//g' || echo 0)
        total=$(echo "${response}" | grep -o '"total":[0-9]*' | cut -d':' -f2 | sed 's/,//g' || echo 1)
        current_game=$(echo "${response}" | grep -o '"current_game":"[^"]*"' | cut -d'"' -f4)
        current_task=$(echo "${response}" | grep -o '"current_task":"[^"]*"' | cut -d'"' -f4)

        echo "Data Ingestion Status: [${status}]"
        _print_progress_bar "${progress:-0}" "${total:-1}"
        echo "Current Task: ${current_game} - ${current_task}"
        echo "(Use Ctrl+C to stop waiting. The app will continue in the background.)"
        printed_lines=4

        if [ "${status}" = "completed" ]; then
            local end_time
            end_time=$(date +%s)
            local elapsed=$((end_time - start_time))
            echo ""
            echo "✓ Data ingestion complete! (took ${elapsed}s)"
            return 0
        fi

        if [ "${status}" = "failed" ]; then
            echo "✗ ERROR: Data ingestion failed. Check backend logs for details." >&2
            echo "  docker-compose logs backend" >&2
            return 1
        fi

        sleep 2
    done
}


# --- Startup Sequence ---

# 5. Wait for key services
echo ""
echo "Verifying service readiness..."
SERVICES_TO_WAIT=(chroma backend frontend)
FAILED=0
for svc in "${SERVICES_TO_WAIT[@]}"; do
    if ! wait_for_service "${svc}" 12 5; then
        echo ""
        echo "ERROR: Service '${svc}' failed to start." >&2
        FAILED=1
    fi
done

if [ ${FAILED} -ne 0 ]; then
    echo ""
    echo "One or more services failed to become healthy. Check logs above." >&2
    echo "For a more detailed log, try running with the --diag flag: ./start.sh --diag" >&2
    echo "Then inspect the generated 'diag_output.log' file." >&2
    exit 2
fi
echo "✓ All services are running."


# 6. Monitor ingestion or print next steps
if [ "${WAIT_FOR_INGEST}" = true ]; then
    if [ "${MONITOR_PROGRESS}" = true ]; then
        if ! run_external_progress_monitor; then
            exit 1
        fi
    else
        if ! monitor_ingestion_progress; then
            exit 1
        fi
    fi
else
    echo ""
    echo "---"
    echo "✓ Services are running. Not waiting for data ingestion due to --no-ingest-wait flag."
    echo "The application may not be fully functional until ingestion completes."
    echo "To monitor progress, run: ./monitor_progress.sh"
    if [ "${MONITOR_PROGRESS}" = true ]; then
        run_external_progress_monitor || exit 1
    fi
fi


# 7. Show final status and next steps
echo ""
echo "================================================="
echo "✓ Mensa Project Started Successfully"
echo "================================================="
echo ""
echo "Container Status:"
eval "${COMPOSE_CMD} ps"
echo ""
echo "Access your application:"
echo "  Frontend: http://localhost:3000"
echo "  Backend API: http://localhost:5000/api"
echo ""
echo "To view live logs from all services, run:" 
echo "  ${COMPOSE_CMD} logs -f"
echo ""
