# Code Quality

This document outlines code quality standards, tools, and practices for Redis Wellness.

## Table of Contents
- [Overview](#overview)
- [Code Style](#code-style)
- [Linting](#linting)
- [Type Checking](#type-checking)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Code Review Guidelines](#code-review-guidelines)

---

## Overview

Redis Wellness maintains production-grade code quality through:
- **Static analysis**: Ruff for linting, type checking with Python 3.11+ type hints
- **Formatting**: Automatic code formatting with Ruff
- **Standards**: PEP 8 compliance with project-specific conventions
- **Automation**: Pre-commit hooks for consistent quality
- **Documentation**: Google-style docstrings throughout

---

## Code Style

### Python Backend

**Style Guide**: PEP 8 with project modifications:
- **Line length**: 88 characters (Black/Ruff default)
- **Quotes**: Double quotes for strings
- **Imports**: Organized by standard library → third-party → local
- **Type hints**: Required for all function signatures (90%+ coverage achieved)

**Docstring Format**: Google-style docstrings

```python
def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """
    Calculate Body Mass Index from weight and height.

    Args:
        weight_kg: Weight in kilograms
        height_m: Height in meters

    Returns:
        BMI value rounded to 2 decimal places

    Raises:
        ValueError: If weight or height is non-positive
    """
    if weight_kg <= 0 or height_m <= 0:
        raise ValueError("Weight and height must be positive")
    return round(weight_kg / (height_m ** 2), 2)
```

### TypeScript Frontend

**Style Guide**: Standard TypeScript conventions
- **Line length**: 100 characters
- **Quotes**: Double quotes for strings
- **Semicolons**: Always required
- **Type annotations**: Explicit types preferred over inference

**ESLint Configuration**: `frontend/.eslintrc.js`
**Prettier Configuration**: `frontend/.prettierrc`

---

## Linting

### Backend (Python)

**Tool**: [Ruff](https://github.com/astral-sh/ruff) - Extremely fast Python linter

**Configuration**: `backend/pyproject.toml`

```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "B",   # flake8-bugbear
    "I",   # isort
    "UP",  # pyupgrade
]
```

**Run Linting**:
```bash
cd backend

# Check all files
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check --fix src/ tests/

# Check specific file
uv run ruff check src/agents/stateful_rag_agent.py
```

**Common Issues**:
- **B904**: Exception chaining - Always use `raise ... from e`
- **F401**: Unused imports - Remove or add `# noqa: F401` for `__init__.py`
- **E501**: Line too long - Break into multiple lines
- **B008**: Function call in default argument - Use `default_factory` in Pydantic

### Frontend (TypeScript)

**Tool**: ESLint + Prettier

**Run Linting**:
```bash
cd frontend

# Check TypeScript types
npm run typecheck

# Run ESLint
npm run lint

# Format code
npm run format
```

---

## Type Checking

### Python Type Hints

**Coverage**: 90%+ of codebase has complete type annotations

**Type Checking Strategy**:
- Function signatures: **Always typed**
- Complex data structures: Pydantic models
- Return types: Explicit (no implicit `None`)
- Generic types: Use `list[T]`, `dict[K, V]` (Python 3.11+ syntax)

**Example**:
```python
from typing import Any

def process_health_data(
    records: list[HealthRecord],
    filters: dict[str, Any],
    max_results: int = 100
) -> tuple[list[HealthRecord], int]:
    """Process and filter health records."""
    filtered = [r for r in records if matches_filters(r, filters)]
    return filtered[:max_results], len(filtered)
```

**Mypy Configuration** (optional):
```bash
# Add to pyproject.toml if using mypy
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### TypeScript Types

**Strategy**:
- All API responses: Typed interfaces
- React components: Props explicitly typed
- No `any` types (use `unknown` if needed)

**Example**:
```typescript
interface ChatRequest {
  message: string;
  session_id: string;
}

interface ChatResponse {
  response: string;
  session_id: string;
  tools_used: Array<{ name: string }>;
  memory_stats: Record<string, any>;
}
```

---

## Pre-commit Hooks

**Status**: Configured and documented (see Phase 4.3)

Pre-commit hooks run automatically before each commit to enforce quality standards.

**Installation**:
```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
cd /path/to/redis-wellness
pre-commit install
```

**What Gets Checked**:
- Python: Ruff linting + formatting
- TypeScript: ESLint + Prettier
- YAML/JSON: Syntax validation
- Trailing whitespace removal
- Large file detection

**Configuration**: `.pre-commit-config.yaml` (root directory)

**Manual Run**:
```bash
# Run on all files
pre-commit run --all-files

# Run on staged files
pre-commit run

# Skip hooks (emergency only)
git commit --no-verify
```

---

## Code Review Guidelines

### What to Check

**Correctness**:
- [ ] Logic is correct and handles edge cases
- [ ] Error handling is appropriate (try/except with logging)
- [ ] Tests cover new functionality

**Code Quality**:
- [ ] Type hints on all functions
- [ ] Docstrings for public APIs
- [ ] No magic numbers (use named constants)
- [ ] Functions < 50 lines (refactor if longer)

**Architecture**:
- [ ] Follows clean architecture layers (agents → services → utils)
- [ ] No circular dependencies
- [ ] Proper separation of concerns

**Performance**:
- [ ] No N+1 queries
- [ ] Caching used appropriately
- [ ] Redis operations are O(1) or O(log n)

**Security**:
- [ ] No secrets in code
- [ ] User input validated
- [ ] SQL injection safe (using parameterized queries)

### Anti-Patterns to Avoid

❌ **Don't**:
```python
# Magic numbers
ttl = 18144000  # What is this?

# No type hints
def process_data(data):
    return data['value']

# Overly long functions
def handle_request():
    # 150 lines of code...
```

✅ **Do**:
```python
# Named constants
SEVEN_MONTHS_TTL = 60 * 60 * 24 * 7 * 30  # 7 months in seconds

# Type hints
def process_data(data: dict[str, Any]) -> float:
    return float(data['value'])

# Small focused functions
def handle_request():
    validate_input()
    result = process_data()
    return format_response(result)
```

---

## Quick Reference

### Backend Commands
```bash
cd backend

# Lint + format
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/

# Run tests
uv run pytest tests/

# Type check (optional with mypy)
uv run mypy src/
```

### Frontend Commands
```bash
cd frontend

# Lint + format
npm run lint
npm run format
npm run typecheck

# Run dev server
npm run dev
```

### Quality Checklist

Before committing:
- [ ] All linting passes (`ruff check`)
- [ ] Code is formatted (`ruff format`)
- [ ] Tests pass (`pytest`)
- [ ] Type hints added to new functions
- [ ] Docstrings added to public APIs
- [ ] No `print()` statements (use `logger`)
- [ ] Constants extracted from magic numbers

---

## Related Documentation

- [06_DEVELOPMENT.md](06_DEVELOPMENT.md) - Development workflow and setup
- [07_TESTING.md](07_TESTING.md) - Testing strategy and anti-hallucination
- [03_ARCHITECTURE.md](03_ARCHITECTURE.md) - System architecture and patterns

---

**Last Updated**: October 2025 (Phase 2 improvements)
