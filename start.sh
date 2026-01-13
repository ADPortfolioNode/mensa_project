#!/bin/bash

# Script to optimize Docker startup sequence by ensuring clean shutdown before starting
# This avoids port conflicts and ensures a fresh start

echo "Stopping and removing existing containers..."
docker-compose down --remove-orphans

# Conditional Docker image building:
# By default, `docker-compose build` uses Docker's build cache.
# This means images are only rebuilt if their Dockerfile instructions or
# build context files (e.g., source code, requirements.txt) have changed.
# This leads to fast startup times when code is not modified.
#
# To force a complete rebuild *without* using the cache (e.g., if you suspect
# a corrupted cache or want to ensure a pristine build environment),
# set the environment variable FORCE_NO_CACHE to "true" before running this script:
#   
#
if [ "$FORCE_NO_CACHE" = "true" ]; then
    echo "Building services with --no-cache (FORCE_NO_CACHE=true)..."
    docker-compose build --no-cache
else
    echo "Building services (Docker cache will be used unless changes are detected)..."
    docker-compose build
fi

echo "Clearing ChromaDB data..."
rm -rf ./data/chroma

echo "Starting services..."
docker-compose up -d

echo "Services started. Check logs with: docker-compose logs -f"
