# Redis Wellness 🏥

> Why memory matters for personalized private wellness conversations using Redis, health data, and local AI

A privacy-first wellness application demonstrating how Redis provides conversational memory for AI-powered health insights. Built with FastAPI, Redis, and local LLMs (Ollama) - your health data never leaves your machine.

## 🎯 Why This Matters

Most chat applications are stateless - they forget everything between sessions. This project shows how Redis transforms simple chat into an intelligent, context-aware conversation by:

- **Remembering past conversations** - Reference previous discussions naturally
- **Accessing health context** - Connect your current question with historical health data
- **Building relationships** - Track patterns and provide personalized insights over time

## 🏗️ Architecture

```
                           Docker Network
┌──────────────────────────────────────────────┐
│                                                              │
│  Frontend (TS+Vite) ────→ Backend (FastAPI) ───→ Redis  │
│       :3000                    :8000             :6379    │
│                                  ↓                       │
│                           Ollama (Host)                   │
│                              :11434                        │
└──────────────────────────────────────────────┘

Redis stores:
- Conversation history
- Health data cache
- Session management
```

## ✨ Features

- **Fully Dockerized**: One command to start everything
- **Private by default**: All data stays local (Redis + Ollama)
- **Conversational memory**: Redis stores and retrieves conversation context
- **TypeScript frontend**: Type-safe, modern UI with Vite
- **FastAPI backend**: Python async API with automatic docs
- **Health data integration**: Import Apple Health XML exports
- **No API costs**: Uses free, local Ollama LLMs

## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose** - For running all services
2. **Ollama** - For local LLM inference (runs on host)

### Install Ollama

```bash
# macOS
brew install ollama

# Or download from https://ollama.ai

# Start Ollama
ollama serve

# In another terminal, pull a model
ollama pull llama3.1
```

### Start Everything

**Option 1: Use the start script (recommended)**

```bash
./start.sh
```

**Option 2: Manual start**

```bash
docker-compose up --build
```

### Access the Application

- **Frontend UI**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **RedisInsight**: http://localhost:8001

## 📊 Loading Health Data

### Export from Apple Health

1. Open Health app on iPhone
2. Tap your profile picture
3. Scroll down → "Export All Health Data"
4. Save and transfer `export.xml` to your computer

### Upload via API

```bash
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@export.xml"
```

Or use the API docs at `http://localhost:8000/docs`

## 🧪 Try It Out

Once everything is running, try these example conversations:

1. **"What's my average heart rate this week?"**
   - Shows how Redis retrieves and aggregates health data

2. **"How did I sleep last night?"**
   - Demonstrates accessing time-series health metrics

3. **Follow up: "Has it improved from last week?"**
   - Memory in action - the AI remembers what "it" refers to

4. **Start a new session, then ask: "What did we discuss last time?"**
   - Shows cross-session memory persistence

## 🔧 Development

### Project Structure

```
.
├── backend/              # FastAPI application
│   ├── src/
│   │   ├── main.py      # FastAPI app
│   │   ├── api/         # API routes
│   │   ├── models/      # Pydantic schemas
│   │   ├── services/    # Redis & Ollama services
│   │   └── parsers/     # Apple Health XML parser
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/             # TypeScript + Vite
│   ├── src/
│   │   ├── main.ts      # Application logic
│   │   ├── api.ts       # Backend API client
│   │   ├── types.ts     # TypeScript types
│   │   └── style.css    # UI styles
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── docker-compose.yml    # Orchestrates all services
└── start.sh              # Quick start script
```

### Start Script

The `start.sh` script provides a convenient way to start all services:

```bash
#!/bin/bash

echo "🏭 Starting Redis Wellness..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Warning: Ollama is not running."
    echo "   Start Ollama with: ollama serve"
    echo "   Then pull a model: ollama pull llama3.1"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start all services
echo "🚀 Starting all services..."
docker-compose up --build
```

Make it executable:

```bash
chmod +x start.sh
```

### Stopping Services

```bash
# Stop all
docker-compose down

# Stop and remove volumes (clears Redis data)
docker-compose down -v
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### API Documentation

Interactive API docs available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🎓 How Memory Works

### 1. Conversation Storage

Each message is stored in Redis with:

- Session ID for grouping
- Timestamp for ordering
- Role (user/assistant)
- Content

```python
conversation:{session_id}:{message_id} → {role, content, timestamp}
```

### 2. Context Retrieval

When you send a message:

1. Your message is stored in Redis
2. Last N messages are retrieved for context
3. Relevant health data is fetched
4. Everything is sent to Ollama as context
5. AI response is stored back in Redis

### 3. Health Data Integration

Health metrics are cached in Redis:

```python
health:{metric_type}:{date} → {value, unit, source}
```

Fast queries for:

- Recent averages
- Time-based trends
- Specific metric types

## 🔒 Privacy

- **Local LLM**: Ollama runs on your machine
- **Local storage**: Redis runs on your machine
- **No external APIs**: Zero data sent to third parties
- **Data control**: You own and control everything

## 📝 Blog Post Outline

This project demonstrates:

1. **The Problem**: Stateless chat = no personalization
2. **The Solution**: Redis as a memory layer
3. **Implementation**: FastAPI + Redis + Ollama
4. **Demo**: Real conversations showing memory in action
5. **Results**: Personalized, context-aware health insights

## 🛠️ Configuration

Edit `.env` to customize:

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1

# App
APP_HOST=0.0.0.0
APP_PORT=8000
```

## 🐛 Troubleshooting

**Services not starting?**

```bash
# Check Docker is running
docker ps

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

**Ollama not responding?**

```bash
# Check if Ollama is running
curl http://localhost:11434

# Start Ollama
ollama serve

# Check installed models
ollama list
```

**Frontend can't reach backend?**

```bash
# Check backend is running
docker-compose logs backend

# Check network
docker network inspect redis-wellness_wellness-network
```

**Build fails?**

```bash
# Clean rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up
```

## 📚 Resources

- [Redis Documentation](https://redis.io/docs/)
- [Ollama Documentation](https://ollama.ai)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [TypeScript Documentation](https://www.typescriptlang.org/)
- [Vite Documentation](https://vitejs.dev/)
- [Docker Documentation](https://docs.docker.com/)

## 🤝 Contributing

This is a demo project for a blog post, but feel free to:

- Report issues
- Suggest improvements
- Share your own examples

## 📄 License

MIT

---

Built with ❤️ to demonstrate why memory matters in AI conversations
