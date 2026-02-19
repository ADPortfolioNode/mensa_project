#!/usr/bin/env bash
set -u

# === Mensa Project Diagnostic Start Script ===
# This script attempts a minimal startup to get a clear error message from docker-compose.
# All output is redirected to 'diag_output.log'.
# It does NOT perform any of the safety checks or retries of the main `start.sh`.

LOG_FILE="diag_output.log"
LOCK_FILE=".diag_start.lock"
DIAG_BUILD_TIMEOUT=${DIAG_BUILD_TIMEOUT:-900}
DIAG_UP_TIMEOUT=${DIAG_UP_TIMEOUT:-300}

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

compose_cmd() {
    if [ "${COMPOSE_CMD}" = "docker compose" ]; then
        docker compose "$@"
    else
        docker-compose "$@"
    fi
}

append_diag_failure_bundle() {
    echo "" >> "${LOG_FILE}"
    echo "--- FAILURE SNAPSHOT ---" >> "${LOG_FILE}"
    echo "[compose ps]" >> "${LOG_FILE}"
    compose_cmd ps >> "${LOG_FILE}" 2>&1 || true
    echo "" >> "${LOG_FILE}"
    echo "[docker ps -a (mensa)]" >> "${LOG_FILE}"
    docker ps -a --filter "name=mensa" >> "${LOG_FILE}" 2>&1 || true
    echo "" >> "${LOG_FILE}"
    echo "[docker info top]" >> "${LOG_FILE}"
    docker info >> "${LOG_FILE}" 2>&1 || true
    echo "" >> "${LOG_FILE}"
    echo "[service logs tail]" >> "${LOG_FILE}"
    compose_cmd logs --tail 80 backend frontend chroma >> "${LOG_FILE}" 2>&1 || true
    echo "--- END FAILURE SNAPSHOT ---" >> "${LOG_FILE}"
}

build_images_windows_direct_diag() {
    local node_version
    node_version="${NODE_VERSION:-22.13.1}"

    echo "Building backend image directly (Windows stability path)..."
    if ! run_compose_with_timeout "${DIAG_BUILD_TIMEOUT}" env DOCKER_BUILDKIT=1 docker build --progress=plain -t mensa_project-backend:latest --build-arg "CACHE_BUSTER=${BACKEND_CACHE_BUSTER}" -f backend/Dockerfile backend; then
        return 1
    fi

    echo "Building frontend image directly (Windows stability path)..."
    if ! run_compose_with_timeout "${DIAG_BUILD_TIMEOUT}" env DOCKER_BUILDKIT=1 docker build --progress=plain -t mensa_project-frontend:latest --build-arg "NODE_VERSION=${node_version}" -f frontend/Dockerfile frontend; then
        return 1
    fi

    return 0
}

is_windows_shell() {
    case "$(uname -s 2>/dev/null || echo unknown)" in
        MINGW*|MSYS*|CYGWIN*) return 0 ;;
        *) return 1 ;;
    esac
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

    "$@" &
    local cmd_pid=$!
    local elapsed=0

    while kill -0 "${cmd_pid}" 2>/dev/null; do
        if [ "${elapsed}" -gt 0 ] && [ $((elapsed % 10)) -eq 0 ]; then
            echo "... still waiting (${elapsed}s/${seconds}s): ${cmd_preview}"
        fi
        if [ "${elapsed}" -ge "${seconds}" ]; then
            kill -TERM "-${cmd_pid}" 2>/dev/null || kill -TERM "${cmd_pid}" 2>/dev/null || true
            sleep 2
            kill -KILL "-${cmd_pid}" 2>/dev/null || kill -KILL "${cmd_pid}" 2>/dev/null || true
            wait "${cmd_pid}" 2>/dev/null || true
            echo "TIMEOUT: command exceeded ${seconds}s: ${cmd_preview}"
            return 124
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    wait "${cmd_pid}"
}

force_remove_container() {
    local container="$1"
    if run_compose_with_timeout 20 sh -lc "docker rm -f ${container}" >> "${LOG_FILE}" 2>&1; then
        return 0
    fi
    echo "WARNING: force remove timed out/failed for ${container}" >> "${LOG_FILE}"
    return 1
}

force_cleanup_mensa_runtime_once() {
    echo "Attempting one-time forced cleanup for stuck Mensa runtime..." >> "${LOG_FILE}"
    run_compose_with_timeout 30 docker rm -f mensa_frontend mensa_backend mensa_chroma >> "${LOG_FILE}" 2>&1 || true
    run_compose_with_timeout 20 docker network rm mensa_project_default >> "${LOG_FILE}" 2>&1 || true
    if ! is_windows_shell; then
        run_compose_with_timeout 30 docker network prune -f >> "${LOG_FILE}" 2>&1 || true
    fi
    echo "Forced cleanup pass completed." >> "${LOG_FILE}"
}

kill_stale_cleanup_jobs() {
    if command -v pkill >/dev/null 2>&1; then
        pkill -f "docker compose down --remove-orphans" >/dev/null 2>&1 || true
        pkill -f "sh -lc docker compose down --remove-orphans" >/dev/null 2>&1 || true
        pkill -f "docker compose up -d --force-recreate" >/dev/null 2>&1 || true
        pkill -f "docker compose up -d --build --force-recreate" >/dev/null 2>&1 || true
        pkill -f "sh -lc docker compose up -d --force-recreate" >/dev/null 2>&1 || true
        pkill -f "sh -lc docker compose up -d --build --force-recreate" >/dev/null 2>&1 || true
        pkill -f "docker-compose up -d --force-recreate" >/dev/null 2>&1 || true
        pkill -f "docker-compose up -d --build --force-recreate" >/dev/null 2>&1 || true
        pkill -f "docker rm -f mensa_frontend mensa_backend mensa_chroma" >/dev/null 2>&1 || true
        pkill -f "docker network prune -f" >/dev/null 2>&1 || true
        pkill -f "docker network rm mensa_project_default" >/dev/null 2>&1 || true
    fi

    if is_windows_shell && command -v powershell.exe >/dev/null 2>&1; then
        powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \
            \$_.CommandLine -match 'docker compose down --remove-orphans|sh -lc docker compose down --remove-orphans|docker compose up -d --force-recreate|docker compose up -d --build --force-recreate|sh -lc docker compose up -d --force-recreate|sh -lc docker compose up -d --build --force-recreate|docker-compose up -d --force-recreate|docker-compose up -d --build --force-recreate|docker rm -f mensa_frontend mensa_backend mensa_chroma|docker network prune -f|docker network rm mensa_project_default' \
        } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1 || true
    fi
}

echo "Running a diagnostic startup..."
echo "This will attempt to start all services without any checks or retries."
echo "The goal is to get a clear error message from docker-compose."
echo "All output is being redirected to the file '${LOG_FILE}'."
echo ""

# Single-instance guard to avoid overlapping diagnostic runs.
if [ -f "${LOCK_FILE}" ]; then
    old_pid=$(cat "${LOCK_FILE}" 2>/dev/null || true)
    if [ -n "${old_pid}" ] && kill -0 "${old_pid}" 2>/dev/null; then
        echo "Stopping previous diagnostic run (pid ${old_pid})..."
        kill -TERM "${old_pid}" 2>/dev/null || true
        sleep 1
        kill -KILL "${old_pid}" 2>/dev/null || true
    fi
fi
echo "$$" > "${LOCK_FILE}"
trap 'rm -f "${LOCK_FILE}"' EXIT

# Ensure no stale helper processes from previous runs are still writing output.
kill_stale_cleanup_jobs

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
kill_stale_cleanup_jobs
if is_windows_shell; then
    echo "Windows shell detected; skipping compose down/cleanup to avoid CLI hang." >> "${LOG_FILE}"
elif ! run_compose_with_timeout 60 compose_cmd down --remove-orphans --timeout 25 >> "${LOG_FILE}" 2>&1; then
    echo "ERROR: timed out or failed while stopping old containers" >> "${LOG_FILE}"
    force_cleanup_mensa_runtime_once
fi
if ! is_windows_shell; then
    force_remove_container mensa_frontend || true
    force_remove_container mensa_backend || true
    force_remove_container mensa_chroma || true
fi
echo "Shutdown/cleanup stage completed." >> "${LOG_FILE}"

# Attempt to build and start (detached mode with loop detection)
echo "--- Building images ---" >> "${LOG_FILE}"
if is_windows_shell; then
    if ! build_images_windows_direct_diag >> "${LOG_FILE}" 2>&1; then
        append_diag_failure_bundle
        echo ""
        echo "---"
        echo "✗ Diagnostic startup FAILED during docker-compose build."
        echo "An error occurred. Check the end of the '${LOG_FILE}' for details."
        echo "You can view the full log with: cat ${LOG_FILE}"
        echo "---"
        exit 1
    fi
elif ! run_compose_with_timeout "${DIAG_BUILD_TIMEOUT}" compose_cmd build --no-cache >> "${LOG_FILE}" 2>&1; then
    append_diag_failure_bundle
    echo ""
    echo "---"
    echo "✗ Diagnostic startup FAILED during docker-compose build."
    echo "An error occurred. Check the end of the '${LOG_FILE}' for details."
    echo "You can view the full log with: cat ${LOG_FILE}"
    echo "---"
    exit 1
fi

echo "--- Building and starting new containers ---" >> "${LOG_FILE}"
if ! run_compose_with_timeout "${DIAG_UP_TIMEOUT}" compose_cmd up -d --force-recreate >> "${LOG_FILE}" 2>&1; then
    append_diag_failure_bundle
    echo ""
    echo "---"
    echo "✗ Diagnostic startup FAILED during docker-compose up."
    echo "An error occurred. Check the end of the '${LOG_FILE}' for details."
    echo "You can view the full log with: cat ${LOG_FILE}"
    echo "---"
    exit 1
fi
echo "Build/start stage completed." >> "${LOG_FILE}"

# Monitor for restart loops
echo "" >> "${LOG_FILE}"
echo "--- Monitoring for restart loops ---" >> "${LOG_FILE}"
echo "Monitoring containers for restart loops (30 second check)..." | tee -a "${LOG_FILE}"

sleep 5  # Give containers time to start

# Track restart counts by compose service
services="backend frontend chroma"
initial_backend=0
initial_frontend=0
initial_chroma=0

# Get initial restart counts
for service in ${services}; do
    container_id=$(compose_cmd ps -q "${service}" 2>/dev/null || true)

    if [ -n "${container_id}" ]; then
        restart_count=$(docker inspect --format='{{.RestartCount}}' "${container_id}" 2>/dev/null || echo "0")
    else
        restart_count="0"
    fi

    case "${service}" in
        backend) initial_backend="${restart_count}" ;;
        frontend) initial_frontend="${restart_count}" ;;
        chroma) initial_chroma="${restart_count}" ;;
    esac
done

# Wait and check again
sleep 25

LOOP_DETECTED=0
for service in ${services}; do
    container_id=$(compose_cmd ps -q "${service}" 2>/dev/null || true)

    if [ -z "${container_id}" ]; then
        echo "✗ ERROR: Service ${service} container was not created!" | tee -a "${LOG_FILE}"
        echo "--- LOGS FOR ${service} ---" >> "${LOG_FILE}"
        compose_cmd logs --tail 50 "${service}" >> "${LOG_FILE}" 2>&1 || true
        echo "--------------------------------" >> "${LOG_FILE}"
        LOOP_DETECTED=1
        continue
    fi

    is_running=$(docker inspect --format='{{.State.Running}}' "${container_id}" 2>/dev/null || echo "false")
    if [ "${is_running}" != "true" ]; then
        echo "✗ ERROR: Service ${service} container is not running!" | tee -a "${LOG_FILE}"
        echo "--- LOGS FOR ${service} ---" >> "${LOG_FILE}"
        compose_cmd logs --tail 50 "${service}" >> "${LOG_FILE}" 2>&1 || true
        echo "--------------------------------" >> "${LOG_FILE}"
        LOOP_DETECTED=1
        continue
    fi

    restart_count=$(docker inspect --format='{{.RestartCount}}' "${container_id}" 2>/dev/null || echo "0")
    case "${service}" in
        backend) initial="${initial_backend}" ;;
        frontend) initial="${initial_frontend}" ;;
        chroma) initial="${initial_chroma}" ;;
        *) initial="0" ;;
    esac
    restarts=$((restart_count - initial))

    if [ "${restarts}" -gt 2 ]; then
        echo "✗ ERROR: Service ${service} has restarted ${restarts} times in 30 seconds - RESTART LOOP DETECTED!" | tee -a "${LOG_FILE}"
        echo "--- LOGS FOR ${service} ---" >> "${LOG_FILE}"
        compose_cmd logs --tail 100 "${service}" >> "${LOG_FILE}" 2>&1 || true
        echo "--------------------------------" >> "${LOG_FILE}"
        LOOP_DETECTED=1
    elif [ "${restarts}" -gt 0 ]; then
        echo "⚠ Warning: Service ${service} has restarted ${restarts} time(s)" | tee -a "${LOG_FILE}"
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
    compose_cmd down >> "${LOG_FILE}" 2>&1 || true
    exit 1
fi

echo "" | tee -a "${LOG_FILE}"
echo "---" | tee -a "${LOG_FILE}"
echo "✓ Diagnostic startup appears SUCCESSFUL - no restart loops detected." | tee -a "${LOG_FILE}"
echo "All containers are running normally." | tee -a "${LOG_FILE}"
echo "Check the '${LOG_FILE}' for detailed output." | tee -a "${LOG_FILE}"
echo "---" | tee -a "${LOG_FILE}"
exit 0