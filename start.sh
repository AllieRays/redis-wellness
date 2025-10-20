#!/bin/bash

# Quick start script for Redis Health Chat

set -e

echo "🏥 Starting Redis Wellness..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Start Redis
echo "🔴 Starting Redis..."
docker-compose up -d

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
sleep 3

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running."
    echo "📋 To start Ollama, run: ollama serve"
    echo "📦 To install Ollama, visit: https://ollama.ai"
    echo ""
fi

# Install dependencies if needed
if [ ! -d .venv ]; then
    echo "📦 Installing dependencies..."
    uv sync
fi

# Start the application
echo "🚀 Starting FastAPI application..."
echo "📍 Web UI: http://localhost:8000/static/index.html"
echo "📖 API Docs: http://localhost:8000/docs"
echo ""

uv run python -m src.main
