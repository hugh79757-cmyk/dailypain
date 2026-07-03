# Testing Patterns

**Analysis Date:** 2026-07-03

## Test framework / tooling

- **No test framework is installed or configured.**
  - No `jest.config.*`, `vitest.config.*`, `pytest.ini`, `tox.ini`, `setup.cfg` with test config, `pyproject.toml`, or `Makefile` with test targets.
  - No testing dependencies in any package manifest (no `package.json`, `requirements.txt`, or `Pipfile` exists at all).
- **No test runner can be invoked** for any part of the project.

## Test file inventory

- **Zero test files found.**
  - No files matching `*.test.*`, `*.spec.*`, `*_test.*`, or `test_*` exist anywhere in the repository.
  - No `tests/`, `__tests__/`, or `spec/` directory exists.
- File count by layer:
  - `workers/` — 0 test files for `worker.js`
  - `collector/` — 0 test files for any `*.py` script
  - `sql/` — 0 test files for DDL or DML queries

## Coverage status

- **No code coverage tooling configured.**
  - No `nyc`, `c8`, `istanbul`, `pytest-cov`, `coverage.py`, or any coverage reporter.
  - No coverage thresholds, reports, or badges.
- **Effective coverage: 0%** — no code paths in the project are verified by automated tests.

## How to run tests (if any)

- **No test commands exist.** The following would all fail:
  - `npm test` — no `package.json`, no `node_modules/`
  - `pytest` — no `pytest.ini`, no test files, no `pytest` dependency
  - `python -m pytest` — same reason
- **Manual testing only:** Scripts are invoked ad-hoc via `python collector/daily_run.py` or `npx wrangler` commands. Validation relies on print output and log inspection.

## CI/CD checks

- **No CI/CD configuration detected.**
  - No `.github/` directory, no `.gitlab-ci.yml`, no `Jenkinsfile`, no `circleci/config.yml`.
  - No pre-commit hooks, no linting checks, no test gates.
- The only automation in the project is the daily pipeline script (`daily_run.py`), which is executed manually from a "dashboard" per `data/dailypain.log` entries.

## Testing gaps & observations

### Critical gaps

| Area | What's untested | Risk |
|------|----------------|------|
| Naver API interaction | `search_kin()` calls in `collect.py`, `collect_v2.py`, `daily_run.py`, `pipeline.py` | API changes, rate limit errors, malformed responses silently swallowed |
| OpenAI classification | `call_openai()`, `classify_batch()` in all classify files | Prompt structure changes break output parsing; `json.loads()` failure on malformed AI response |
| JSON output parsing | Stripping codeblocks, validating schema, handling missing fields | Production crash observed (`data/dailypain.log:247` string-vs-dict error) |
| D1 database operations | All SQL INSERT/UPDATE/SELECT in `worker.js`, `upload_d1.py`, `daily_run.py` | Schema mismatches, constraint violations, data corruption |
| SQL injection prevention | `esc()` function in `upload_d1.py`, `make_sql.py`, `daily_run.py` | Custom escaping may not cover all edge cases; no parameterized queries in upload scripts |
| `.env` parsing | Manual parser in 6 files | Unhandled edge cases (quotes, escaped chars, comments) could cause silent credential failures |
| Worker HTTP routes | All routes in `worker.js` | CORS, error codes, parameter validation, edge cases untested |
| Dedup logic | `seen`/`seen_links` sets across collect scripts | Hash collisions, URL normalization bugs could cause data duplication |

### Observed runtime failure

- `data/dailypain.log:243-247` — `AttributeError: 'str' object has no attribute 'get'` crashed the pipeline mid-run on 2026-03-15. This type of parsing error would be caught by a simple unit test on the OpenAI response handler.

### Version drift risk

- Multiple parallel versions of the same logic exist (`collect.py` + `collect_v2.py`, `classify.py` + `classify_v2.py`, `pipeline.py` + `daily_run.py`). Without tests, there is no automated verification that they produce consistent results or that bug fixes in one are ported to the other.

### Testability concerns

- **Procedural script execution on import:** Several files (`collect_v2.py`, `classify_v2.py`, `upload_d1.py`, `make_sql.py`, `daily_run.py`) run their entire pipeline at module load time, making them impossible to import testably without side effects.
- **Hard-coded absolute paths** prevent running the pipeline in any other environment (CI, container, different user).
- **No dependency injection** — all secrets, file paths, and API clients are resolved at module level.

---

*Testing analysis: 2026-07-03*
