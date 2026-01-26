 
 # Mensa Predictive RAG — Local Run GuideDashboard.js:58  
This repository contains a minimal production-oriented scaffold for ingesting NY Lottery draws, storing canonical records in ChromaDB, training reproducible experiments, and serving predictions.

This README explains how to build and run the system with Docker Compose and how to perform quick verification of the UI and backend endpoints.

## Prerequisites

- Docker and Docker Compose installed
- Recommended: run from WSL (Windows) or Linux for faster file-sharing

## Services

- `chroma`: ChromaDB server (container)
- `backend`: FastAPI backend (container)
- `frontend`: React dev server (container)

All stateful data is stored under Docker volumes and the `/data` folder inside the backend container:

- `/data/chroma` (Chroma server data)
- `/data/models` (model artifacts)
- `/data/experiments` (experiment metadata)
- `/data/logs`

## Build & Run (development)

From the repository root run:

```bash
./start.sh
```

This script ensures a clean startup by stopping any existing containers first, then building and starting the services. It will:

- Pull and run the `chromadb/chroma` image
- Build the backend image (installs Python deps in `backend/requirements_dev.txt`)
- Build the frontend image and start the React dev server

Compose config notes:

- The `backend` service depends on `chroma` health check (Compose `condition: service_healthy`) so it waits for Chroma to be ready before starting.
- The backend `entrypoint.sh` also includes an optional wait loop when `WAIT_FOR_CHROMA` is set.

## Verify services

View logs:

```bash
docker-compose ps
docker-compose logs -f chroma backend frontend
```

Health checks

- Backend: `http://localhost:5000/` should return a JSON welcome message
- Frontend: `http://localhost:3000/` serves the React app

Quick curl checks:

```bash
curl http://localhost:5000/
curl http://localhost:3000/
```

## Quick API examples

1) Ingest sample (Take5):

```bash
curl -X POST http://localhost:5000/api/ingest/fetch_and_sync \
  -H "Content-Type: application/json" \
  -d '{"resource_id":"take5","game":"take5","limit":50}'
```

Response: `{ "status": "success", "added": X, "skipped": Y, "versioned": Z }`

2) Run experiments (train clones):

```bash
curl -X POST http://localhost:5000/api/experiments/run \
  -H "Content-Type: application/json" \
  -d '{"game":"take5","seeds":[42,43,44],"hyperparameters":{"k":10,"n_estimators":100}}'
```

3) Predict (uses promoted/best artifact if available):

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"game":"take5","recent_k":10}'
```

Response contains: prediction, artifact path, and provenance record IDs.

## Frontend

Open `http://localhost:3000/` to view the dashboard. Use the controls to call ingest, train, and predict. The Dashboard calls backend endpoints directly (CORS enabled for localhost).

Frontend environment configuration
----------------------------------

The frontend can target a backend running on a different origin by setting the `REACT_APP_API_BASE` environment variable. If left empty, the frontend uses relative paths (recommended when serving frontend and backend from the same origin). Create a `frontend/.env` file or set the variable in your environment. Example in `frontend/.env`:

```bash
# Point API calls to a backend running on localhost:5000
REACT_APP_API_BASE=http://localhost:5000
```

An example file is included as `frontend/.env.example`.

## Troubleshooting

- If the backend fails to start because of `chromadb` client import errors, try rebuilding the backend image:

```bash
docker-compose build backend --no-cache
```

- If using Windows native Docker and experiencing slow builds, run from WSL or enable file sharing for the project folder.

- To inspect Chroma data, explore the `chroma_data` Docker volume or query via the Chroma REST API at `http://localhost:8000/`.

## Next steps

- Add stronger chron_index transactional handling (e.g., file lock, Redis or DB counter) for concurrent ingestion
- Add unit and integration tests (ingest canonicalization, dedupe/versioning, deterministic experiment runs)
- Extend predictor to produce probabilistic/top-k outputs and better feature engineering

If you'd like, I can now add unit tests and/or wire the frontend to display model predictions in a nicer UI. Which would you prefer next?
# Mensa Predictive RAG System
Run:
1. docker-compose up --build
2. Open http://localhost:3000
Notes:
- default Socrata resource ids provided; change in frontend Dashboard or call /api/ingest/fetch_and_sync with other ids.
- Chroma runs at http://localhost:8000
- Data persists to /data in project root

Quick notes & tunables (so Copilot knows how to finish)
Resource IDs used for convenience:

Take 5: 6wrc-wmqa (data.ny.gov). 
State of New York

Pick 3: n4w8-wxte. 
State of New York

Pick 4 / widgets: referenced on data.ny.gov as well. 
State of New York
+1

To change concurrency: update max_clones in backend/main.py (Concierge constructor).

To upgrade embedding: replace services/chroma_client.py embed_texts with your preferred embedding model and persist model name in experiment metadata.

The scaffold uses a simple RandomForest baseline for reproducible quick experiments. Replace trainer with PyTorch CNN if you want more complex modeling — keep experiment_id, seed, and meta logging for reproducibility.

Citations (core sources used)
data.ny.gov — Take 5 dataset page. 
State of New York

data.ny.gov — Pick 3 dataset page. 
State of New York

data.ny.gov widgets & Pick4 references. 
State of New York
+1
