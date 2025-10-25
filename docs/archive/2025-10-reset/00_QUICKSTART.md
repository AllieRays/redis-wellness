# Quickstart

This demo compares a stateless AI agent with a stateful RAG agent using Redis and RedisVL over your local Apple Health data.

- Frontend: http://localhost:3000
- API: http://localhost:8000/docs
- RedisInsight: http://localhost:8001

## 1) Start the stack

```bash path=null start=null
# Build and start services
docker compose up --build -d

# Verify containers
docker compose ps
```

## 2) Ensure Ollama is running with required models

```bash path=null start=null
# Install/start Ollama (macOS example)
brew install ollama || true
ollama serve &

# Pull models used by the app
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large
```

## 3) Import Apple Health data (one-time)

Place your export at `apple_health_export/export.xml`, then run:

```bash path=null start=null
# From repo root; imports XML → Redis and builds workout indexes
uv run python import_health_data.py apple_health_export/export.xml
```

## 4) Try the comparison

- Stateless (no memory):
```bash path=null start=null
curl -s -X POST http://localhost:8000/api/chat/stateless \
  -H 'Content-Type: application/json' \
  -d '{"message": "What was my average heart rate last week?"}' | jq '.response'
```

- Stateful (memory; use a session_id):
```bash path=null start=null
curl -s -X POST http://localhost:8000/api/chat/stateful \
  -H 'Content-Type: application/json' \
  -d '{"message": "What was my average heart rate last week?", "session_id": "demo-1"}' | jq '.response'

# Follow-up relies on memory
curl -s -X POST http://localhost:8000/api/chat/stateful \
  -H 'Content-Type: application/json' \
  -d '{"message": "Is that good?", "session_id": "demo-1"}' | jq '.response'
```

## Architecture (high level)

```mermaid path=null start=null
flowchart LR
    UI[Frontend (Vite, TS):3000]
    API[FastAPI Backend:8000]
    R[(Redis Stack:6379)]
    O[Ollama:11434\nQwen 2.5 7B + mxbai-embed-large]

    UI -- HTTP --> API
    API <---> R
    API <---> O

    subgraph Memory
      R ---|Short-term| R
      R ---|Episodic/Procedural/Semantic via RedisVL| R
    end
```
