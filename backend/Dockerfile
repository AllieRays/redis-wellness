FROM python:3.11-slim

WORKDIR /app

# Install git (needed for git dependencies) and uv for faster dependency management
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (production only)
ENV UV_HTTP_TIMEOUT=120
RUN uv sync --frozen --no-dev

# Copy application code and validation scripts
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY docker-entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Validate critical imports and Redis checkpointer at build time
RUN uv run python scripts/validate_imports.py || exit 1

# Expose port
EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"]

# Run the application
CMD ["uv", "run", "python", "-m", "src.main"]
