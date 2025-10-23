# Redis Wellness AI - Documentation

**Version**: 1.0.0
**Last Updated**: October 2025

---

## Overview

Redis Wellness AI is a technical demonstration showcasing Redis + RedisVL for building stateful AI applications. The project compares **stateless vs stateful agents** side-by-side to demonstrate the transformative power of memory in conversational AI.

**Key Technologies**:
- **Backend**: FastAPI + Python + LangChain
- **Frontend**: TypeScript + Vite
- **Database**: Redis Stack 7.4 + RedisVL (vector search)
- **LLM**: Qwen 2.5 7B + mxbai-embed-large (via Ollama)
- **Architecture**: Agentic tool-calling with dual memory system

---

## Documentation Structure

### Getting Started
- **[Quick Start Guide](./01_QUICK_START.md)** - Get running in 5 minutes
- **[Prerequisites](./02_PREREQUISITES.md)** - Required software and setup

### Architecture
- **[System Architecture](./03_ARCHITECTURE.md)** - High-level system design
- **[Memory System](./04_MEMORY_SYSTEM.md)** - Dual memory architecture (Redis + RedisVL)
- **[Agent Comparison](./05_AGENT_COMPARISON.md)** - Stateless vs Stateful agents

### Development
- **[Development Guide](./06_DEVELOPMENT.md)** - Local development workflow
- **[Testing Guide](./07_TESTING.md)** - Running and writing tests
- **[Code Quality](./08_CODE_QUALITY.md)** - Linting, formatting, pre-commit hooks

### API Reference
- **[API Documentation](./09_API.md)** - Endpoints, request/response formats
- **[Health Data Integration](./10_HEALTH_DATA.md)** - Apple Health XML import pipeline

### Deployment
- **[Docker Deployment](./11_DEPLOYMENT.md)** - Production deployment guide
- **[Configuration](./12_CONFIGURATION.md)** - Environment variables and settings

### Demo Presentation
- **[Demo Guide](./13_DEMO_GUIDE.md)** - Presentation script for technical demos

---

## Quick Links

### Running the Application
```bash
# Quick start
docker-compose up --build

# Access points
http://localhost:3000  # Frontend
http://localhost:8000  # Backend API
http://localhost:8001  # RedisInsight
```

### Common Commands
```bash
# Backend tests
cd backend && uv run pytest tests/

# Frontend development
cd frontend && npm run dev

# Linting
./lint.sh
```

---

## Project Structure

```
redis-wellness/
├── backend/
│   ├── src/
│   │   ├── agents/          # AI agents (stateless vs stateful)
│   │   ├── services/        # Data layer (Redis, memory)
│   │   ├── utils/           # Pure utilities
│   │   ├── api/             # HTTP endpoints
│   │   └── apple_health/    # Health data processing
│   └── tests/               # All backend tests
├── frontend/
│   └── src/                 # TypeScript + Vite
├── docs/                    # Documentation (you are here)
└── docker-compose.yml       # Service orchestration
```

---

## Key Features

### 1. Dual Memory Architecture
- **Short-term**: Redis LIST for recent conversation (last 10 messages)
- **Long-term**: RedisVL HNSW index for semantic search (1024-dim vectors)

### 2. Side-by-Side Comparison
- Same agent implementation with/without memory
- Identical tools, LLM, and validation
- 186 lines of code = entire memory system

### 3. Production-Ready Patterns
- Connection pooling (20 max connections)
- Circuit breaker pattern (5 failures → OPEN)
- Graceful degradation
- Comprehensive error handling

### 4. Privacy-First
- 100% local processing (no cloud APIs)
- Ollama for LLM inference
- Redis for data storage
- Self-contained Docker environment

---

## Contributing

This is a technical demonstration project. For development:

1. Follow the **[Development Guide](./06_DEVELOPMENT.md)**
2. Run tests before committing: `uv run pytest tests/`
3. Use pre-commit hooks: `pre-commit install`
4. Follow existing code patterns and conventions

---

## Support

- **Issues**: Review existing docs first, then check archived docs in `/docs/archive/`
- **Questions**: See **[FAQ](./14_FAQ.md)** for common questions

---

## License

This project is a technical demonstration for Redis interview purposes.

---

**Next Steps**: Start with the **[Quick Start Guide](./01_QUICK_START.md)** to get the application running.
