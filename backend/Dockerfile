FROM python:3.11-slim AS base

# Set workdir for all stages
WORKDIR /app

# --- Builder stage ---
FROM base AS builder

# Install build dependencies (if any are needed, e.g. gcc, build-essential, etc.)
# Only install pip and venv-related tools if not present (python:3.11-slim has venv and pip)

# Copy only requirements.txt first for better cache usage
COPY requirements.txt ./

# Create venv and install dependencies
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code (excluding files in .dockerignore)
COPY . .

# --- Final stage ---
FROM base AS final

# Create a non-root user and group
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy application code and venv from builder
COPY --from=builder /app /app
COPY --from=builder /opt/venv /opt/venv

# Set environment so the venv is used by default
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set permissions
RUN chown -R appuser:appgroup /app /opt/venv && \
    chmod +x /app/start.sh
USER appuser

# Verify venv and fastapi are available
RUN python -c "import fastapi; print('FastAPI is available')"

# Expose port (if your app listens on a specific port, e.g. 8000)
EXPOSE 8000

# Set entrypoint (adjust if your app uses a different entrypoint)
CMD ["/app/start.sh"]
