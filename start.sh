#!/usr/bin/env bash
set -euo pipefail

# === Mensa Project Quick Start ===
# Simplified startup for development: build → start → wait
# For detailed progress monitoring, use: ./monitor_startup.sh

echo "Starting Mensa Project..."
echo ""

# Stop and remove old containers
docker-compose down --remove-orphans 2>/dev/null || true
docker rm -f mensa_frontend mensa_backend mensa_chroma 2>/dev/null || true

# Build and start services with proper dependency ordering
echo "Building and starting services (this may take a few minutes on first run)..."
docker-compose up -d --build

# Wait for services to be healthy
echo "Waiting for services to be ready..."
for i in {1..30}; do
    if docker-compose ps | grep -q "healthy"; then
        echo "✓ Services ready"
        break
    fi
    sleep 2
done

# Show status
echo ""
echo "Container Status:"
docker-compose ps
echo ""

# Show access points
echo "✓ Application started"
echo ""
echo "Access your application:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:5000/api"
echo ""
echo "View logs:"
echo "  docker-compose logs -f"
echo ""
