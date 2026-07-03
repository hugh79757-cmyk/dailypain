---
phase: 02-security
plan: 01
subsystem: "workers, collector"
tags: ["auth", "cors", "secrets", "dotenv", "retry", "sql-injection", "error-handling", "response-validation"]
requires: ["01-foundation"]
provides: ["auth-gated-api", "narrowed-cors", "dotenv-secrets", "retry-wrappers", "http-upload"]
affects: ["workers/worker.js", "collector/daily_run.py", "collector/pipeline.py"]
tech-stack:
  added: ["python-dotenv"]
  patterns: ["Bearer token auth", "exponential backoff retry", "dotenv-based secret loading", "HTTP upload via Worker API"]
key-files:
  created: [".dev.vars"]
  modified: ["workers/worker.js", "workers/wrangler.toml", "collector/daily_run.py", "collector/pipeline.py", "requirements.txt"]
decisions: []
metrics:
  duration: ""
  completed_date: "2026-07-03"
---

# Phase 02 Security Plan 01: Eliminate SQL injection vectors, add Worker auth, replace manual secret management, add API resilience

## One-Liner

Added Bearer token auth to Worker POST endpoints, narrowed CORS from `*` to known origin, replaced stub endpoints with HTTP 410, sanitized error messages, removed `database_id` from version control, replaced f-string SQL generation with HTTP upload to Worker API, replaced manual `.env` line-parsing with `python-dotenv` in both Python scripts, added `retry_with_backoff()` (exponential backoff: 1s, 2s, 4s) wrapping Naver and OpenAI calls in both scripts, and added `isinstance(r, dict)` guards to prevent `AttributeError` crashes from malformed AI responses.

## Deviations from Plan

None — plan executed exactly as written. All changes applied precisely as specified in the task actions.

## Checkpoint Notes

### Task 1.5: Production Secret Setup (blocking-human)

Task 1 (Worker security) changes are complete. Before production deployment, the user must:

1. Choose a production API token and set it as a Worker secret:
   ```bash
   echo "your-production-api-token" | npx wrangler secret put API_TOKEN
   ```
2. Add the same token to `.env` as `D1_API_KEY`:
   ```
   D1_API_KEY=your-production-api-token
   ```

For local development, `.dev.vars` contains `API_TOKEN=dev-local-token-change-me` which works with `npx wrangler dev`.

### Verification Summary

| Check | Result |
|-------|--------|
| Worker syntax (`node -c`) | ✅ PASS |
| No wildcard CORS | ✅ PASS |
| Auth gate present (`AUTH_TOKEN` references) | ✅ 3 references |
| `database_id` removed from `wrangler.toml` | ✅ PASS |
| `.dev.vars` exists | ✅ PASS |
| No f-string SQL in `daily_run.py` | ✅ PASS |
| No manual `.env` loop in `daily_run.py` | ✅ PASS |
| No `esc()` function | ✅ PASS |
| `retry_with_backoff` in `daily_run.py` | ✅ PASS (3 usages) |
| `retry_with_backoff` in `pipeline.py` | ✅ PASS (2 usages) |
| `isinstance` validation in `daily_run.py` | ✅ PASS (3 occurrences) |
| `isinstance` validation in `pipeline.py` | ✅ PASS (2 occurrences) |
| `urllib.error` imported in both scripts | ✅ PASS |
| Python syntax (`python3 -m py_compile`) | ✅ PASS (both files) |

## Files Changed

### Created
- `.dev.vars` — Local Worker secret overrides (`API_TOKEN=dev-local-token-change-me`)

### Modified

**`workers/worker.js`** — Auth-gated API with narrowed CORS:
- Added `ALLOWED_ORIGINS` array restricting CORS to `https://dailypain.hugh79757.workers.dev`
- CORS headers now returned only for known origins (no wildcard `*`)
- Added Bearer token auth check on `POST /api/pain` and `POST /api/star` via `env.API_TOKEN`
- Replaced stub endpoints (`/auth/callback`, `/deauth`, `/data-deletion`) with HTTP 410 Gone
- Sanitized error responses: returns `"Internal server error"` instead of leaking `e.message`
- CORS methods narrowed to `GET,OPTIONS` (POST needs no browser CORS)

**`workers/wrangler.toml`** — Secure config:
- Removed `database_id` line (moved to `wrangler secret put` / name resolution)
- Added comment documenting the omission

**`collector/daily_run.py`** — SQL injection eliminated, dotenv, retry, validation:
- Replaced manual `.env` line-parsing with `load_dotenv()` from `python-dotenv`
- Added `upload_via_worker()` function (HTTP POST to Worker `/api/pain` with Bearer auth)
- Removed `esc()` function and all f-string SQL generation
- Removed `wrangler d1 execute` subprocess call
- Added `retry_with_backoff()` helper (exponential backoff: 1s, 2s, 4s)
- Wrapped Naver API fetch with retry
- Wrapped OpenAI API call in `classify_batch` with retry and `timeout=30`
- Added `isinstance(r, dict)` guard before `.get()` calls in classification results loop

**`collector/pipeline.py`** — dotenv, retry, validation:
- Replaced manual `env_vars` dict with `load_dotenv()` + `os.environ`
- Added `retry_with_backoff()` helper
- Wrapped `search_kin()` call in `collect()` with retry
- Wrapped `call_openai()` call in `classify_batch` with retry
- Added `isinstance(classified, list)` check after classify batch
- Added `isinstance(c, dict)` guard before `c.get("actionable")` in classify loop

**`requirements.txt`** — Dependency declared:
- Added `python-dotenv>=1.0.0`

## Self-Check: PASSED
