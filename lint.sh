#!/bin/bash
set -e

echo "🧹 Running linters for Redis Wellness App..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Backend linting
echo -e "\n${YELLOW}Backend (Python)${NC}"
cd backend

print_status "Running Ruff (linter)..."
if ! uv run ruff check src ../tests; then
    print_error "Ruff linting failed"
    exit 1
fi

print_status "Running Ruff (formatter check)..."
if ! uv run ruff format --check src ../tests; then
    print_error "Ruff formatting check failed. Run 'uv run ruff format src ../tests' to fix."
    exit 1
fi

print_status "Running Black (formatter check)..."
if ! uv run black --check src ../tests; then
    print_error "Black formatting check failed. Run 'uv run black src ../tests' to fix."
    exit 1
fi

cd ..

# Frontend linting
echo -e "\n${YELLOW}Frontend (TypeScript)${NC}"
cd frontend

print_status "Running TypeScript compiler check..."
if ! npm run typecheck; then
    print_error "TypeScript compilation failed"
    exit 1
fi

print_status "Running ESLint..."
if ! npm run lint:check; then
    print_error "ESLint failed. Run 'npm run lint' to fix auto-fixable issues."
    exit 1
fi

print_status "Running Prettier check..."
if ! npm run format:check; then
    print_error "Prettier formatting check failed. Run 'npm run format' to fix."
    exit 1
fi

cd ..

echo -e "\n${GREEN}🎉 All linting checks passed!${NC}"
