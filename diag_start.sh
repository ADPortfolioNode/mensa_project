#!/usr/bin/env bash
set -u

# === Mensa Project Diagnostic Start Script ===
# This script attempts a minimal startup to get a clear error message from docker-compose.
# All output is redirected to 'diag_output.log'.
# It does NOT perform any of the safety checks or retries of the main `start.sh`.

LOG_FILE="diag_output.log"
LOCK_FILE=".diag_start.lock"
DIAG_SCRIPT_VERSION="2026-07-02-port-resolve"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIAG_BUILD_TIMEOUT=${DIAG_BUILD_TIMEOUT:-900}
DIAG_UP_TIMEOUT=${DIAG_UP_TIMEOUT:-300}
ENGINE_DROP_DETECTED=0

# shellcheck source=scripts/resolve_host_ports.sh
. "${SCRIPT_DIR}/scripts/resolve_host_ports.sh"

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
    if ! run_compose_with_timeout "${DIAG_BUILD_TIMEOUT}" env DOCKER_BUILDKIT=1 docker build --progress=plain -t mensa_project-frontend:latest \
        --build-arg "NODE_VERSION=${node_version}" \
        --build-arg "REACT_APP_API_BASE=" \
        --build-arg "CACHE_BUSTER=${BACKEND_CACHE_BUSTER}" \
        -f frontend/Dockerfile frontend; then
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

docker_info_ok() {
    # docker info can hang indefinitely on Windows when the engine pipe is dead
    run_compose_with_timeout 8 docker info >/dev/null 2>&1
}

try_start_docker_desktop() {
    if ! is_windows_shell || ! command -v powershell.exe >/dev/null 2>&1; then
        return 1
    fi
    if docker_info_ok; then
        return 0
    fi

    echo "Docker daemon unreachable; attempting to start Docker Desktop..." >> "${LOG_FILE}"
    powershell.exe -NoProfile -Command \
        "Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -ErrorAction SilentlyContinue" \
        >> "${LOG_FILE}" 2>&1 || true
    return 0
}

wait_for_docker_daemon() {
    local max_wait="${1:-120}"
    local elapsed=0
    local started_desktop=0

    while [ "${elapsed}" -lt "${max_wait}" ]; do
        if docker_info_ok; then
            echo "Docker daemon is ready (${elapsed}s)." >> "${LOG_FILE}"
            return 0
        fi

        if [ "${started_desktop}" -eq 0 ] && [ "${elapsed}" -ge 4 ]; then
            try_start_docker_desktop
            started_desktop=1
        fi

        if [ "${elapsed}" -gt 0 ] && [ $((elapsed % 10)) -eq 0 ]; then
            echo "Waiting for Docker daemon... (${elapsed}s/${max_wait}s)" >> "${LOG_FILE}"
        fi

        sleep 2
        elapsed=$((elapsed + 2))
    done

    echo "ERROR: Docker daemon not ready after ${max_wait}s." >> "${LOG_FILE}"
    return 1
}

ensure_docker_ready_for_diag() {
    local max_wait="${1:-180}"
    echo "--- Waiting for Docker daemon (max ${max_wait}s) ---" >> "${LOG_FILE}"
    if wait_for_docker_daemon "${max_wait}"; then
        return 0
    fi
    ENGINE_DROP_DETECTED=1
    return 1
}

wait_for_service_diag() {
    local svc_name="$1"
    local max_checks="${2:-24}"
    local interval="${3:-5}"
    local i=0

    echo "Waiting for ${svc_name} (${max_checks}x${interval}s)..." >> "${LOG_FILE}"
    while [ "${i}" -lt "${max_checks}" ]; do
        if ! docker_info_ok; then
            echo "ERROR: Docker engine lost while waiting for ${svc_name}" >> "${LOG_FILE}"
            return 1
        fi

        local container_id health_status running_status
        container_id=$(compose_cmd ps -q "${svc_name}" 2>/dev/null || true)
        if [ -z "${container_id}" ]; then
            container_id=$(docker ps -aq --filter "name=mensa_${svc_name}" | head -n1 || true)
        fi

        if [ -n "${container_id}" ]; then
            running_status=$(docker inspect --format='{{.State.Running}}' "${container_id}" 2>/dev/null || echo "false")
            health_status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${container_id}" 2>/dev/null || echo "missing")
            if [ "${running_status}" = "true" ]; then
                if [ "${health_status}" = "healthy" ] || [ "${health_status}" = "none" ]; then
                    echo "${svc_name} is ready (health=${health_status})." >> "${LOG_FILE}"
                    return 0
                fi
            fi
        fi

        sleep "${interval}"
        i=$((i + 1))
    done

    echo "ERROR: timed out waiting for ${svc_name}" >> "${LOG_FILE}"
    return 1
}

staged_compose_up_windows() {
    local attempt="$1"
    echo "--- Staged compose up (attempt ${attempt}) ---" >> "${LOG_FILE}"

    if ! wait_for_docker_daemon 90; then
        return 1
    fi

    if ! run_compose_with_timeout 120 compose_cmd up -d --force-recreate chroma >> "${LOG_FILE}" 2>&1; then
        return 1
    fi
    if ! wait_for_service_diag chroma 30 5; then
        return 1
    fi

    if ! wait_for_docker_daemon 60; then
        return 1
    fi
    if ! run_compose_with_timeout 120 compose_cmd up -d --force-recreate backend >> "${LOG_FILE}" 2>&1; then
        return 1
    fi
    if ! wait_for_service_diag backend 36 5; then
        return 1
    fi

    if ! wait_for_docker_daemon 60; then
        return 1
    fi
    if ! run_compose_with_timeout 90 compose_cmd up -d --force-recreate frontend >> "${LOG_FILE}" 2>&1; then
        return 1
    fi
    if ! wait_for_service_diag frontend 18 5; then
        return 1
    fi

    echo "Staged compose up completed." >> "${LOG_FILE}"
    return 0
}

log_has_engine_drop() {
    grep -Fq 'dockerDesktopLinuxEngine' "${LOG_FILE}" 2>/dev/null \
        || grep -Fq 'failed to connect to the docker API' "${LOG_FILE}" 2>/dev/null
}

compose_up_with_retries() {
    local attempt

    if is_windows_shell; then
        for attempt in 1 2 3; do
            if staged_compose_up_windows "${attempt}"; then
                return 0
            fi
            if log_has_engine_drop; then
                ENGINE_DROP_DETECTED=1
            fi
            echo "Staged compose up attempt ${attempt} failed; waiting 20s..." >> "${LOG_FILE}"
            sleep 20
            wait_for_docker_daemon 120 || true
        done
    else
        if run_compose_with_timeout "${DIAG_UP_TIMEOUT}" compose_cmd up -d --force-recreate >> "${LOG_FILE}" 2>&1; then
            return 0
        fi
        if log_has_engine_drop; then
            ENGINE_DROP_DETECTED=1
        fi
    fi

    if [ "${ENGINE_DROP_DETECTED}" -eq 1 ]; then
        return 2
    fi
    return 1
}

print_engine_failure_help() {
    local phase="$1"
    local built="${2:-unknown}"

    echo "✗ Diagnostic startup FAILED: Docker Desktop engine unavailable during ${phase}."
    if [ "${built}" = "yes" ]; then
        echo "Builds succeeded. Deploy failed because the Docker engine pipe disconnected."
        echo ""
        echo "Recovery (skip rebuild — images are already built):"
        echo "  1. Restart Docker Desktop, wait until 'Running' (~60s)"
        echo "  2. ./recover_stack.sh"
        echo "     or: docker compose up -d --force-recreate"
        echo "  3. docker ps --filter name=mensa"
        echo "  4. curl http://127.0.0.1:3000/api/health"
    else
        echo "Build never started because Docker was not running."
        echo ""
        echo "Recovery:"
        echo "  1. Start Docker Desktop manually, wait until 'Running' (~60s)"
        echo "  2. Re-run: ./start.sh --build --diag"
        echo "     or: ./diag_start.sh"
    fi
    echo ""
    echo "This is a Docker Desktop stability issue on Windows — not an app config error."
}

log_has_port_conflict() {
    grep -Fq 'port is already allocated' "${LOG_FILE}" 2>/dev/null
}

print_compose_failure_help() {
    if [ "${ENGINE_DROP_DETECTED}" -eq 1 ] || log_has_engine_drop; then
        print_engine_failure_help "compose up" "yes"
    elif log_has_port_conflict; then
        echo "✗ Diagnostic startup FAILED: host port conflict during compose up."
        echo "Another process or container is using a required port (often 8000 or 5000)."
        echo ""
        echo "Recovery:"
        echo "  1. Set free ports in .env, e.g.:"
        echo "       BACKEND_HOST_PORT=5001"
        echo "       CHROMA_HOST_PORT=8001"
        echo "  2. Re-run: ./diag_start.sh"
        echo "     or:     ./recover_stack.sh"
        echo ""
        echo "Check the end of '${LOG_FILE}' for the exact port."
    else
        echo "✗ Diagnostic startup FAILED during docker-compose up."
        echo "Check the end of '${LOG_FILE}' for details."
        echo "Look for: cat ${LOG_FILE}"
    fi
}

print_build_failure_help() {
    if [ "${ENGINE_DROP_DETECTED}" -eq 1 ] || log_has_engine_drop; then
        print_engine_failure_help "image build" "no"
    else
        echo "✗ Diagnostic startup FAILED during docker-compose build."
        echo "An error occurred. Check the end of the '${LOG_FILE}' for details."
        echo "You can view the full log with: cat ${LOG_FILE}"
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

echo "Running diagnostic startup (${DIAG_SCRIPT_VERSION})..."
echo "Builds images, then starts services in stages (chroma -> backend -> frontend)."
echo "All output is written to '${LOG_FILE}'."
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
echo "--- Diagnostic Run at $(date) [${DIAG_SCRIPT_VERSION}] ---" >> "${LOG_FILE}"
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
    echo "Windows shell detected; using direct container cleanup (skipping compose down)." >> "${LOG_FILE}"
    force_cleanup_mensa_runtime_once
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

if ! ensure_docker_ready_for_diag 180; then
    append_diag_failure_bundle
    echo ""
    echo "---"
    print_build_failure_help
    echo "---"
    exit 1
fi

# Attempt to build and start (detached mode with loop detection)
echo "--- Building images ---" >> "${LOG_FILE}"
if ! wait_for_docker_daemon 30; then
    ENGINE_DROP_DETECTED=1
    append_diag_failure_bundle
    echo ""
    echo "---"
    print_build_failure_help
    echo "---"
    exit 1
fi
if is_windows_shell; then
    if ! build_images_windows_direct_diag >> "${LOG_FILE}" 2>&1; then
        if log_has_engine_drop; then
            ENGINE_DROP_DETECTED=1
        fi
        append_diag_failure_bundle
        echo ""
        echo "---"
        print_build_failure_help
        echo "---"
        exit 1
    fi
elif ! run_compose_with_timeout "${DIAG_BUILD_TIMEOUT}" compose_cmd build --no-cache >> "${LOG_FILE}" 2>&1; then
    if log_has_engine_drop; then
        ENGINE_DROP_DETECTED=1
    fi
    append_diag_failure_bundle
    echo ""
    echo "---"
    print_build_failure_help
    echo "---"
    exit 1
fi

echo "--- Building and starting new containers ---" >> "${LOG_FILE}"
if [ -f "${SCRIPT_DIR}/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    . "${SCRIPT_DIR}/.env"
    set +a
fi
if is_windows_shell && [ -z "${DOCKER_BIND_HOST:-}" ]; then
    export DOCKER_BIND_HOST=127.0.0.1
    echo "Windows: DOCKER_BIND_HOST=${DOCKER_BIND_HOST}" >> "${LOG_FILE}"
fi
if ! resolve_compose_host_ports >> "${LOG_FILE}" 2>&1; then
    append_diag_failure_bundle
    echo ""
    echo "---"
    echo "✗ Diagnostic startup FAILED: could not resolve host ports."
    echo "---"
    exit 1
fi
echo "Host ports: backend=${BACKEND_HOST_PORT:-5000}, chroma=${CHROMA_HOST_PORT:-8000}, frontend=${FRONTEND_HOST_PORT:-3000}" >> "${LOG_FILE}"
compose_up_with_retries
compose_up_rc=$?
if [ "${compose_up_rc}" -ne 0 ]; then
    append_diag_failure_bundle
    if log_has_engine_drop; then
        ENGINE_DROP_DETECTED=1
    fi
    echo ""
    echo "---"
    print_compose_failure_help
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