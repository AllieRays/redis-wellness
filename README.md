# Redis Wellness 🧠💾

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/typescript-5.6+-blue.svg)](https://www.typescriptlang.org/)
[![Redis](https://img.shields.io/badge/redis-7.0+-red.svg)](https://redis.io/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Privacy](https://img.shields.io/badge/privacy-100%25%20local-success.svg)](#privacy)

> **Can AI be intelligent without memory?**

Compare two identical AI agents side-by-side. Same LLM. Same tools. One difference: **Redis memory**.

See how Redis + RedisVL transforms stateless Q&A into intelligent conversation with context awareness, goal recall, and pattern learning.

🔒 **100% local** - Your health data never leaves your machine.

---

## 🎯 The Difference

### Stateless Agent (No Memory)

```mermaid
flowchart TB
    UI["User Interface"]
    Router["Intent Router<br/>(Pre-LLM)<br/>Pattern matching"]

    Simple["Redis<br/>(Simple Queries)"]
    SimpleLoop["Simple Tool Loop<br/>• Qwen 2.5 7B LLM<br/>• Tool calling<br/>• Response synthesis"]

    Tools["Health Tools<br/>(3 tools)"]
    RedisData["Redis Health Data Store"]
    Forget["❌ FORGET EVERYTHING"]

    UI --> Router
    Router -->|"Simple"| Simple
    Router -->|"Complex"| SimpleLoop
    Simple --> RedisData
    SimpleLoop --> Tools
    Tools --> RedisData
    RedisData --> Forget

    style UI fill:#fff,stroke:#6c757d,stroke-width:2px,color:#000
    style Router fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Simple fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style SimpleLoop fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Tools fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style RedisData fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Forget fill:#fff,stroke:#dc3545,stroke-width:2px,color:#dc3545,stroke-dasharray: 5 5
```

### Stateful Agent (With Memory)

```mermaid
flowchart TB
    UI["User Interface"]
    Router["Intent Router<br/>(Pre-LLM)<br/>Pattern matching"]
    Simple["Redis<br/>(Simple Queries)"]
    Complex["LangGraph StateGraph<br/>• Qwen 2.5 7B LLM<br/>• Tool calling loop<br/>• Response synthesis"]
    RedisShort["Redis Short-term<br/>Checkpointing"]
    RedisVL["RedisVL<br/>Episodic + Procedural<br/>Vector Search"]
    Tools["LLM Tools<br/>(5 total: 3 health + 2 memory)"]
    Store["✅ STORE MEMORY"]

    UI --> Router
    Router -->|"Fast path"| Simple
    Router -->|"Complex path"| Complex
    Complex --> RedisShort
    Complex --> RedisVL
    Complex --> Tools
    Tools --> Store

    style UI fill:#fff,stroke:#6c757d,stroke-width:2px,color:#000
    style Router fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Simple fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Complex fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style RedisShort fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style RedisVL fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Tools fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style Store fill:#fff,stroke:#28a745,stroke-width:2px,color:#28a745,stroke-dasharray: 5 5
```

**Key difference:** Redis memory enables follow-up questions, goal recall, and pattern learning.

**[📖 See detailed comparison →](docs/05_STATELESS_VS_STATEFUL_COMPARISON.md)**

---

## 🚀 Quick Start

```bash
# 1. Start services
make up

# 2. Import Apple Health data
make import

# 3. Open http://localhost:3000
```

**Try it:**
- Ask both agents: *"How many workouts do I have?"* → Both answer correctly ✅
- Follow up: *"What's the most common type?"*
  - ❌ Stateless: *"What are you referring to?"*
  - ✅ Stateful: *"Traditional Strength Training (40 workouts, 26%)\"*

**[📖 Full setup guide →](docs/02_QUICKSTART.md)**

---

## 📚 Documentation

**Quick Start:**
- [Prerequisites](docs/01_PREREQUISITES.md) - Docker, Ollama, Apple Health export
- [Quickstart](docs/02_QUICKSTART.md) - Running in 5 minutes
- [Example Queries](docs/09_EXAMPLE_QUERIES.md) - Try these to see memory in action

**Architecture Deep Dives:**
- [Stateless vs Stateful Comparison](docs/05_STATELESS_VS_STATEFUL_COMPARISON.md) - Side-by-side breakdown
- [Memory Architecture](docs/10_MEMORY_ARCHITECTURE.md) - Four-layer memory system
- [Agentic RAG](docs/06_AGENTIC_RAG.md) - How tool calling works
- [LangGraph Checkpointing](docs/12_LANGGRAPH_CHECKPOINTING.md) - Conversation state

**[📖 All 13 docs →](docs/)**

---

## 🛠️ Tech Stack

- **Backend:** FastAPI + Python 3.11
- **Frontend:** TypeScript + Vite
- **AI:** Ollama (Qwen 2.5 7B) + LangChain
- **Memory:** Redis + RedisVL (HNSW vector search)
- **Privacy:** 100% local processing

---

## 🤝 Contributing

This is a demo project showcasing Redis + RedisVL for AI agent memory. Feel free to:
- Open issues for bugs or questions
- Submit PRs for improvements
- Use as reference for your own projects

---

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

**Built to showcase Redis + RedisVL for intelligent AI agents** 🧠💾
