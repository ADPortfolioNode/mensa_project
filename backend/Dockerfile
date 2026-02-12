# Multi-stage build for optimized image size and layer caching
FROM python:3.11-slim as builder

WORKDIR /app

# Allow choosing a requirements file at build time for fast validation builds
ARG REQUIREMENTS_FILE=requirements.txt

# Copy only requirements for dependency caching layer
COPY ${REQUIREMENTS_FILE} requirements.txt

# Install dependencies in builder stage with extended timeout and retries
# Install to user site-packages to make them easier to copy
RUN pip --default-timeout=300 --retries 5 install --no-cache-dir --user -r requirements.txt

# Final runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Add health check: use wget or netcat to verify port is listening
# Falls back to testing with python built-ins if needed
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 5000), timeout=2).close()" || exit 1

# Use h11 instead of httptools to avoid memory allocation issues
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--http", "h11"]
