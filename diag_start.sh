#!/usr/bin/env bash
set -eu

# === Mensa Project Diagnostic Start Script ===
# This script attempts a minimal startup to get a clear error message from docker-compose.
# All output is redirected to 'diag_output.log'.
# It does NOT perform any of the safety checks or retries of the main `start.sh`.

LOG_FILE="diag_output.log"

echo "Running a diagnostic startup..."
echo "This will attempt to start all services without any checks or retries."
echo "The goal is to get a clear error message from docker-compose."
echo "All output is being redirected to the file '${LOG_FILE}'."
echo ""

# Create a separator in the log file
echo "" > "${LOG_FILE}"
echo "--- Diagnostic Run at $(date) ---" >> "${LOG_FILE}"
echo "" >> "${LOG_FILE}"

# Stop and remove old containers to ensure a clean start
echo "--- Stopping and removing old containers ---" >> "${LOG_FILE}"
docker-compose down --remove-orphans >> "${LOG_FILE}" 2>&1 || true
docker rm -f mensa_frontend mensa_backend mensa_chroma >> "${LOG_FILE}" 2>&1 || true

# Attempt to build and start
echo "--- Building and starting new containers ---" >> "${LOG_FILE}"
if ! docker-compose up --build --force-recreate >> "${LOG_FILE}" 2>&1; then
    echo ""
    echo "---"
    echo "✗ Diagnostic startup FAILED."
    echo "An error occurred. Check the end of the '${LOG_FILE}' for details."
    echo "You can view the full log with: cat ${LOG_FILE}"
    echo "---"
    exit 1
fi

echo ""
echo "---"
echo "✓ Diagnostic startup appears to have SUCCEEDED."
echo "Check the '${LOG_FILE}' for detailed output."
echo "---"
exit 0