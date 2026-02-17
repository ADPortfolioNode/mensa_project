#!/usr/bin/env bash
set -eu

# === Mensa Project Diagnostic Start Script ===
# This script attempts a minimal startup to get a clear error message from docker-compose.
# All output is redirected to 'diag_output.log'.
# It does NOT perform any of the safety checks or retries of the main `start.sh`.

LOG_FILE="diag_output.log"

choose_compose_command() {
    if docker compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    else
        echo "ERROR: Neither 'docker compose' nor 'docker-compose' commands are available." >&2
        exit 1
    fi
}

configure_build_backend() {
    if [ "${FORCE_BUILDKIT:-false}" = "true" ]; then
        export DOCKER_BUILDKIT=1
        export COMPOSE_DOCKER_CLI_BUILD=1
    else
        export DOCKER_BUILDKIT=0
        export COMPOSE_DOCKER_CLI_BUILD=0
    fi
}

configure_backend_cache_buster() {
    local ts
    ts=$(date +%s)
    export BACKEND_CACHE_BUSTER="diag-${ts}-${RANDOM}"
}

run_compose_with_timeout() {
    local seconds="$1"
    shift
    local cmd_preview="$*"
    if command -v timeout >/dev/null 2>&1 && timeout --version 2>/dev/null | grep -qi "coreutils"; then
        timeout "${seconds}"s "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout "${seconds}"s "$@"
    else
        "$@" &
        local cmd_pid=$!
        local elapsed=0

        while kill -0 "${cmd_pid}" 2>/dev/null; do
            if [ "${elapsed}" -gt 0 ] && [ $((elapsed % 10)) -eq 0 ]; then
                echo "... still waiting (${elapsed}s/${seconds}s): ${cmd_preview}" | tee -a "${LOG_FILE}"
            fi
            if [ "${elapsed}" -ge "${seconds}" ]; then
                kill -TERM "${cmd_pid}" 2>/dev/null || true
                sleep 2
                kill -KILL "${cmd_pid}" 2>/dev/null || true
                wait "${cmd_pid}" 2>/dev/null || true
                return 124
            fi
            sleep 1
            elapsed=$((elapsed + 1))
        done

        wait "${cmd_pid}"
    fi
}

force_remove_container() {
    local container="$1"
    if run_compose_with_timeout 20 sh -lc "docker rm -f ${container}" >> "${LOG_FILE}" 2>&1; then
        return 0
    fi
    echo "WARNING: force remove timed out/failed for ${container}" >> "${LOG_FILE}"
    return 1
}

echo "Running a diagnostic startup..."
echo "This will attempt to start all services without any checks or retries."
echo "The goal is to get a clear error message from docker-compose."
echo "All output is being redirected to the file '${LOG_FILE}'."
echo ""

# Create a separator in the log file
echo "" > "${LOG_FILE}"
echo "--- Diagnostic Run at $(date) ---" >> "${LOG_FILE}"
echo "" >> "${LOG_FILE}"

choose_compose_command
configure_build_backend
configure_backend_cache_buster
echo "Using compose command: ${COMPOSE_CMD}" >> "${LOG_FILE}"
echo "Build mode: DOCKER_BUILDKIT=${DOCKER_BUILDKIT}, COMPOSE_DOCKER_CLI_BUILD=${COMPOSE_DOCKER_CLI_BUILD}" >> "${LOG_FILE}"
echo "Backend cache-buster: ${BACKEND_CACHE_BUSTER}" >> "${LOG_FILE}"

# Stop and remove old containers to ensure a clean start
echo "--- Stopping and removing old containers ---" >> "${LOG_FILE}"
if ! run_compose_with_timeout 180 sh -lc "${COMPOSE_CMD} down --remove-orphans" >> "${LOG_FILE}" 2>&1; then
    echo "ERROR: timed out or failed while stopping old containers" >> "${LOG_FILE}"
fi
force_remove_container mensa_frontend || true
force_remove_container mensa_backend || true
force_remove_container mensa_chroma || true

# Attempt to build and start (detached mode with loop detection)
echo "--- Building and starting new containers ---" >> "${LOG_FILE}"
if ! run_compose_with_timeout 5400 sh -lc "${COMPOSE_CMD} up -d --build --force-recreate" >> "${LOG_FILE}" 2>&1; then
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