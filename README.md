# Mensa Predictive RAG - Production-Ready Docker Application

A full-stack predictive analytics and RAG (Retrieval-Augmented Generation) application for lottery data analysis, featuring a React frontend, Python FastAPI backend with ChromaDB vector database, and multi-model AI integration.

## 🚀 Quick Start

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### One-Command Deployment

```bash
# Clone the repository
git clone <repository-url>
cd mensa_project

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys

# Build and start all services
docker compose up --build -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:5000
# ChromaDB: http://localhost:8000
```

## 📁 Project Structure

```
mensa_project/
├── frontend/              # React frontend (Create React App)
│   ├── Dockerfile         # Multi-stage build with nginx
│   ├── nginx.conf         # API proxy configuration
│   └── src/               # React components
├── backend/               # Python FastAPI backend
│   ├── Dockerfile         # Multi-stage build with non-root user
│   ├── main.py            # FastAPI application with /api/health endpoint
│   ├── requirements.txt   # Python dependencies
│   └── services/          # RAG, ChromaDB, AI services
├── compose.yaml           # Docker Compose configuration
├── docker-compose.yml     # Docker Compose compatibility file
├── .dockerignore          # Docker build exclusions
└── .env.example           # Environment variables template
```

## 🔧 Docker Configuration

### Security Features
- **Non-root users**: Both frontend (nginx) and backend (appuser) run as non-root users
- **Multi-stage builds**: Minimal final images for reduced attack surface
- **Health checks**: Automated health monitoring for all services
- **Network isolation**: Custom bridge network for service communication
- **Secrets management**: Environment variables for sensitive data

### Services

#### Frontend (React + nginx)
- **Base Image**: node:22.13.1-slim → nginx:alpine
- **Port**: 3000 (external) → 80 (internal)
- **Features**: Static file serving, API proxy to backend, health checks
- **Health Check**: HTTP GET to root endpoint every 30s

#### Backend (Python FastAPI)
- **Base Image**: python:3.11-slim (multi-stage)
- **Port**: 5000
- **Features**: RAG with ChromaDB, multi-model AI (GPT, Gemini, Grok), lottery prediction
- **Health Check**: Socket connection to port 5000 every 10s
- **Memory Limit**: 4GB

#### ChromaDB (Vector Database)
- **Image**: chromadb/chroma:0.5.3
- **Port**: 8000
- **Features**: Persistent vector storage for RAG
- **Health Check**: API heartbeat endpoint every 30s

## 🔑 Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Frontend
REACT_APP_API_BASE=http://localhost:5000

# Backend - API Keys (Required)
GEMINI_API_KEY=your_gemini_api_key_here
CHAT_GPT_API_KEY=your_chatgpt_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GROK_API_KEY=your_grok_api_key_here

# Backend - Configuration
DATA_DIR=/data
CHROMA_HOST=mensa_chroma
CHROMA_PORT=8000
MAX_CONCURRENT_CLONES=3
```

## 🛠️ Development

### Local Development (Without Docker)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
hypercorn main:app --bind 0.0.0.0:5000

# Frontend
cd frontend
npm install
npm start
```

### Docker Development

```bash
# Build specific service
docker compose build frontend
docker compose build backend

# Rebuild with cache busting
BACKEND_CACHE_BUSTER=$(date +%s) docker compose build backend

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v
```

## 🧪 Testing

### Health Checks

```bash
# Backend health
curl http://localhost:5000/api/health

# Frontend health
curl http://localhost:3000

# ChromaDB health
curl http://localhost:8000/api/v1/heartbeat
```

### API Endpoints

```bash
# Get available games
curl http://localhost:5000/api/games

# Get startup status
curl http://localhost:5000/api/startup_status

# Get ChromaDB status
curl http://localhost:5000/api/chroma/status
```

## 📦 Distribution

### Docker Hub Deployment

```bash
# Tag images
docker tag mensa_frontend:latest yourusername/mensa-frontend:latest
docker tag mensa_backend:latest yourusername/mensa-backend:latest

# Push to Docker Hub
docker push yourusername/mensa-frontend:latest
docker push yourusername/mensa-backend:latest
```

### One-Click Run (From Docker Hub)

```bash
docker run -d \
  -p 3000:80 \
  -e REACT_APP_API_BASE=http://your-backend-host:5000 \
  yourusername/mensa-frontend:latest
```

## 🔄 CI/CD

See `.github/workflows/` for automated build and deployment workflows:
- `build-and-push-backend.yml` - Backend CI/CD
- Additional workflows can be added for frontend and full stack

## 📊 Monitoring

### Container Status

```bash
docker compose ps
docker compose top
```

### Resource Usage

```bash
docker stats
```

### Logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs backend
docker compose logs frontend
docker compose logs chroma
```

## 🔒 Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Rotate API keys regularly** - Update environment variables
3. **Use secrets management** - Consider Docker Secrets or external vault
4. **Keep images updated** - Regularly rebuild with latest base images
5. **Network isolation** - Services communicate via internal network only
6. **Resource limits** - Memory and CPU limits prevent resource exhaustion

## 🐛 Troubleshooting

### Port Conflicts

```bash
# Change ports in compose.yaml or docker-compose.yml
ports:
  - "3001:80"  # Frontend on 3001
  - "5001:5000" # Backend on 5001
```

### Permission Issues

```bash
# Fix volume permissions
docker compose down
sudo chown -R $USER:$USER ./data
docker compose up -d
```

### Build Failures

```bash
# Clear Docker cache
docker system prune -a
docker compose build --no-cache
```

### Service Not Starting

```bash
# Check service health
docker compose ps
docker compose logs backend

# Restart specific service
docker compose restart backend
```

## 📝 License

See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Support

For issues and questions, please open a GitHub issue.
