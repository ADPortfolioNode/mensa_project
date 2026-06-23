#!/bin/sh
set -e

# Fix permissions for data directory if it exists
if [ -d "/data" ]; then
    echo "Fixing permissions for /data directory..."
    # Ensure experiments directory exists and has correct permissions
    mkdir -p /data/experiments
    chown -R appuser:appuser /data /data/experiments
    echo "Permissions fixed for /data directory"
fi

# Execute the main command
exec "$@"
