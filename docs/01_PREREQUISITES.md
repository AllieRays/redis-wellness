# Prerequisites

## 1. Overview

Before running the Redis Wellness demo, you need to install several tools and export your Apple Health data. This guide walks through all required setup steps for Docker, Ollama, and Apple Health data export.

### What You'll Learn

- **[System Requirements](#2-system-requirements)** - Hardware and software requirements
- **[Docker Installation](#3-docker-installation)** - Install and verify Docker Desktop
- **[Ollama Installation](#4-ollama-installation)** - Install Ollama and download required models
- **[Apple Health Data Export](#5-apple-health-data-export)** - Export health data from iPhone
- **[Verification & Next Steps](#6-verification--next-steps)** - Verify all prerequisites and continue to quickstart

---

## 2. System Requirements

| Component | Requirement |
|-----------|-------------|
| **Operating System** | macOS 12+ (recommended) or Linux |
| **RAM** | 8GB minimum, 16GB recommended |
| **Disk Space** | ~15GB free space |
| **Docker Images** | ~5GB |
| **Ollama Models** | ~5.5GB (Qwen 2.5 7B + embeddings) |
| **Apple Health Data** | 100-500MB (varies by user) |

**Estimated Setup Time**: 30-45 minutes

---

## 3. Docker Installation

Docker is required to run Redis, the backend API, and the frontend.

### macOS Installation

**Option A: Docker Desktop (Recommended)**

1. Download Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/)
2. Open the downloaded `.dmg` file and drag Docker to Applications
3. Launch Docker Desktop from Applications
4. Wait for Docker to start (whale icon in menu bar should be stable)

**Verify installation**:
```bash
docker --version
# Should show: Docker version 24.0.0 or higher

docker compose version
# Should show: Docker Compose version v2.20.0 or higher
```

**Option B: Homebrew**

```bash
# Install Docker via Homebrew
brew install --cask docker

# Launch Docker Desktop
open /Applications/Docker.app

# Wait for Docker to start, then verify
docker --version
```

### Linux Installation

**Ubuntu/Debian**:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (avoid sudo for docker commands)
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
docker compose version
```

**Troubleshooting**:
- If Docker won't start, check System Settings → Privacy & Security → Allow apps from identified developers
- Ensure virtualization is enabled in your system BIOS/UEFI

---

## 4. Ollama Installation

Ollama runs the Qwen 2.5 7B language model locally on your machine.

### macOS Installation

**Option A: Download Installer (Recommended)**

1. Visit [ollama.com/download](https://ollama.com/download)
2. Download the macOS installer
3. Open the downloaded file and follow installation prompts
4. Ollama will start automatically in the background

**Option B: Homebrew**

```bash
brew install ollama
```

### Linux Installation

```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### Verify Installation

```bash
# Check Ollama is running
curl http://localhost:11434
# Should return: "Ollama is running"

# Check Ollama version
ollama --version
# Should show: ollama version 0.1.0 or higher
```

### Pull Required Models

Download the Qwen 2.5 7B model and embeddings model (required for the demo):

```bash
# Pull Qwen 2.5 7B Instruct (main chat model - 4.7 GB)
ollama pull qwen2.5:7b

# Pull mxbai-embed-large (embeddings model - 669 MB)
ollama pull mxbai-embed-large
```

**This will take 5-15 minutes depending on your internet speed.**

### Verify Models

```bash
# List installed models
ollama list

# Should show:
# NAME                    SIZE
# qwen2.5:7b             4.7 GB
# mxbai-embed-large      669 MB
```

**Troubleshooting**:
- If `ollama serve` fails with port 11434 already in use, Ollama is already running (this is normal)
- On macOS, Ollama runs as a background service automatically
- To restart Ollama on macOS: quit from menu bar icon and relaunch
- On Linux, use: `sudo systemctl restart ollama`

---

## 5. Apple Health Data Export

Export your health data from your iPhone's Health app.

### Export Steps

1. **Open Health App** on your iPhone
2. **Tap your profile picture** in the top right corner
3. **Scroll down** and tap **"Export All Health Data"**
4. **Tap "Export"** to confirm
   - This will take 1-5 minutes depending on how much data you have
   - You'll see a progress indicator
5. **Choose share destination**:
   - **AirDrop to your Mac** (fastest)
   - **Save to Files** and then sync to your computer
   - **Email to yourself** (for smaller exports)

### Transfer to Project

Once you have the `export.zip` file on your computer:

```bash
# Navigate to the project root
cd /path/to/redis-wellness

# Create Apple Health export directory
mkdir -p apple_health_export

# Unzip your export (adjust path to your actual file location)
unzip ~/Downloads/export.zip -d apple_health_export/

# Verify the export.xml file exists
ls -lh apple_health_export/export.xml
```

**Expected structure**:
```
apple_health_export/
├── export.xml          # Main health data file (100-500 MB typical)
├── export_cda.xml      # Clinical documents (optional)
└── workout-routes/     # GPS workout routes (optional)
```

### Privacy Note

- Your health data **never leaves your machine**
- All processing happens locally via Docker + Ollama
- No data is sent to external APIs or cloud services
- The export file contains sensitive health information - keep it secure

### Troubleshooting Export

**Export button disabled**:
- Make sure you have health data recorded
- Check Storage: Settings → General → iPhone Storage → Health (needs space for export)
- Try restarting the Health app

**Export fails or hangs**:
- Your device may have too much data to export at once
- Try exporting smaller date ranges using third-party apps
- Ensure your iPhone has sufficient battery/power

**Can't find export.xml**:
- The export creates a `.zip` file - you must unzip it first
- The main file is named `export.xml` (not `export_cda.xml`)

**No Apple Health data**:
- For demo purposes, you can use sample data (see 01_QUICKSTART.md)
- Or record a few days of data before exporting

---

## 6. Verification & Next Steps

### Verify Prerequisites

Run these commands to verify all prerequisites are met:

```bash
# Check Docker
docker --version && docker compose version

# Check Ollama
curl http://localhost:11434

# Check Ollama models
ollama list | grep -E "qwen2.5:7b|mxbai-embed-large"

# Check Apple Health export
ls apple_health_export/export.xml
```

**All checks should pass** before proceeding to 01_QUICKSTART.md.

### Expected Output

```
✅ Docker version 24.0.0, build 1a79695
✅ Docker Compose version v2.20.0
✅ Ollama is running
✅ qwen2.5:7b                4.7 GB
✅ mxbai-embed-large         669 MB
✅ apple_health_export/export.xml exists
```

### Quick Reference Commands

**Start Ollama (if not running):**

**macOS**:
```bash
# Ollama usually runs automatically
# If not, launch from Applications or:
open /Applications/Ollama.app
```

**Linux**:
```bash
# Start Ollama service
sudo systemctl start ollama

# Or run in terminal
ollama serve
```

**Check Ollama Status:**

```bash
# Test Ollama API
curl http://localhost:11434

# List available models
ollama list

# Test model inference
ollama run qwen2.5:7b "Hello, how are you?"
```

**Docker Troubleshooting:**

**Docker daemon not running**:
```bash
# macOS: Launch Docker Desktop
open /Applications/Docker.app

# Linux: Start Docker service
sudo systemctl start docker
```

**Permission denied errors (Linux)**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in for changes to take effect
```

### Optional Tools

These tools are helpful but not required:

**RedisInsight (Redis GUI):**

RedisInsight is automatically included in `docker-compose.yml` and accessible at [http://localhost:8001](http://localhost:8001) once the project is running.

**Make (for convenient commands):**

**macOS**: Already installed

**Linux**:
```bash
sudo apt-get install make  # Ubuntu/Debian
sudo yum install make      # RHEL/CentOS
```

With Make installed, you can use shortcuts like:
```bash
make dev      # Start development servers
make import   # Import Apple Health data
make health   # Check all services
```

See the `Makefile` in the project root for all available commands.

### Next Steps

Once all prerequisites are installed and verified:

| Prerequisite | Status |
|--------------|--------|
| Docker installed and running | ✅ |
| Ollama installed with Qwen 2.5 7B and mxbai-embed-large | ✅ |
| Apple Health data exported to `apple_health_export/export.xml` | ✅ |

**→ Continue to [01_QUICKSTART.md](01_QUICKSTART.md)** to start the application and import your health data.

### Getting Help

**Docker Issues:**
- [Docker Desktop Documentation](https://docs.docker.com/desktop/)
- [Docker Installation Guide](https://docs.docker.com/engine/install/)

**Ollama Issues:**
- [Ollama Documentation](https://github.com/ollama/ollama)
- [Ollama FAQ](https://github.com/ollama/ollama/blob/main/docs/faq.md)

**Apple Health Export:**
- [Apple Health Export Guide](https://support.apple.com/en-us/HT203037)

**Project-Specific Issues:**
- Check [01_QUICKSTART.md](01_QUICKSTART.md) for common setup issues
- Review logs: `docker compose logs`

---

## Related Documentation

- **[01_QUICKSTART.md](01_QUICKSTART.md)** - Quick start guide to run the application
- **[02_THE_DEMO.md](02_THE_DEMO.md)** - Understanding the side-by-side demo
- **[07_APPLE_HEALTH_DATA.md](07_APPLE_HEALTH_DATA.md)** - Apple Health data pipeline details

---

**Key takeaway:** Install Docker and Ollama, download the Qwen 2.5 7B and embedding models, export your Apple Health data, and you're ready to run the Redis Wellness demo locally.
