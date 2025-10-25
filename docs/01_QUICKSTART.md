# Quickstart

Get the demo running in 5 minutes.

## Prerequisites

- Docker & Docker Compose
- Ollama installed and running

## 1. Install Ollama & Pull Models

```bash
# Install Ollama (macOS)
brew install ollama

# Or download from https://ollama.ai

# Start Ollama service
ollama serve

# In another terminal, pull required models
ollama pull qwen2.5:7b              # LLM for chat (4.7 GB)
ollama pull mxbai-embed-large       # Embeddings for memory (669 MB)
```

> **Note**: First run downloads ~5.4 GB total. Subsequent runs are instant.

## 2. Start the Demo

**Option 1: Quick start script (recommended)**

```bash
chmod +x start.sh
./start.sh
```

This script checks dependencies and starts all services.

**Option 2: Manual start**

```bash
# Build and start all services
docker compose up --build

# Or run in detached mode
docker compose up -d --build
```

## 3. Access the Demo

Open **http://localhost:3000** in your browser.

You'll see a side-by-side comparison:
- **Left**: Stateless agent (no memory)
- **Right**: Stateful agent (Redis-powered memory)

## 4. Try the Comparison

Ask both agents the same questions:

```
You: "How many workouts do I have?"
Bot: "You have 154 workouts recorded."

You: "What day do I work out most?"
Bot: "Friday is your most common workout day (50% of recent workouts)."

You: "Why did you say that?"
❌ Stateless: "I don't have context about what I said before."
✅ Stateful: "Based on your last 6 workouts, 3 were on Friday..."
```

Watch the **Performance Comparison** table update in real-time showing:
- Token usage
- Response latency

## 5. Use Your Own Data (Optional)

Load your Apple Health export:

```bash
# Export from iPhone: Health app → Profile → Export All Health Data
# Place export.xml in apple_health_export/

python import_health_data.py apple_health_export/export.xml
```

See [07_APPLE_HEALTH_DATA.md](./07_APPLE_HEALTH_DATA.md) for details.

## Troubleshooting

**Services not starting?**
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

**Ollama not running?**
```bash
curl http://localhost:11434/api/version
ollama list
```

**Redis issues?**
```bash
docker compose ps redis
redis-cli -h localhost -p 6379 ping
```

## Next Steps

- [02_THE_DEMO.md](./02_THE_DEMO.md) - Understand what you're seeing
- [03_MEMORY_ARCHITECTURE.md](./03_MEMORY_ARCHITECTURE.md) - Learn about Redis memory patterns
- [04_AUTONOMOUS_AGENTS.md](./04_AUTONOMOUS_AGENTS.md) - Learn about agentic tool calling
