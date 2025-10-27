# Code Linting Setup

This project uses comprehensive linting and formatting tools for both Python backend and TypeScript frontend code.

## Quick Start

```bash
# Run all linting checks
./lint.sh

# Auto-fix issues where possible
cd backend && uv run ruff check --fix src ../tests && uv run ruff format src ../tests
cd frontend && npm run lint && npm run format
```

## Python Backend (Ruff + Black)

### Tools Used
- **Ruff**: Fast Python linter and formatter
- **Black**: Code formatter for consistent style
- **pre-commit**: Git hooks for automatic linting

### Commands
```bash
cd backend

# Check code with Ruff
uv run ruff check src ../tests

# Auto-fix Ruff issues
uv run ruff check --fix src ../tests

# Format code with Ruff
uv run ruff format src ../tests

# Check Black formatting
uv run black --check src ../tests

# Apply Black formatting
uv run black src ../tests
```

### Configuration
- `pyproject.toml` - Main Ruff and Black configuration
- Line length: 88 characters
- Python 3.11+ target version
- Import sorting with isort integration

## TypeScript Frontend (ESLint + Prettier)

### Tools Used
- **ESLint**: JavaScript/TypeScript linting
- **@typescript-eslint**: TypeScript-specific rules
- **Prettier**: Code formatting

### Commands
```bash
cd frontend

# Check TypeScript compilation
npm run typecheck

# Lint code (with auto-fix)
npm run lint

# Check linting only (no fixes)
npm run lint:check

# Format code with Prettier
npm run format

# Check Prettier formatting
npm run format:check
```

### Configuration
- `.eslintrc.json` - ESLint rules and TypeScript parser
- `.prettierrc` - Prettier formatting options
- Print width: 88 characters (matches Python)
- Single quotes, semicolons, trailing commas

## Pre-commit Hooks

Pre-commit hooks run automatically on `git commit` and include:

### Python
- Ruff linting and formatting
- Black formatting
- Import sorting

### TypeScript
- ESLint checking with auto-fix
- Prettier formatting

### General
- Trailing whitespace removal
- End-of-file newline fixes
- YAML/JSON validation
- Merge conflict detection
- Large file prevention

### Setup
```bash
# Install hooks (already done)
cd backend && uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files

# Skip hooks (only if absolutely necessary)
git commit --no-verify
```

## IDE Integration

### VS Code
Install these extensions for automatic linting:
- Python: ms-python.python
- Ruff: charliermarsh.ruff
- ESLint: dbaeumer.vscode-eslint
- Prettier: esbenp.prettier-vscode

### Settings
Add to `.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```

## Troubleshooting

### Common Issues

**Ruff configuration errors**: Make sure `pyproject.toml` has proper `[tool.ruff.lint]` sections

**ESLint TypeScript errors**: Verify `tsconfig.json` exists in frontend directory

**Pre-commit failures**: Run `uv run pre-commit run --all-files` to see specific errors

**Import sorting conflicts**: Ruff handles import sorting - avoid using isort separately

### Bypassing Rules

Only bypass linting when absolutely necessary:

```bash
# Skip pre-commit hooks (discouraged)
git commit --no-verify

# Disable specific ESLint rules
// eslint-disable-next-line @typescript-eslint/no-explicit-any

# Ignore Ruff rules for specific lines
# ruff: noqa: E501
```

## Continuous Integration

The linting setup integrates with your pre-push git hooks to prevent pushing code that fails linting checks. This ensures code quality is maintained across the entire team.
