.PHONY: help install dev test lint import clean redis-start redis-stop redis-clean fresh-start demo health verify stats

# Default target - show help
help:
	@echo "════════════════════════════════════════════════════════════════"
	@echo "  Redis Wellness - Makefile Commands"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📦 Setup & Installation:"
	@echo "  make install          Install all dependencies"
	@echo "  make dev              Start development servers"
	@echo "  make health           Check all services (Redis, API, Ollama)"
	@echo ""
	@echo "📊 Data Management:"
	@echo "  make import           Import Apple Health data"
	@echo "  make import-xml       Import from specific XML file"
	@echo "  make verify           Verify data is loaded and indexed"
	@echo "  make stats            Show health data types and statistics"
	@echo ""
	@echo "🧪 Testing & Quality:"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-e2e         Run E2E tests"
	@echo "  make lint             Run code linting"
	@echo ""
	@echo "🔴 Redis Operations:"
	@echo "  make redis-start      Start Redis container"
	@echo "  make redis-stop       Stop Redis container"
	@echo "  make redis-clean      Clean Redis data (FLUSHALL)"
	@echo "  make redis-keys       Show Redis keys"
	@echo ""
	@echo "🚀 Quick Commands:"
	@echo "  make fresh-start      Clean + Import + Dev (full reset)"
	@echo "  make demo             Prepare for demo (import + verify)"
	@echo "  make clean            Clean all build artifacts"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"

# Install dependencies
install:
	@echo "📦 Installing backend dependencies..."
	cd backend && uv sync
	@echo "✅ Dependencies installed"

# Start development servers
dev:
	@echo "🚀 Starting development servers..."
	@echo "📍 Frontend: http://localhost:3000"
	@echo "📍 Backend API: http://localhost:8000"
	@echo "📍 API Docs: http://localhost:8000/docs"
	@make redis-start
	@echo ""
	@echo "Starting backend server..."
	cd backend && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Import Apple Health data (auto-detect)
import:
	@echo "📱 Importing Apple Health data..."
	uv run --directory backend import-health ../apple_health_export/export.xml

# Import from specific XML file
import-xml:
	@echo "📱 Importing from XML file..."
	@read -p "Enter path to export.xml: " xml_path; \
	cd backend && uv run import-health "$$xml_path"

# Verify data is loaded and indexed
verify:
	@echo "🔍 Verifying Redis data..."
	uv run --directory backend wellness verify

# Health check all services
health:
	@echo "🏥 Checking system health..."
	uv run --directory backend wellness health

# Show health data statistics
stats:
	@echo "📊 Showing health data statistics..."
	uv run --directory backend wellness stats

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

# Fresh start - clean everything and reimport
fresh-start:
	@echo "🚀 Fresh start - resetting everything..."
	@make redis-start
	@echo "🔴 Cleaning Redis..."
	@docker compose exec -T redis redis-cli FLUSHALL
	@echo "📱 Importing health data..."
	@make import
	@echo "✅ Fresh start complete!"
	@echo ""
	@echo "Verify with: make redis-keys"

# Demo preparation
demo:
	@echo "🎬 Preparing for demo..."
	@make redis-start
	@echo ""
	@echo "📊 Current Redis status:"
	@make redis-keys
	@echo ""
	@read -p "Import fresh data? (y/N): " do_import; \
	if [ "$$do_import" = "y" ] || [ "$$do_import" = "Y" ]; then \
		docker compose exec -T redis redis-cli FLUSHALL; \
		make import; \
	fi
	@echo ""
	@echo "🧪 Running validation tests..."
	@cd backend/tests/e2e && ./test_data_validation.sh
	@echo ""
	@echo "✅ Demo ready!"
	@echo "Start servers with: make dev"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned"
