.PHONY: help install dev dev-docker up down logs test lint import import-docker clean redis-start redis-stop redis-clean fresh-start demo health verify stats clear-session rebuild

# Default target - show help
help:
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  Redis Wellness - Makefile Commands"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📦 Setup & Development:"
	@echo "  make install          Install all dependencies"
	@echo "  make up               Start all Docker containers"
	@echo "  make down             Stop all Docker containers"
	@echo "  make logs             View Docker logs (all services)"
	@echo "  make dev              Start backend locally (dev mode)"
	@echo "  make health           Check all services (Redis, API, Ollama)"
	@echo ""
	@echo "📊 Data Management:"
	@echo "  make import           Import data (Docker containers)"
	@echo "  make import-local     Import data (local dev mode)"
	@echo "  make verify           Verify data is loaded and indexed"
	@echo "  make stats            Show health data types and statistics"
	@echo ""
	@echo "🧪 Testing & Quality:"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make lint             Run code linting"
	@echo ""
	@echo "🔴 Redis Operations:"
	@echo "  make redis-start      Start Redis container only"
	@echo "  make redis-stop       Stop Redis container"
	@echo "  make redis-clean      Clean Redis data (FLUSHALL)"
	@echo "  make redis-keys       Show Redis keys"
	@echo "  make clear-session    Clear chat session (keep health data)"
	@echo ""
	@echo "🚀 Quick Commands:"
	@echo "  make rebuild          Rebuild Docker images (clear cache, keep data)"
	@echo "  make fresh-start      Clean + Import + Start (full reset)"
	@echo "  make demo             Prepare for demo (import + verify)"
	@echo "  make clean            Clean all build artifacts"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "💡 TIP: Use 'make up' for Docker, 'make dev' for local development"
	@echo "════════════════════════════════════════════════════════════════"

# Install dependencies
install:
	@echo "📦 Installing backend dependencies..."
	cd backend && uv sync
	@echo "✅ Dependencies installed"

# Start all Docker containers
up:
	@echo "🐳 Starting all Docker containers..."
	@echo "📍 Frontend: http://localhost:3000"
	@echo "📍 Backend API: http://localhost:8000"
	@echo "📍 API Docs: http://localhost:8000/docs"
	@echo "📍 RedisInsight: http://localhost:8001"
	@docker compose up -d
	@echo ""
	@echo "✅ All services started!"
	@echo "💡 View logs: make logs"
	@echo "💡 Import data: make import"

# Stop all Docker containers
down:
	@echo "🐳 Stopping all Docker containers..."
	@docker compose down
	@echo "✅ All services stopped"

# View Docker logs
logs:
	@docker compose logs -f

# Start backend locally (for development)
dev:
	@echo "🚀 Starting backend locally (dev mode)..."
	@echo "⚠️  Make sure Redis is running: make redis-start"
	@echo "📍 Backend API: http://localhost:8000"
	@echo "📍 API Docs: http://localhost:8000/docs"
	@echo ""
	@make redis-start
	@sleep 2
	@echo "Starting backend server..."
	cd backend && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Import data into Docker Redis (for Docker setup)
import:
	@echo "📱 Importing Apple Health data into Docker Redis..."
	@echo "🐳 Running import inside backend container..."
	@docker compose exec backend uv run import-health /apple_health_export/export.xml
	@echo "✅ Import complete! Data is now in Docker Redis."
	@echo "💡 Verify: make verify"

# Import data into localhost Redis (for local dev)
import-local:
	@echo "📱 Importing Apple Health data (local mode)..."
	@echo "⚠️  This imports to localhost:6379 (for local dev)"
	uv run --directory backend import-health apple_health_export/export.xml
	@echo "✅ Import complete!"

# Import from specific XML file (Docker)
import-xml:
	@echo "📱 Importing from XML file (Docker)..."
	@read -p "Enter path to export.xml (inside container): " xml_path; \
	docker compose exec backend uv run import-health "$$xml_path"

# Verify data is loaded and indexed
verify:
	@echo "🔍 Verifying Redis data (Docker)..."
	@docker compose exec backend uv run wellness verify

# Health check all services
health:
	@echo "🏥 Checking system health (Docker)..."
	@docker compose exec backend uv run wellness health

# Show health data statistics
stats:
	@echo "📊 Showing health data statistics (Docker)..."
	@docker compose exec backend uv run wellness stats

# Run all tests
test:
	@echo "🧪 Running all tests..."
	cd backend && uv run pytest tests/ -v

# Run unit tests only
test-unit:
	@echo "🧪 Running unit tests..."
	cd backend && uv run pytest tests/unit/ -v -m unit

# Run E2E tests
test-e2e:
	@echo "🧪 Running E2E tests..."
	cd backend/tests/e2e && ./test_data_validation.sh
	cd backend/tests/e2e && ./test_hallucinations.sh

# Run linting
lint:
	@echo "🔍 Running linter..."
	cd backend && uv run ruff check src/ tests/
	@echo "✅ Linting complete"

# Start Redis
redis-start:
	@echo "🔴 Starting Redis..."
	@docker compose up -d redis
	@echo "⏳ Waiting for Redis to be ready..."
	@sleep 2
	@docker compose exec -T redis redis-cli PING > /dev/null && echo "✅ Redis is ready" || echo "❌ Redis failed to start"

# Stop Redis
redis-stop:
	@echo "🔴 Stopping Redis..."
	docker compose stop redis
	@echo "✅ Redis stopped"

# Clean Redis data (FLUSHALL)
redis-clean:
	@echo "🔴 Cleaning Redis data..."
	@echo "⚠️  This will delete ALL data in Redis!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker compose exec -T redis redis-cli FLUSHALL && echo "✅ Redis data cleared"; \
	else \
		echo "❌ Cancelled"; \
	fi

# Show Redis keys (for debugging)
redis-keys:
	@echo "🔴 Redis keys:"
	@docker compose exec -T redis redis-cli KEYS "*" | head -20
	@echo ""
	@echo "Total keys:"
	@docker compose exec -T redis redis-cli DBSIZE

# Clear chat session (keeps health data intact)
clear-session:
	@echo "🧹 Clearing chat session..."
	@docker compose exec -T redis redis-cli DEL "user:wellness_user:session:default" "langgraph:checkpoints:default" && echo "✅ Session cleared" || echo "⚠️  Session may not exist"
	@echo "🧠 Clearing episodic memory (goals)..."
	@docker compose exec -T redis redis-cli --scan --pattern "episodic:*" | xargs -r docker compose exec -T redis redis-cli DEL && echo "✅ Episodic memory cleared" || echo "⚠️  No episodic memory found"
	@echo "📋 Note: Health data preserved"

# Fresh start - clean everything and reimport
fresh-start:
	@echo "🚀 Fresh start - resetting everything..."
	@echo "🐳 Starting containers..."
	@docker compose up -d
	@sleep 3
	@echo "🔴 Cleaning Redis..."
	@docker compose exec -T redis redis-cli FLUSHALL
	@echo "📱 Importing health data..."
	@make import
	@echo "✅ Fresh start complete!"
	@echo ""
	@echo "Verify with: make redis-keys"
	@echo "View logs: make logs"


# Rebuild Docker images (clear cache, keep Redis data)
rebuild:
	@echo "🔨 Rebuilding Docker images with cache clearing..."
	@echo "📋 Note: Redis data will be preserved"
	@docker compose build --no-cache
	@docker compose up -d
	@echo "✅ Rebuild complete!"
	@echo "💡 View logs: make logs"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned"
