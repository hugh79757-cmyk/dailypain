# DailyPain — Requirements

**Scope:** Full stabilization of existing codebase
**Source:** Codebase map (CONCERNS.md, TESTING.md, STACK.md)

## Functional Requirements (existing — must preserve)

- FR1: Collect Naver Knowledge iN posts by B2B pain-point keywords
- FR2: Classify collected posts via OpenAI (actionable vs non-actionable)
- FR3: Serve classified pain points via Cloudflare Workers API + dashboard
- FR4: Support filtering by date and category
- FR5: Support starring/highlighting specific pain points
- FR6: Upload pipeline results to Cloudflare D1 database

## Non-Functional Requirements

### NFR1: Reproducibility
- Declare all Python dependencies in `requirements.txt` (or `pyproject.toml`)
- Declare Node/Workers dependencies in `package.json`
- Remove hardcoded absolute paths; use relative path resolution

### NFR2: Data Integrity
- Fix D1 schema file (`sql/create-tables.sql`) to match actual table structure (add `date`, `starred` columns)
- Use parameterized queries / prepared statements everywhere (eliminate f-string SQL)
- De-duplicate `source_url` handling must be explicit

### NFR3: Security
- Add authentication/authorization to all Worker POST endpoints
- Remove or narrow `Access-Control-Allow-Origin: *`
- Stop manual `.env` line parsing; use `os.environ` directly or python-dotenv
- Never expose database error messages to API clients
- Move secrets out of version control (wrangler.toml database_id)

### NFR4: Reliability
- Add retry with exponential backoff for Naver API and OpenAI calls
- Validate OpenAI response structure before indexing
- Handle malformed AI responses gracefully
- Add proper error logging (not bare `except Exception: pass`)

### NFR5: Testability
- Add test framework (pytest for Python, vitest for Workers)
- Achieve basic coverage on critical paths:
  - OpenAI response parsing (prevent `AttributeError` reoccurrence)
  - SQL generation / parameterized queries
  - Worker route handlers
- Add CI/CD pipeline (GitHub Actions)

### NFR6: Maintainability
- Consolidate duplicate scripts (v1 vs v2, pipeline.py vs daily_run.py)
- Remove orphaned artifacts (backup3.py, backup TXT, unused `daily_stats` table writes)
- Add code linting configuration
- Add AGENTS.md for future LLM-assisted development
- Set up log rotation for `data/dailypain.log`
