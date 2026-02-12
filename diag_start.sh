#!/usr/bin/env bash
set -euo pipefail

# === Mensa Project Diagnostic Start Script ===
# This script attempts a minimal startup to get a clear error message from Docker Compose.
# All output is redirected to 'diag_output.log'.
# It does NOT perform any of the safety checks or retries of the main `start.sh`.

LOG_FILE="diag_output.log"

echo "Running a diagnostic startup..."
echo "This will attempt to start all services without any checks or retries."
echo "The goal is to get a clear error message from Docker Compose."
echo "Output is being saved to '${LOG_FILE}' and displayed below."
echo ""

# Create a separator in the log file
echo "" > "${LOG_FILE}"
echo "--- Diagnostic Run at $(date) ---" >> "${LOG_FILE}"
echo "" >> "${LOG_FILE}"

# Determine compose command if not provided by the caller
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

# Stop and remove old containers to ensure a clean start
echo "--- Stopping and removing old containers ---" >> "${LOG_FILE}"
eval "${COMPOSE_CMD} down --remove-orphans" 2>&1 | tee -a "${LOG_FILE}" || true
docker rm -f mensa_frontend mensa_backend mensa_chroma 2>&1 | tee -a "${LOG_FILE}" || true

# Attempt to build and start (detached mode with loop detection)
echo "--- Building and starting new containers ---" >> "${LOG_FILE}"
if ! eval "${COMPOSE_CMD} up -d --build --force-recreate" 2>&1 | tee -a "${LOG_FILE}"; then
    echo ""
    echo "---"
    echo "✗ Diagnostic startup FAILED during docker-compose up."
    echo "An error occurred. Check the end of the '${LOG_FILE}' for details."
    echo "You can view the full log with: cat ${LOG_FILE}"
    echo "---"
    exit 1
fi

# Monitor for restart loops
echo "" >> "${LOG_FILE}"
echo "--- Monitoring for restart loops ---" >> "${LOG_FILE}"
echo "Monitoring containers for restart loops (30 second check)..." | tee -a "${LOG_FILE}"

sleep 5  # Give containers time to start

# Track restart counts
declare -A initial_restart_counts
declare -A final_restart_counts

# Get initial restart counts
for container in mensa_backend mensa_frontend mensa_chroma; do
    restart_count=$(docker inspect --format='{{.RestartCount}}' "${container}" 2>/dev/null || echo "0")
    initial_restart_counts["${container}"]="${restart_count}"
done

# Wait and check again
sleep 25

LOOP_DETECTED=0
for container in mensa_backend mensa_frontend mensa_chroma; do
    if ! docker ps --filter "name=${container}" --format "{{.Names}}" | grep -q "${container}"; then
        echo "✗ ERROR: Container ${container} is not running!" | tee -a "${LOG_FILE}"
        echo "--- LOGS FOR ${container} ---" >> "${LOG_FILE}"
        docker logs "${container}" --tail 50 >> "${LOG_FILE}" 2>&1 || true
        echo "--------------------------------" >> "${LOG_FILE}"
        LOOP_DETECTED=1
        continue
    fi
    
    restart_count=$(docker inspect --format='{{.RestartCount}}' "${container}" 2>/dev/null || echo "0")
    final_restart_counts["${container}"]="${restart_count}"
    initial=${initial_restart_counts["${container}"]}
    
    restarts=$((restart_count - initial))
    
    if [ "${restarts}" -gt 2 ]; then
        echo "✗ ERROR: Container ${container} has restarted ${restarts} times in 30 seconds - RESTART LOOP DETECTED!" | tee -a "${LOG_FILE}"
        echo "--- LOGS FOR ${container} ---" >> "${LOG_FILE}"
        docker logs "${container}" --tail 100 >> "${LOG_FILE}" 2>&1 || true
        echo "--------------------------------" >> "${LOG_FILE}"
        LOOP_DETECTED=1
    elif [ "${restarts}" -gt 0 ]; then
        echo "⚠ Warning: Container ${container} has restarted ${restarts} time(s)" | tee -a "${LOG_FILE}"
    fi
done

if [ ${LOOP_DETECTED} -ne 0 ]; then
    echo "" | tee -a "${LOG_FILE}"
    echo "---" | tee -a "${LOG_FILE}"
    echo "✗ DIAGNOSTIC FAILED: One or more containers are in a restart loop or failed to start." | tee -a "${LOG_FILE}"
    echo "Check the '${LOG_FILE}' for container logs and error details." | tee -a "${LOG_FILE}"
    echo "Common causes:" | tee -a "${LOG_FILE}"
    echo "  - Invalid configuration (check compose.yaml)" | tee -a "${LOG_FILE}"
    echo "  - Missing environment variables" | tee -a "${LOG_FILE}"
    echo "  - Port conflicts" | tee -a "${LOG_FILE}"
    echo "  - Invalid command line arguments" | tee -a "${LOG_FILE}"
    echo "---" | tee -a "${LOG_FILE}"
    eval "${COMPOSE_CMD} down" >> "${LOG_FILE}" 2>&1 || true
    exit 1
fi

echo "" | tee -a "${LOG_FILE}"
echo "---" | tee -a "${LOG_FILE}"
echo "✓ Diagnostic startup appears SUCCESSFUL - no restart loops detected." | tee -a "${LOG_FILE}"
echo "All containers are running normally." | tee -a "${LOG_FILE}"
echo "Check the '${LOG_FILE}' for detailed output." | tee -a "${LOG_FILE}"
echo "---" | tee -a "${LOG_FILE}"
exit 0