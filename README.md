## Running the Project with Docker

This project uses Docker for both the Python backend and JavaScript frontend. The setup is managed via Docker Compose and is tailored to the following requirements:

### Project-Specific Docker Requirements
- **Backend**
  - Uses `python:3.11-slim` as the base image.
  - Dependencies are installed from `requirements.txt` in a Python virtual environment (`.venv`).
  - Exposes port **8000**.
  - Runs as a non-root user (`appuser`).
- **Frontend**
  - Uses `node:22.13.1-slim` (Node.js v22.13.1) as the base image.
  - Installs dependencies via `npm ci` and builds the app with `npm run build`.
  - Exposes port **3000**.
  - Runs as a non-root user (`appuser`).

### Environment Variables
- **Backend**
  - Optionally supports an `.env` file in `./backend` (uncomment `env_file` in `docker-compose.yml` if needed).
- **Frontend**
  - Requires an `.env` file in `./frontend` (already referenced in `docker-compose.yml`).

### Build and Run Instructions
1. Ensure Docker and Docker Compose are installed.
2. Place any required environment variables in `./frontend/.env` and (optionally) `./backend/.env`.
3. From the project root, build and start the services:
   ```sh
   docker compose up --build
   ```
   This will build and start both the backend and frontend containers.

### Service Ports
- **Backend**: Accessible on port **8000** (internal to Docker network).
- **Frontend**: Accessible on port **3000** (internal to Docker network).

### Special Configuration
- Both services run as non-root users for improved security.
- The frontend service depends on the backend and will wait for it to be available before starting.
- All services are connected via the custom Docker network `app-net`.

Refer to the `docker-compose.yml`, `backend/Dockerfile`, and `frontend/Dockerfile` for further customization or advanced configuration.
