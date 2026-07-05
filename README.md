# Mensa Predictive RAG — Production-Ready Docker Application

A full-stack predictive analytics and RAG (Retrieval-Augmented Generation) application for lottery data analysis, featuring a React frontend, Python FastAPI backend with ChromaDB vector database, and multi-model AI integration (Gemini, GPT, Grok).

## 🚀 Quick Start

### Prerequisites
- Docker 20.10+ and Docker Compose 2.0+

### One-Command Deployment (local development)

```bash
# Clone the repository
git clone https://github.com/ADPortfolioNode/mensa_project.git
cd mensa_project

# Copy environment template and configure API keys
cp .env.example .env
# Edit .env with your API keys (see Required Keys below)

# Build and start all services
docker compose up --build -d

# Access the application
# Frontend:  http://localhost:3000
# Backend:   http://localhost:5000
# ChromaDB:  http://localhost:8000
```

### Public web server (subscribing customers)

Deploy with HTTPS, internal-only API/Chroma, and optional subscriber login:

```bash
cp .env.production.example .env
# Edit DOMAIN, ACME_EMAIL, API keys; set CADDY_PROFILE=subscribers for paid access
./scripts/deploy-production.sh
```

Full guide: [docs/deployment/PUBLIC_DISTRIBUTION.md](docs/deployment/PUBLIC_DISTRIBUTION.md)

### Required API Keys

At least one of these is needed for AI chat features. Set them in `.env`:

| Provider   | Env Variable       | Get Key At                                      |
|------------|--------------------|-------------------------------------------------|
| Google     | `GEMINI_API_KEY`   | https://aistudio.google.com/app/apikey          |
| OpenAI     | `OPENAI_API_KEY`   | https://platform.openai.com/api-keys            |
| xAI (Grok) | `GROK_API_KEY`     | https://console.x.ai                            |

The app runs **without** keys — ingestion, training, and predictions work in local mode. Only AI chat requires configuration.

## � Documentation

Comprehensive documentation is organized in the `docs/` directory:

- **[docs/README.md](docs/README.md)** - Documentation index and navigation
- **[docs/architecture/](docs/architecture/)** - Architecture documentation and diagrams
- **[docs/deployment/](docs/deployment/)** - Deployment guides and configurations
- **[docs/guides/](docs/guides/)** - User guides and operational documentation
- **[docs/testing/](docs/testing/)** - Testing documentation and reports
- **[docs/status/](docs/status/)** - Project status and completion reports
- **[docs/changes/](docs/changes/)** - Change logs and summaries

## �📁 Project Structure

```
mensa_project/
├── frontend/                  # React app (Create React App)
│   ├── Dockerfile             # Multi-stage: node build + nginx serve
│   ├── nginx.conf             # Production nginx with security headers + rate limiting
│   └── src/                   # React components
├── backend/                   # Python FastAPI backend
│   ├── Dockerfile             # Multi-stage: builder + slim runtime
│   ├── main.py                # FastAPI app bootstrap (<100 lines)
│   ├── routes/                # API endpoint definitions
│   ├── middleware/            # CORS, rate limiting
│   ├── state/                 # State management
│   ├── utils/                 # Helper functions
│   ├── config.py              # Game configs, schedules, aliases
│   └── services/              # Ingest, trainer, predictor, RAG, Chroma, LM router
├── docs/                      # Consolidated documentation
│   ├── architecture/          # Architecture docs and diagrams
│   ├── deployment/            # Deployment guides
│   ├── guides/                # Quick start, troubleshooting, operations
│   ├── testing/               # Test reports and plans
│   ├── status/                # Project status and completion reports
│   └── changes/               # Change logs and summaries
├── docker-compose.yml         # Single Docker Compose configuration
├── .github/workflows/         # CI/CD: build, test, lint, push, release
│   ├── docker-build-push.yml  # Build + push to GHCR + Docker Hub
│   └── lint-and-quality.yml   # Flake8, Black, Hadolint, YAML lint
├── .env.example               # Environment template
├── .dockerignore              # Build exclusions
├── verify_production.ps1      # Production readiness checker
└── vercel.json                # Vercel deploy config
```

## 🐳 Docker Setup

### Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│   ChromaDB   │
│  (nginx:80)  │     │  (FastAPI)   │     │  (Vector DB) │
│  Port: 3000  │     │  Port: 5000  │     │  Port: 8000  │
└──────────────┘     └──────────────┘     └──────────────┘
       │                     │                     │
       ▼                     ▼                     ▼
  mensa-net (internal bridge network)
```

### Services

| Service   | Image                                   | Base Image         | Key Features                         |
|-----------|-----------------------------------------|--------------------|--------------------------------------|
| frontend  | `ghcr.io/adportfolionode/mensa-frontend` | nginx:alpine       | Security headers, rate limiting, SPA |
| backend   | `ghcr.io/adportfolionode/mensa-backend`  | python:3.11-slim   | RAG, predictions, training, AI chat |
| chroma    | `chromadb/chroma:0.5.3`                 | official           | Vector database, persistent storage  |

### Security

- **Non-root users**: nginx (frontend) and appuser (backend) — never run as root
- **Multi-stage builds**: Minimal final images with only runtime dependencies
- **Health checks**: All services self-monitor with configurable intervals
- **Security headers**: HSTS, X-Frame-Options, X-Content-Type-Options, Permissions-Policy
- **Rate limiting**: 30 req/s at nginx, 100 req/min at backend (exempts health checks)
- **Network isolation**: Internal bridge network, no exposed ports except ingress
- **server_tokens off**: nginx version hidden from HTTP responses
- **Hidden file blocking**: `.env`, `.git`, secrets inaccessible via nginx

### Dockerfile Optimizations

**Backend (`backend/Dockerfile`)**:
- Multi-stage: `python:3.11-slim` builder → slim runtime
- Layer caching: `requirements.txt` copied and installed first
- Cache busting via `CACHE_BUSTER` arg for app code changes
- Chroma embedding warmup during build to speed first request
- Single hypercorn worker for consistent in-memory state
- Data directory at `/data` (mounted volume)

**Frontend (`frontend/Dockerfile`)**:
- Multi-stage: `node:22.13.1-slim` build → nginx:alpine serve
- `npm ci` installs locked dependencies (no lockfile needed — pure CRA)
- Custom nginx config with security + proxying

### Docker Commands

```bash
# Build and start
docker compose up --build -d

# Build specific service
docker compose build backend
docker compose build frontend

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop everything
docker compose down

# Stop and remove volumes (destroys data)
docker compose down -v

# Rebuild backend with cache busting
BACKEND_CACHE_BUSTER=$(date +%s) docker compose build backend
```

## 🔧 Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Key variables:

| Variable              | Required | Default                  | Description                      |
|-----------------------|----------|--------------------------|----------------------------------|
| `GEMINI_API_KEY`      | No       | —                        | Google Gemini API key            |
| `OPENAI_API_KEY`      | No       | —                        | OpenAI API key                   |
| `CHAT_GPT_API_KEY`    | No       | —                        | ChatGPT API key                  |
| `GROK_API_KEY`        | No       | —                        | xAI Grok API key                 |
| `GROK_API_BASE`       | No       | `https://api.x.ai/v1`    | Grok API base URL                |
| `GROK_MODEL`          | No       | `grok-3-mini-beta`       | Grok model name                  |
| `CHROMA_HOST`         | No       | `mensa_chroma`           | ChromaDB container hostname      |
| `CHROMA_PORT`         | No       | `8000`                   | ChromaDB port                    |
| `REACT_APP_API_BASE`  | Yes      | `http://localhost:5000`  | Backend URL for frontend         |
| `MAX_CONCURRENT_CLONES` | No     | `3`                      | Max parallel data fetches        |

## 🧪 Testing

### Quick Health Check

```bash
# Backend
curl http://localhost:5000/api/health

# Frontend
curl -I http://localhost:3000

# ChromaDB
curl http://localhost:8000/api/v1/heartbeat
```

### Automated Verification

```powershell
# Windows (PowerShell)
.\verify_production.ps1

# Run all checks including security headers
.\verify_production.ps1 -All
```

### Manual Endpoint Tests

```bash
# List available games
curl http://localhost:5000/api/games

# Get startup/ingestion status
curl http://localhost:5000/api/startup_status

# Check Chroma collections
curl http://localhost:5000/api/chroma/collections

# Get game summary (replace take5 with any game)
curl http://localhost:5000/api/games/take5/summary
```

## 🛠️ Development

### Local (Without Docker)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
hypercorn main:app --bind 0.0.0.0:5000

# Frontend
cd frontend
npm install
npm start
```

### Docker Development

```bash
# Build with cache busting for fresh installs
BACKEND_CACHE_BUSTER=$(date +%s) docker compose build backend

# Rebuild frontend with different Node version
docker compose build --build-arg NODE_VERSION=20.11.0 frontend

# Watch logs for a specific service
docker compose logs -f backend
```

## ☁️ Deploy to Vercel (Frontend Only)

The frontend can be deployed to Vercel for free. The backend must remain containerized.

### Setup

1. In Vercel dashboard: New Project → Import Git Repository
2. Build command: `npm --prefix frontend run build`
3. Output directory: `frontend/build`
4. Add environment variable in Vercel:
   - Key: `REACT_APP_API_BASE`
   - Value: `@backend_url` (Vercel secret reference)
5. Create secret: `backend_url` = your backend public URL

### Deploy

```bash
npx vercel login
npx vercel --prod
```

See `frontend/VERCEL_DEPLOYMENT.md` for full walkthrough.

## 🐳 Docker Hub Distribution

### Build & Push

```bash
# Login
docker login

# Tag and push
docker tag mensa-frontend:latest yourusername/mensa-frontend:latest
docker tag mensa-backend:latest yourusername/mensa-backend:latest
docker push yourusername/mensa-frontend:latest
docker push yourusername/mensa-backend:latest
```

### One-Click Run From Docker Hub

```bash
# 1. Edit docker-compose.hub.yml — set image: to your Docker Hub images
# 2. Copy .env.example → .env and configure
# 3. Run
docker compose -f docker-compose.hub.yml up -d
```

**Or run individual containers:**

```bash
docker run -d -p 3000:80 \
  -e REACT_APP_API_BASE=https://your-backend.com \
  yourusername/mensa-frontend:latest
```

## 🤖 CI/CD Pipeline

Two GitHub Actions workflows are included:

### 1. Build & Push (`docker-build-push.yml`)

Triggers:
- Push to `main` or `mensa`
- Pull request to `main` or `mensa`
- Tag push (`v*`)

Stages:
1. **Build & Test**: Builds both images, verifies backend imports and frontend build
2. **Push to Registry**: Pushes to GHCR and Docker Hub (on non-PR events)
3. **Draft Release**: Creates GitHub Release when a version tag is pushed

### 2. Lint & Quality (`lint-and-quality.yml`)

Triggers: push/PR to `main`/`mensa`
- `flake8` Python linting with error checking
- `black` Python formatting check (non-blocking)
- `hadolint` Dockerfile linting
- `yamllint` YAML validation

### Secrets Required

| Secret             | Description                     |
|--------------------|---------------------------------|
| `DOCKER_USERNAME`  | Docker Hub username             |
| `DOCKER_PASSWORD`  | Docker Hub access token         |

(No GHCR setup needed — `GITHUB_TOKEN` is auto-provided.)

## 🔄 Versioning & Releases

See `RELEASE_NOTES.md` for full changelog.

```bash
# Tag a release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main --tags

# CI automatically:
# 1. Builds and pushes images to GHCR + Docker Hub
# 2. Creates a GitHub Release with auto-generated notes
```

Version scheme: [SemVer](https://semver.org/)
- **MAJOR**: Breaking API changes
- **MINOR**: New games, providers, features
- **PATCH**: Bug fixes, security patches

## 📊 Supported Games

| Game         | Main Numbers   | Bonus      | Schedule         |
|--------------|----------------|------------|------------------|
| Take 5       | 5 (1–39)       | 1 (1–39)   | 2× daily         |
| Pick 3       | 3 (0–9)        | —          | 2× daily         |
| Powerball    | 5 (1–69)       | 1 (1–26)   | Mon, Wed, Sat    |
| Mega Millions| 5 (1–70)       | 1 (1–25)   | Tue, Fri         |
| Pick 10      | 20 (1–80)      | —          | Daily            |
| Cash4Life    | 5 (1–60)       | 1 (1–4)    | Daily            |
| Quick Draw   | 20 (1–80)      | —          | ~360× daily      |
| NY Lotto     | 6 (1–59)       | 1 (1–59)   | Wed, Sat         |

## 🔒 Security Best Practices

1. **Never commit `.env` files** — `.env` is gitignored; use `.env.example`
2. **Rotate API keys regularly**
3. **Keep base images updated**: `docker compose build --no-cache --pull`
4. **Use specific version tags** in production, not `latest`
5. **Scan images**: `docker scan yourusername/mensa-frontend:latest`
6. **Limit exposed ports**: Only `3000` (frontend) should be public; restrict `5000` and `8000`
7. **Enable Docker content trust** for supply chain security

## 🐛 Troubleshooting

### Port Conflicts

```yaml
# In compose.yaml, change host ports:
ports:
  - "3001:80"   # Frontend on 3001
  - "5001:5000" # Backend on 5001
```

### Container Won't Start

```bash
# Check logs
docker compose logs backend

# Verify health
docker inspect mensa_backend | jq '.[].State.Health'

# Restart specific service
docker compose restart backend
```

### Volume Permissions

```bash
docker compose down
docker compose run --rm backend chown -R appuser:appuser /data
docker compose up -d
```

### Reset Everything

```bash
docker compose down -v        # Stops and removes volumes
docker system prune -a -f     # Cleans all unused images
docker compose up --build -d  # Fresh start
```

## 📄 License

See `LICENSE` file details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`feat/your-feature`)
3. Make changes
4. Submit a pull request to `mensa` branch

Run the CI checks locally before pushing:
```bash
pip install flake8 black
flake8 backend/ --select=E9,F63,F7,F82 --show-source
black --check backend/ --diff
