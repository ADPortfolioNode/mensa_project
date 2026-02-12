#!/usr/bin/env bash
set -uo pipefail

# === Mensa Project Startup Monitor ===
# Provides real-time startup timing and status visibility
# Includes progress tracking for background ingestion

RESET='\033[0m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'

# Error handler
handle_error() {
    local line=$1
    local code=$2
    echo ""
    echo -e "${RED}✗ ERROR at line $line (exit code $code)${RESET}"
    echo "Check logs with: docker compose logs --tail=100"
    exit "$code"
}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${CYAN}Mensa Project - Startup Monitor${RESET}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# Determine compose command
if [ -z "${COMPOSE_CMD:-}" ]; then
    if docker compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    else
        echo "ERROR: Neither 'docker compose' nor 'docker-compose' commands are available." >&2
        exit 1
    fi
fi

echo -e "${CYAN}Using compose command:${RESET} ${COMPOSE_CMD}"
echo ""

# Overall timer
OVERALL_START_TIME=$(date +%s)

# Phase 1: Stop and clean
echo -e "${YELLOW}[Phase 1]${RESET} Stopping and removing existing containers..."
start_time=$(date +%s)
eval "${COMPOSE_CMD} down --remove-orphans" 2>/dev/null || true
docker rm -f mensa_frontend mensa_backend mensa_chroma 2>/dev/null || true
docker system prune -f 2>/dev/null || true
phase1_duration=$(($(date +%s) - start_time))
echo -e "${GREEN}✓${RESET} Cleaned in ${phase1_duration}s"
echo ""

# Phase 2: Build
echo -e "${YELLOW}[Phase 2]${RESET} Building and starting services..."
echo "  Command: ${COMPOSE_CMD} up -d --build"
start_time=$(date +%s)

BUILD_OUTPUT=$(eval "${COMPOSE_CMD} up -d --build" 2>&1)
BUILD_EXIT=$?

if [ $BUILD_EXIT -ne 0 ]; then
    phase2_duration=$(($(date +%s) - start_time))
    echo -e "${RED}✗ Build and start FAILED after ${phase2_duration}s${RESET}"
    echo ""
    echo "Build output:"
    echo "$BUILD_OUTPUT" | tail -20
    echo ""
    echo "Trying to show container logs for debugging:"
    docker logs mensa_backend --tail=20 2>/dev/null || true
    docker logs mensa_chroma --tail=20 2>/dev/null || true
    docker logs mensa_frontend --tail=20 2>/dev/null || true
    exit 1
fi

phase2_duration=$(($(date +%s) - start_time))
echo -e "${GREEN}✓${RESET} Build and start completed in ${phase2_duration}s"
echo ""

# Phase 3: Wait for health checks
echo -e "${YELLOW}[Phase 3]${RESET} Waiting for services to be healthy..."
start_time=$(date +%s)
max_wait=120
elapsed=0

check_service_health() {
    local service=$1
    local max_retries=30
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        echo -n "." >&2
        
        local ps_output
        ps_output=$(eval "${COMPOSE_CMD} ps" 2>/dev/null || echo "")
        
        if echo "$ps_output" | grep -q "$service.*healthy"; then
            echo -e "${GREEN}✓${RESET} $service is healthy"
            return 0
        fi
        
        # Check if container is dead/exited
        if echo "$ps_output" | grep -qE "$service.*(Exited|Dead)"; then
            echo -e "${RED}✗${RESET} $service container exited unexpectedly"
            echo "Container logs:"
            docker logs "mensa_${service}" --tail=20 2>/dev/null || true
            return 1
        fi
        
        sleep 2
        retry=$((retry + 1))
        local now
        now=$(date +%s)
        elapsed=$((now - start_time))
    done
    
    echo -e "${YELLOW}⚠${RESET} $service not healthy after ${elapsed}s"
    echo "Current status:"
    eval "${COMPOSE_CMD} ps" | grep "$service" || true
    return 1
}

echo ""
echo "Waiting for Chroma..."
check_service_health "chroma" || {
    echo "  Showing chroma logs:"
    docker logs mensa_chroma --tail=50 2>/dev/null || true
    handle_error "${LINENO}" 1
}

echo "Waiting for Backend..."
check_service_health "backend" || {
    echo "  Showing backend logs:"
    docker logs mensa_backend --tail=50 2>/dev/null || true
    handle_error "${LINENO}" 1
}

echo "Waiting for Frontend..."
check_service_health "frontend" || {
    echo "  Showing frontend logs:"
    docker logs mensa_frontend --tail=50 2>/dev/null || true
    echo "  (Frontend health may be slower; continuing...)"
}

phase3_duration=$(($(date +%s) - start_time))
echo -e "${GREEN}✓${RESET} Services checked after ${phase3_duration}s"
echo ""

# Phase 4: Monitor ingestion progress
echo -e "${YELLOW}[Phase 4]${RESET} Monitoring background ingestion..."
start_time=$(date +%s)
phase4_duration=0
last_game=""
max_wait=300
elapsed=0

while [ $elapsed -lt $max_wait ]; do
    status=$(curl -s http://127.0.0.1:5000/api/startup_status 2>/dev/null || echo "")
    
    if [ -z "$status" ]; then
        echo "Waiting for API to be ready..."
        sleep 2
        elapsed=$(($(date +%s) - start_time))
        continue
    fi
    
    if echo "$status" | grep -q '"status":"completed"'; then
        phase4_duration=$(($(date +%s) - start_time))
        echo -e "${GREEN}✓${RESET} Ingestion completed in ${phase4_duration}s"
        break
    fi
    
    current_game=$(echo "$status" | grep -o '"current_game":"[^"]*"' | cut -d'"' -f4)
    progress=$(echo "$status" | grep -o '"progress":[0-9]*' | cut -d':' -f2)
    total=$(echo "$status" | grep -o '"total":[0-9]*' | cut -d':' -f2)
    
    if [ -n "$current_game" ] && [ "$current_game" != "$last_game" ]; then
        elapsed=$(($(date +%s) - start_time))
        echo -e "  ${CYAN}[${elapsed}s]${RESET} Ingesting: ${current_game} (${progress}/${total})"
        last_game="$current_game"
    fi
    
    elapsed=$(($(date +%s) - start_time))
    sleep 1
done

# Ensure phase4_duration is set
if [ "${phase4_duration}" = "0" ]; then
    phase4_duration=$(($(date +%s) - start_time))
fi

echo ""

# Phase 5: Final status
echo -e "${YELLOW}[Phase 5]${RESET} Container status:"
eval "${COMPOSE_CMD} ps"
echo ""

total_duration=$(($(date +%s) - OVERALL_START_TIME))
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}✓ Startup Complete${RESET}"
echo ""
echo -e "Timeline:"
echo -e "  Phase 1 (Cleanup):    ${phase1_duration}s"
echo -e "  Phase 2 (Build):      ${phase2_duration}s"
echo -e "  Phase 3 (Health):     ${phase3_duration}s"
echo -e "  Phase 4 (Ingest):     ${phase4_duration}s"
echo -e "  ${CYAN}────────────────${RESET}"
echo -e "  Total elapsed:        ${total_duration}s"
echo ""
echo -e "Access your application:"
echo -e "  Frontend: ${CYAN}http://localhost:3000${RESET}"
echo -e "  Backend:  ${CYAN}http://localhost:5000/api${RESET}"
echo -e "  Chroma:   ${CYAN}http://localhost:8000/api/v1/heartbeat${RESET}"
echo ""
echo -e "View logs:"
echo -e "  Backend:  ${CYAN}${COMPOSE_CMD} logs -f backend${RESET}"
echo -e "  Frontend: ${CYAN}${COMPOSE_CMD} logs -f frontend${RESET}"
echo -e "  All:      ${CYAN}${COMPOSE_CMD} logs -f${RESET}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
