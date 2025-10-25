# Redis Wellness 🏥

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/typescript-5.6+-blue.svg)](https://www.typescriptlang.org/)
[![Redis](https://img.shields.io/badge/redis-7.0+-red.svg)](https://redis.io/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Privacy](https://img.shields.io/badge/privacy-100%25%20local-success.svg)](#-privacy)

> **Can AI agents be intelligent without memory?**

A side-by-side demo comparing stateless chat vs. agentic RAG chat powered by **Redis + RedisVL**. Same AI, with and without memory - the difference is dramatic.

🔒 **100% local** - Your health data never leaves your machine (Ollama + Redis)

## 🎯 The Demo

| Stateless Chat | Redis RAG Chat |
|----------------|----------------|
| ❌ Forgets context immediately | ✅ Remembers conversation history |
| ❌ Can't answer "Is that good?" | ✅ Understands pronouns & references |
| ❌ No memory between messages | ✅ Dual memory (short + long-term) |
| ❌ Repeats same questions | ✅ Semantic search with RedisVL |

**Try it yourself:**
```bash
You: "What was my average heart rate last week?"
Bot: "87 bpm"

You: "Is that good?"
❌ Stateless: "What are you referring to?"
✅ Redis RAG: "87 bpm is within normal range for your age group..."
```

## 🏭 Architecture

```
User → Frontend (TypeScript) → Backend (FastAPI) → Redis + RedisVL
                                      ↓
                                   Ollama (Local LLM)
```

**The key difference:** Redis RAG agent stores conversation in Redis (short-term) and uses RedisVL vector search (long-term semantic memory). Stateless agent has no memory at all.

**Tech Stack:** FastAPI • Redis • RedisVL • Ollama (Qwen 2.5 7B) • TypeScript • Docker

## ✨ Features

- 🤖 **Agentic tool calling** - 9 specialized health tools with autonomous selection
- 🧠 **Dual memory system** - Short-term (Redis LIST) + long-term (RedisVL vector search)
- 📊 **Apple Health integration** - Import and analyze your health data
- 🔒 **100% private** - All processing local (Ollama + Redis)
- ⚡ **Real-time streaming** - SSE streaming responses
- 🧪 **Production-ready** - Comprehensive tests, code quality checks, Docker

## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose** - For running all services
2. **Ollama** - For local LLM inference (runs on host)

### Install Ollama & Models

**Why Ollama + Qwen?**
- 🔒 **100% Privacy**: Runs locally, your health data never leaves your machine
- ⚡ **Fast Setup**: One-command install, no API keys or cloud accounts
- 🧠 **Smart Tool Calling**: Qwen 2.5 7B excels at function calling for agentic workflows
- 📊 **Reasonable Size**: 4.7 GB model runs on most modern laptops
- 🎯 **Optimized for Tools**: Better tool selection than larger general-purpose models

```bash
# Install Ollama (macOS)
brew install ollama

# Or download from https://ollama.ai

# Start Ollama service
ollama serve

# In another terminal, pull the models
ollama pull qwen2.5:7b              # Main LLM - optimized for tool calling (4.7 GB)
ollama pull mxbai-embed-large       # Embeddings - for semantic search (669 MB)
```

> **Note**: First run will download models (~5.4 GB total). Subsequent runs are instant.

### Start the Application

**Option 1: Quick start (recommended)**

```bash
chmod +x start.sh
./start.sh
```

This script:
1. Checks Docker and Ollama are running
2. Verifies required models are installed
3. Starts all services with `docker-compose`
4. Opens the UI at http://localhost:3000

**Option 2: Manual start**

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### Access Points

- **Frontend Demo UI**: http://localhost:3000 (side-by-side chat comparison)
- **Backend API Docs (Swagger)**: http://localhost:8000/docs
- **Backend API Docs (ReDoc)**: http://localhost:8000/redoc
- **RedisInsight**: http://localhost:8001 (visualize Redis data)
- **Health Check**: http://localhost:8000/api/health/check
- **Demo Info**: http://localhost:8000/api/chat/demo/info

## 📊 Using the Demo

Open http://localhost:3000 and try the side-by-side comparison. The UI shows memory stats in real-time.

**Example workflow:**
1. Ask both agents: "What was my average heart rate last week?"
2. Follow up with: "Is that good?"
3. Watch stateless forget, Redis RAG remember ✅

**Load your Apple Health data:**
```bash
python import_health_data.py export.xml
```

> **Learn more:** See [RAG_IMPLEMENTATION.md](./docs/RAG_IMPLEMENTATION.md) for memory architecture details

## 📚 Documentation

- **[WARP.md](./WARP.md)** - Complete development guide
- **[RAG_IMPLEMENTATION.md](./docs/RAG_IMPLEMENTATION.md)** - Memory architecture deep dive
- **[LANGGRAPH_REMOVAL_PLAN.md](./docs/LANGGRAPH_REMOVAL_PLAN.md)** - Why simple loop > LangGraph
- **[HEALTH_DATA_PIPELINE.md](./docs/HEALTH_DATA_PIPELINE.md)** - Apple Health data processing
- **[TEST_PLAN.md](./backend/TEST_PLAN.md)** - Testing strategy

## 🔧 Development

### API Docs

API documentation available at:
- **Swagger**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Testing

```bash
cd backend
uv run pytest tests/ -v              # All tests
uv run pytest tests/unit/ -v         # Unit tests only
```

### Code Quality

```bash
./lint.sh                            # Run all linters
```


## 🐛 Troubleshooting

```bash
# Services not starting?
docker-compose logs -f backend
docker-compose logs -f frontend

# Ollama not running?
curl http://localhost:11434/api/version
ollama list

# Redis issues?
docker-compose ps redis
redis-cli -h localhost -p 6379 ping

# Port conflicts?
lsof -i :3000 :8000 :6379 :11434
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Redis + RedisVL • Demonstrating why memory matters in AI</strong><br>
  Built with ❤️ by <a href="https://github.com/AllieRays">@AllieRays</a>
</p>
