# Multi-stage build for optimized image size and layer caching
FROM python:3.11-slim as builder

WORKDIR /app

# Copy only requirements for dependency caching layer
# This layer is cached unless requirements.txt changes, reducing rebuild time
COPY requirements.txt .

# Install with extended timeout and retries for network resilience
# Remove httptools (C extension) and use h11 (pure Python HTTP) to avoid memory issues
RUN pip --default-timeout=300 --retries 5 install --no-cache-dir -r requirements.txt && \
    pip uninstall -y httptools

# Final runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Add health check: use wget or netcat to verify port is listening
# Falls back to testing with python built-ins if needed
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 5000), timeout=2).close()" || exit 1

# Use h11 instead of httptools to avoid memory allocation issues
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--http", "h11"]
