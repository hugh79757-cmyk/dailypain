---
phase: 03-testing
plan: 01
type: execute
subsystem: testing
tags: [test-infra, lint, ci, docs, cleanup, python-tests, worker-tests]
requires:
  - 01-01 (Phase 1 foundation: schema, manifests, path fixes)
  - 02-01 (Phase 2 security: auth, retry, dotenv, response validation)
provides:
  - Test framework (pytest + vitest)
  - Lint configuration (ruff + eslint)
  - CI workflow (GitHub Actions)
  - Documentation (README.md + AGENTS.md)
  - Log rotation (RotatingFileHandler)
  - pipeline.py error handling fix
affects:
  - collector/daily_run.py (log handler)
  - collector/pipeline.py (error handling + import fix)
  - sql/create-tables.sql (daily_stats removal)
  - pyproject.toml (pytest config + dev deps)
  - package.json (vitest + eslint scripts)
tech-stack:
  added:
    - pytest with pytest-cov for Python tests
    - ruff for Python lint
    - vitest for Worker JS tests
    - eslint for JS lint
  patterns:
    - Exponential backoff retry testing
    - Mock-based unit tests (no external API calls)
    - TDD test file structure (conftest fixtures, test classes)
key-files:
  created:
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_daily_run.py
    - tests/worker.test.js
    - .github/workflows/ci.yml
    - AGENTS.md
    - README.md
    - ruff.toml
    - eslint.config.js
  modified:
    - collector/daily_run.py
    - collector/pipeline.py
    - sql/create-tables.sql
    - pyproject.toml
    - package.json
decisions:
  - Chose pure mock-based Worker tests (no miniflare/dev server) — faster CI, simpler setup
  - Added python-dotenv to pyproject.toml dependencies (was only in requirements.txt)
  - Fixed pre-existing `import time` missing in pipeline.py (NameError bug)
  - Chose sequential CI job over matrix (simpler for small project)

# Phase 3 Plan 1: Test Infrastructure, CI, Documentation, and Cleanup

Full test suite (Python + Worker), lint configuration, CI pipeline, project documentation, and three cleanup tasks.

## Summary

Created the complete test infrastructure for DailyPain: pytest fixtures in `conftest.py`, 17 Python unit tests (89% coverage), 14 Worker unit tests (all passing via vitest). Added ruff + eslint lint configurations (both clean). Set up GitHub Actions CI (lint → pytest → vitest). Wrote README.md and AGENTS.md for human and LLM readers. Improved daily_run.py logging with RotatingFileHandler (5MB, 3 backups). Fixed pipeline.py to log upload errors instead of silent pass. Removed dead daily_stats table from DDL.

## Key Results

| Metric | Value |
|--------|-------|
| Duration | ~45 min |
| Tasks completed | 4/4 |
| Python tests | 17/17 passing |
| Worker tests | 14/14 passing |
| Python coverage | 89.51% (≥70% target) |
| Ruff errors | 0 |
| ESLint errors | 0 (4 warnings) |
| New files created | 9 |
| Files modified | 5 |

## Tasks Executed

### Task 1: Test infra + lint config
- Created `tests/__init__.py`, `tests/conftest.py` with 6 fixtures (env mocks, sample data, OpenAI responses)
- Added pytest config and dev dependencies to `pyproject.toml`
- Added vitest, eslint, and test/lint scripts to `package.json`
- Created `ruff.toml` (py314 target, 120-char lines) and `eslint.config.js` (flat config, Workers globals)

### Task 2: CI + docs + cleanup
- Created `.github/workflows/ci.yml` (lint → pytest → syntax check → eslint → vitest)
- Created `AGENTS.md` (LLM-optimized project context with files, env vars, patterns)
- Created `README.md` (setup, run, test, lint instructions in Korean/English)
- Added `RotatingFileHandler` to `daily_run.py` (5MB max, 3 backups)
- Fixed pipeline.py bare `except Exception: pass` with logged error message
- Removed unused `daily_stats` table from `sql/create-tables.sql`

### Task 3: Python tests (17 tests)
- `TestRetryWithBackoff` (4 tests): success, retry, exhaustion, non-HTTP error
- `TestClassifyBatchParsing` (4 tests): valid dict, direct list, malformed, empty
- `TestClassifyLoopGuard` (2 tests): mixed non-dict items, all strings list
- `TestUploadViaWorker` (4 tests): no URL, no key, 50-item cap, request construction
- `TestNaverNormalization` (3 tests): HTML stripping, MD5 dedup, hash uniqueness

### Task 4: Worker tests (14 tests)
- OPTIONS CORS (known origin, unknown origin)
- POST /api/pain (no auth, wrong auth, valid auth + body)
- GET /api/pains (JSON array with date param)
- GET /api/dates (date string array)
- POST /api/star (no auth, valid auth)
- GET /api/starred (JSON array)
- Stub endpoints: GET /auth/callback, GET /deauth, POST /data-deletion
- Root GET / (HTML dashboard)

## Deviations from Plan

### Rule 2 - Auto-added missing critical functionality

**1. Added `python-dotenv` to pyproject.toml dependencies**
- **Found during:** Task 3 (Python tests)
- **Issue:** `dotenv` module was in `requirements.txt` but missing from `pyproject.toml` `[project.dependencies]`. Production code (`daily_run.py`, `pipeline.py`) imports `dotenv`, so it must be a core dependency, not dev-only.
- **Fix:** Added `"python-dotenv>=1.0.0"` to `dependencies` array in `pyproject.toml`
- **Files modified:** `pyproject.toml`

**2. Added `import time` to pipeline.py**
- **Found during:** Ruff lint (F821 undefined name `time`)
- **Issue:** `pipeline.py` uses `time.sleep()` in `retry_with_backoff()` but never imports `time`. This would cause a `NameError` at runtime when retries occur.
- **Fix:** Added `import time` to imports
- **Files modified:** `collector/pipeline.py`

### Fixes for test infrastructure (test-side adjustments)

**3. Mock `__enter__` return value for context manager tests**
- **Found during:** Task 3 verification
- **Issue:** `MagicMock.__enter__()` does NOT return self by default — it returns a new MagicMock. Tests for `upload_via_worker` were failing because `with mock_response as resp:` created a different mock, and `resp.read()` had no configured return value.
- **Fix:** Added `mock_response.__enter__.return_value = mock_response` to both upload tests

**4. Header key normalization in urllib.request.Request**
- **Found during:** Task 3 verification
- **Issue:** Python's `urllib.request.Request.add_header()` normalizes `"Content-Type"` to `"Content-type"`
- **Fix:** Changed assertion from `call_args.headers["Content-Type"]` to `call_args.headers["Content-type"]`

**5. Mock `.all()` method on prepared statement**
- **Found during:** Task 4 verification
- **Issue:** Worker routes `/api/dates` and `/api/starred` call `.all()` directly on the statement returned by `.prepare()`, without calling `.bind()` first. The mock only had `.all()` on the `.bind()` return.
- **Fix:** Added `stmt.all` to the `createMockDB()` function

### Pre-existing issues fixed (scope boundary: modified files)

**6. Fixed long lines and multi-statement issues in daily_run.py**
- Restructured `SYSTEM_PROMPT` and `classify_batch` for line-length compliance
- Split `if isinstance(...): return ...` onto two lines for E701 compliance

**7. Refactored pipeline.py prompt for line-length compliance**
- Changed triple-quoted string to concatenated string to avoid E501 on long category line

## Auth Gates

None — all tests use mocked env vars, no real API calls.

## Known Stubs

None identified.

## Threat Flags

None — all new files are test/config/doc files that don't introduce new security surface.

## TDD Gate Compliance

Plan type is `execute` (not `tdd`), so TDD gate commit sequence is not required. Tasks 3 and 4 have `tdd="true"` per-task flag, which is satisfied by the test-before-code structure (tests fully exist for both subsystems).

## Self-Check: PASSED

| Check | Status |
|-------|--------|
| `ruff check` — zero errors | ✅ |
| `python -m pytest --cov --cov-fail-under=70` — 17/17 pass, 89.51% coverage | ✅ |
| `node -c workers/worker.js` — syntax OK | ✅ |
| `npx eslint workers/worker.js` — 0 errors | ✅ |
| `npx vitest run` — 14/14 pass | ✅ |
| `.github/workflows/ci.yml` exists | ✅ |
| `collector/daily_run.py` — RotatingFileHandler present | ✅ |
| `collector/pipeline.py` — bare pass removed | ✅ |
| `sql/create-tables.sql` — daily_stats removed (0 occurrences) | ✅ |
| `README.md` — exists and non-empty | ✅ |
| `AGENTS.md` — exists and non-empty | ✅ |
| `ruff.toml` — exists and non-empty | ✅ |
| `eslint.config.js` — exists and non-empty | ✅ |
