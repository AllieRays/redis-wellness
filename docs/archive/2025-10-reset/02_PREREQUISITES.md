# Prerequisites

Software and setup required to run Redis Wellness AI.

---

## Required Software

### 1. Docker Desktop

**Purpose**: Container orchestration for Redis, backend, and frontend.

**Installation**:
```bash
# macOS
brew install --cask docker

# Or download from: https://www.docker.com/products/docker-desktop
```

**Verification**:
```bash
docker --version
# Expected: Docker version 24.0.0 or higher

docker-compose --version
# Expected: Docker Compose version 2.20.0 or higher
```

**Start Docker Desktop** before proceeding.

---

### 2. Ollama

**Purpose**: Local LLM inference for Qwen 2.5 7B and embeddings.

**Installation**:
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from: https://ollama.com/download
```

**Verification**:
```bash
ollama --version
# Expected: ollama version 0.1.0 or higher

# Check if Ollama is running
curl http://localhost:11434
# Expected: "Ollama is running"
```

**Start Ollama**:
```bash
# Run in background
ollama serve

# Or as a service (macOS)
brew services start ollama
```

---

### 3. Pull Required Models

**Qwen 2.5 7B** (Main LLM):
```bash
ollama pull qwen2.5:7b
# Size: 4.7 GB
# Time: 5-10 minutes
```

**mxbai-embed-large** (Embeddings):
```bash
ollama pull mxbai-embed-large
# Size: 669 MB
# Time: 1-2 minutes
```

**Verify Models**:
```bash
ollama list
# Expected output:
# qwen2.5:7b           4.7 GB
# mxbai-embed-large    669 MB
```

---

## Apple Health Data (Optional)

**For real health insights**, you'll need your Apple Health export.

### Quick Export Steps:

1. Open **Health app** on iPhone
2. Tap **profile icon** (top right)
3. Scroll down → **"Export All Health Data"**
4. Save `export.zip` and extract `export.xml`

**Detailed instructions**: See [Health Data Guide](./10_HEALTH_DATA.md)

**Don't have data?** The demo works without it - it will just respond that no data is available. Or generate sample data:
```bash
cd backend
uv run python scripts/generate_sample_data.py
```

---

## Optional Software

### 1. Python (for backend development)

**Only needed if developing backend outside Docker.**

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify
uv --version
# Expected: uv 0.1.0 or higher
```

---

### 2. Node.js (for frontend development)

**Only needed if developing frontend outside Docker.**

```bash
# macOS
brew install node

# Verify
node --version
# Expected: v18.0.0 or higher

npm --version
# Expected: 9.0.0 or higher
```

---

## System Requirements

### Minimum
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Disk**: 15 GB free space
- **OS**: macOS 12+, Ubuntu 20.04+, Windows 10+ with WSL2

### Recommended
- **CPU**: 8 cores
- **RAM**: 16 GB
- **Disk**: 30 GB free space (for development)
- **GPU**: Optional (Ollama supports GPU acceleration)

---

## Network Requirements

**Required Ports**:
- `3000` - Frontend
- `6379` - Redis
- `8000` - Backend API
- `8001` - RedisInsight
- `11434` - Ollama

**Verify Ports Are Available**:
```bash
# Check if ports are free
lsof -i :3000
lsof -i :6379
lsof -i :8000
lsof -i :8001
lsof -i :11434

# If any port is in use, stop the conflicting service
```

---

## Pre-Run Checklist

Before running `docker-compose up`:

- [ ] Docker Desktop is running
- [ ] Ollama is running (`curl http://localhost:11434` succeeds)
- [ ] Models are pulled (`ollama list` shows both models)
- [ ] Ports 3000, 6379, 8000, 8001 are available
- [ ] At least 10 GB free disk space

---

## Troubleshooting

### Docker Desktop Not Starting
```bash
# macOS: Reset Docker Desktop
# Docker Desktop → Preferences → Reset → Reset to factory defaults
```

### Ollama Models Not Pulling
```bash
# Check internet connection
ping ollama.com

# Manually download model
ollama pull qwen2.5:7b --insecure
```

### Permission Denied Errors
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Then log out and log back in
```

---

**Next Step**: Continue to [Quick Start Guide](./01_QUICK_START.md)
