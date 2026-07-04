#!/usr/bin/env bash
# Verify the Windows host can reach Mensa published ports (not just in-container health).

verify_windows_host_connectivity() {
    local bind_host="${DOCKER_BIND_HOST:-127.0.0.1}"
    local frontend_port="${FRONTEND_HOST_PORT:-3000}"
    local max_wait="${WINDOWS_PORT_WAIT_SEC:-90}"
    local elapsed=0
    local health_url="http://${bind_host}:${frontend_port}/api/health"
    local status_url="http://${bind_host}:${frontend_port}/api/startup_status"

    echo "Verifying Windows host connectivity (${bind_host}:${frontend_port})..."

    while [ "${elapsed}" -lt "${max_wait}" ]; do
        if command -v curl >/dev/null 2>&1; then
            if curl -sf "${health_url}" >/dev/null 2>&1 && curl -sf "${status_url}" >/dev/null 2>&1; then
                echo "✓ Host can reach ${health_url}"
                return 0
            fi
        fi

        if command -v powershell.exe >/dev/null 2>&1; then
            if powershell.exe -NoProfile -Command \
                "try { \
                    Invoke-WebRequest -Uri '${health_url}' -UseBasicParsing -TimeoutSec 6 | Out-Null; \
                    Invoke-WebRequest -Uri '${status_url}' -UseBasicParsing -TimeoutSec 6 | Out-Null; \
                    exit 0 \
                } catch { exit 1 }" >/dev/null 2>&1; then
                echo "✓ Host can reach frontend API via PowerShell (${bind_host}:${frontend_port})"
                return 0
            fi
        fi

        sleep 3
        elapsed=$((elapsed + 3))
        if [ $((elapsed % 9)) -eq 0 ]; then
            echo "  still waiting for ${bind_host}:${frontend_port} (${elapsed}s/${max_wait}s)..."
        fi
    done

    echo "ERROR: Windows host cannot reach ${health_url}" >&2
    echo "Use http://${bind_host}:${frontend_port}/ (not localhost) if IPv6/wslrelay conflicts occur." >&2
    return 1
}

repair_windows_port_forwarding() {
    echo "Repairing Docker port forwarding (Windows)..."
    compose_cmd restart backend frontend >/dev/null 2>&1 || true
    sleep 12
    compose_cmd up -d --force-recreate frontend >/dev/null 2>&1 || true
    sleep 10
}