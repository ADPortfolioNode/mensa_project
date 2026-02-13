# Single-stage build to avoid cross-stage copy failures on large dependency trees
FROM python:3.11-slim

WORKDIR /app

# Allow choosing a requirements file at build time for fast validation builds
ARG REQUIREMENTS_FILE=requirements.txt

# Copy only requirements first for better layer caching
COPY ${REQUIREMENTS_FILE} requirements.txt

# Install dependencies and validate ASGI server import
RUN pip --default-timeout=300 --retries 5 install --no-cache-dir -r requirements.txt \
    && python - <<'PY'
from hypercorn.config import Config

print(f"hypercorn install verified: {Config.__module__}")
PY

# Copy application code
ARG CACHE_BUSTER=1
COPY . .

# Add health check: verify API port is accepting connections
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 5000), timeout=2).close()" || exit 1

# Run ASGI app with Hypercorn
CMD ["hypercorn", "main:app", "--bind", "0.0.0.0:5000", "--workers", "2"]
