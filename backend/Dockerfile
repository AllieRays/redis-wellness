FROM python:3.11-slim

WORKDIR /app

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (production only)
ENV UV_HTTP_TIMEOUT=120
RUN uv sync --frozen --no-dev

# Copy application code and validation scripts
COPY src/ ./src/
COPY scripts/ ./scripts/

# Validate critical imports and Redis checkpointer at build time
RUN uv run python scripts/validate_imports.py || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "python", "-m", "src.main"]
