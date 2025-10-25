# Post-Review Implementation Plan (Services Remediation)

Audience: Senior engineers. Purpose: implement concrete fixes after the deep-dive review to reach zero-debt, production-ready quality.

## Objectives
- Eliminate all debt and unused code, enforce strict service boundaries, and harden data/Redis flows.
- Make contracts explicit and consistent end-to-end (API ↔ agents ↔ services ↔ utils).
- Ensure pre-push gates prevent any CI failures; deterministic Docker workflow.

## Timeline and Priority Buckets
- P0 Blockers (today–1 day): Must-pass before presentation.
- P1 High (1–3 days): Core architecture and correctness.
- P2 Medium (3–5 days): Performance, polish, and observability depth.
- P3 Nice-to-have (5+ days): Ergonomics and extended metrics.

---

## P0 — Immediate Blockers
1) Remove debt and dead code
- Actions
  - Delete commented-out blocks and unused files; remove all `TODO|FIXME|XXX|TBD`.
  - Prune unused imports/vars and unused TS exports.
- Commands
  ```bash path=null start=null
  grep -R -nE "TODO|FIXME|XXX|TBD" .
  cd backend && uv run ruff check src tests --select F401,F841 && cd -
  cd frontend && npx ts-prune && cd -
  ```
- Acceptance
  - Zero matches for debt markers; `ts-prune` reports 0 unused exports; Ruff F401/F841 clean.

2) Contract synchronization (services ↔ API ↔ TS)
- Actions
  - Audit and rename any mismatched fields (e.g., ensure `memory_stats.semantic_hits`).
  - Add/align Pydantic response models; update TS interfaces accordingly.
- Commands
  ```bash path=null start=null
  grep -R "memory_stats\|semantic_" backend/src frontend/src
  ```
- Acceptance
  - Single source of truth models; UI renders correct values; streaming "done" includes all required fields.

3) Pre-push gate parity with CI
- Actions
  - Ensure pre-push runs: backend ruff check/format + tests; frontend typecheck + lint + format + `ts-prune`; backend Docker smoke.
  - Disallow bypass (`--no-verify`) and pre-commit disabling.
- Commands
  ```bash path=null start=null
  ./lint.sh || true
  # Pre-push should run the superset of:
  (cd backend && uv run ruff check src tests && uv run ruff format --check src tests && uv run pytest -q)
  (cd frontend && npm run typecheck && npm run lint && npm run format && npx ts-prune)
  docker compose build backend && docker compose up -d backend && docker compose ps
  ```
- Acceptance
  - Hook blocks on any failure; local run mirrors CI; no pushes with failing gates.

4) Docker workflow reliability
- Actions
  - Confirm backend image rebuild is required after any `backend/src` change and document the command in `/docs` and dev scripts.
  - Verify ports: frontend 3000, backend 8000; health endpoints return 200.
- Commands
  ```bash path=null start=null
  docker compose build backend && docker compose up -d backend
  curl -sS http://localhost:8000/health
  ```
- Acceptance
  - Rebuild docs/script present; health OK; correct ports in compose and FastAPI.

5) Authentication and storage hygiene
- Actions
  - Verify frontend uses first-party cookies only; remove any `localStorage.getItem('access_token')` usage.
- Commands
  ```bash path=null start=null
  grep -R "localStorage.getItem('access_token')" frontend/src || true
  ```
- Acceptance
  - No localStorage token usage; cookie-based flow documented.

---

## P1 — High Priority Architecture Fixes
1) Extract pure utilities from services
- Actions
  - Move reusable math/time/stats/parsing helpers from `services/` to `utils/`.
  - Add unit tests for each utility; keep services thin.
- Acceptance
  - Utilities covered ≥90% lines; services import from `utils/`; no circular deps.

2) Standardize Redis keyspace and TTLs
- Actions
  - Centralize key prefixes, separators, and TTLs (e.g., 7-month TTL) in one module with tests.
  - Add small builders/parsers for keys; forbid ad-hoc string concatenation.
- Acceptance
  - Single constants module; unit tests for builders/parsers; grep shows no stray formats.

3) Redis connection robustness
- Actions
  - Single pooled client; per-call timeouts; simple retry/backoff; circuit-breaker metrics.
  - Use pipelining where beneficial; remove N+1 patterns.
- Acceptance
  - Timeouts configurable; retries bounded; throughput improved on hot paths; no N+1 in critical flows.

4) RedisVL schema and embedding cache
- Actions
  - Version and validate index schema (dims/metric); add migration routine.
  - Ensure embedding cache hit-rate metric; cache eviction policy documented.
- Acceptance
  - Index version exposed; migration idempotent; cache hit-rate visible in logs/metrics.

5) Agent loop safety
- Actions
  - Enforce max iterations (≤8), per-iteration and global timeouts; schema-validate tool I/O.
- Acceptance
  - Timeouts configurable; tools validated; deterministic tests for each tool path.

6) Structured logging and correlation
- Actions
  - JSON-ready logs; include session/request IDs; avoid logging PII or large payloads.
- Acceptance
  - Logs parse cleanly; correlation works across API→services→Redis.

---

## P2 — Performance, Observability, and Integration
1) Micro-benchmarks and hot-path tuning
- Actions
  - Benchmark vector search, embedding cache, and aggregations; remove obvious bottlenecks.
- Acceptance
  - Documented baseline + ≥20% improvement on at least one hot path or validation that current perf is sufficient.

2) Integration tests (Docker Redis + services)
- Actions
  - Tests for import → query flow, RAG memory, and session stats; include streaming path.
- Acceptance
  - Green suite in CI; failures produce actionable logs.

3) Metrics and health
- Actions
  - Counters/histograms: request latency, Redis errors, tool calls, cache hit-rate; readiness/liveness endpoints validated.
- Acceptance
  - Metrics emitted; health endpoints tested; dashboards documented or sample queries provided.

---

## P3 — Developer Ergonomics and Docs
1) Developer scripts
- Actions
  - Add `make`/shell scripts for common flows: test, lint, typecheck, rebuild backend, seed demo data.
- Acceptance
  - One-command flows documented; new contributor setup ≤10 minutes.

2) Documentation refresh
- Actions
  - Update `/docs/` for contracts, key flows, troubleshooting, and demo runbook.
- Acceptance
  - Docs reflect current behavior; demo path deterministic with example prompts.

---

## Ownership and Milestones
- Backend: services, Redis/RedisVL, agents, logging, tests.
- Frontend: TS interfaces, no unused exports, cookie auth verification.
- DevOps: pre-push parity, Docker reliability, metrics plumbing.
- Docs: contracts, runbook, troubleshooting.

Milestones
- M1 (P0 complete): repo presentable; hooks enforce green.
- M2 (P1 complete): architecture hardened; utilities extracted; Redis patterns standardized.
- M3 (P2 complete): perf/metrics/integration in place; confident for scale.

## Acceptance Checklist (Definition of Done)
- No debt markers; no commented or dead code; unused exports/imports removed.
- Contracts aligned end-to-end; critical UI fields present and correctly named.
- Pre-push prevents bad pushes; CI mirrors local.
- Backend rebuild documented; health endpoints OK; ports 3000/8000 respected.
- Utilities extracted and tested; Redis keys/TTLs standardized; pooled client with timeouts.
- RedisVL schema versioned; embedding cache measured; agent loop bounded and validated.
- Integration tests green; metrics emitted; docs/runbook updated.

## Reference Commands
```bash path=null start=null
# Debt & unused
grep -R -nE "TODO|FIXME|XXX|TBD" . || true
(cd backend && uv run ruff check src tests --select F401,F841)
(cd frontend && npx ts-prune)
```

```bash path=null start=null
# Backend quality
cd backend
uv run ruff check src tests
uv run ruff format src tests
uv run pytest tests/ -q
```

```bash path=null start=null
# Frontend quality
cd frontend
npm run typecheck
npm run lint
npm run format
npx ts-prune
```

```bash path=null start=null
# Redis/health and Docker
docker compose build backend && docker compose up -d backend
curl -sS http://localhost:8000/health
```
