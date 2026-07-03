# Coding Conventions

**Analysis Date:** 2026-07-03

## Code style & formatting

- **No linting or auto-formatting tooling configured:**
  - No `.eslintrc*`, `.prettierrc*`, `eslint.config.*`, `biome.json`, `pyproject.toml`, `setup.cfg`, `.flake8`, `.pylintrc`, `ruff.toml`, or equivalent.
  - `backup3.py` references cache/venv exclusion paths but none are actively in use.
- Style is hand-formatted and inconsistent across files.
- **JavaScript** (`workers/worker.js`):
  - Compact single-line patterns for CORS headers, route dispatch, and HTML generation.
  - Mixed spacing around braces; no semicolons in the inline HTML style block.
  - Long template literal for HTML (~2000 chars) is embedded directly inside a function.
- **Python** (`collector/*.py`):
  - Import styles vary: comma-separated on one line (`collect_v2.py:1`) vs one-per-line (`collect.py:1-5`, `pipeline.py:5-9`).
  - Empty lines with Korean comment fences used as visual section separators (e.g., `# ── 1단계: 수집 ──`).
  - Many lines exceed ~100 characters (long SQL strings, OpenAI prompt literals).
  - Inconsistent use of parentheses around multi-line expressions (some wrapped, some not).
- **SQL** (`sql/create-tables.sql`):
  - Standard DDL with uppercase keywords, consistent indentation, trailing semicolons.

## Naming conventions

- **Python:**
  - Functions/variables: `snake_case` — `clean_html()`, `search_kin()`, `collect_pain_points()`, `call_openai()`, `classify_batch()`.
  - Module-level constants: `UPPER_SNAKE_CASE` — `SCRIPT_DIR`, `PROJECT_DIR`, `NAVER_ID`, `OPENAI_KEY`, `MAX_FILE_SIZE`.
  - Iteration/temp variables often single-letter: `i`, `j`, `k`, `c`, `r`.
  - Files: `snake_case.py` — `collect.py`, `daily_run.py`, `make_sql.py`.
  - Versioned iterations use `_v2` suffix: `collect_v2.py`, `classify_v2.py`.
- **JavaScript:**
  - Variables: `camelCase` — `url`, `cors`, `dateSelect`, `catSelect`.
  - Constants within function scope: lowercase or `camelCase` (`cors`).
  - File: `worker.js` (hyphen not used despite project conventions).
- **SQL:**
  - Indexes: `idx_<table>_<column>` pattern (`idx_pain_category`, `idx_pain_score`).

## Language-specific patterns

- **Python (collector scripts):**
  - Top-level guard: `if __name__ == "__main__":` used only in `collect.py`, `classify.py`, `pipeline.py`, `backup3.py`.
  - Several scripts are fully procedural and execute on import: `collect_v2.py`, `classify_v2.py`, `upload_d1.py`, `make_sql.py`, `daily_run.py`.
  - HTTP requests via `urllib.request` (standard library) in older files; `openai` SDK in `classify_v2.py` and `daily_run.py`.
  - JSON processing via standard `json` module throughout.
  - `subprocess.run(["npx", "wrangler", "d1", "execute", ...])` used for D1 uploads from `upload_d1.py` and `daily_run.py`.
  - `.env` parsing is duplicated across 6 files, each implementing its own string-split parser.
  - Hard-coded absolute paths (`"/Users/twinssn/Projects/dailypain/..."`) appear in `collect_v2.py`, `classify_v2.py`, `upload_d1.py`, `make_sql.py`, `daily_run.py` — not portable.
- **JavaScript (Worker):**
  - Single default-export object with `async fetch(request, env)` handler — standard Cloudflare Workers pattern.
  - D1 binding accessed via `env.DB.prepare(sql).bind(...).run()/.all()`.
  - No middleware, no router library, no TypeScript — pure procedural JS.
- **SQL:**
  - D1-compatible SQLite syntax: `INSERT OR IGNORE`, `AUTOINCREMENT`, `BOOLEAN` (stored as integer).

## Error handling

- **Dominant pattern:** Broad `try/except Exception` (Python) and `try/catch(e)` (JS) catching all exception types.
  - `collect.py:58` — per-pattern Naver API errors caught and printed, loop continues.
  - `pipeline.py:67` — collection errors printed with Korean prefix `[수집 ERROR]`.
  - `pipeline.py:139` / `classify.py:83` — classification batch errors caught, empty classified list returned.
  - `upload_d1.py:176` — upload errors silently pass (`pass` with no logging), making failures invisible.
  - `daily_run.py:66` — collection errors logged, loop continues.
  - `worker.js:14` — returns HTTP 500 with raw `e.message` to client.
- **No structured error types** (no custom exception classes, no error code enums).
- **No retry/backoff** beyond a static `time.sleep(0.15)` / `time.sleep(0.5)` between API calls.
- **Production error observed:** `data/dailypain.log:247` shows `AttributeError: 'str' object has no attribute 'get'` in `daily_run.py:112`, where an OpenAI response was parsed as a string instead of a dict — error path not robust.

## Logging approach

- **No standard library `logging` module used** anywhere.
- **`print()` based:**
  - `collect.py`, `classify.py`, `pipeline.py`, `collect_v2.py`, `classify_v2.py`, `upload_d1.py`, `make_sql.py` — all use `print()` for progress, results, and errors.
  - Messages are in Korean with bracketed English prefixes (e.g., `[수집 ERROR]`, `[분류]`).
- **Custom file logging:**
  - `daily_run.py:20-24` — defines `log(msg)` that prints + appends to `data/dailypain.log` with `[YYYY-MM-DD HH:MM:SS]` timestamp.
  - `data/dailypain.log` is in `.gitignore` and grows unbounded (no rotation).
- **Worker JS:** No server-side logging; errors surface only in the HTTP response body.

## Configuration/secrets handling

- **Primary secrets store:** `/Users/twinssn/Projects/dailypain/.env` — listed in `.gitignore`, must not be committed.
- **No `.env.example`** — required keys are undocumented.
- **Manual `.env` parsing** duplicated in 6 files:
  - `collect.py:12-17` — line-split on `=`, populates local `env_vars` dict.
  - `classify.py:9-15` — same pattern.
  - `pipeline.py:16-22` — same pattern.
  - `collect_v2.py:5-11` — writes directly to `os.environ`.
  - `classify_v2.py:5-11` — writes to `os.environ`.
  - `daily_run.py:6-12` — writes to `os.environ`.
  - This parser does **not** handle: quoted values, escaped `=` signs, comments mid-line, or `export` prefix.
- **Required env vars observed in code:**
  - `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` — Naver search API credentials.
  - `OPENAI_API_KEY` — OpenAI chat completions API key.
  - `D1_API_URL`, `D1_API_KEY` — optional, used by `pipeline.py` for direct HTTP upload.
- **Hard-coded absolute paths** in `collect_v2.py:5`, `classify_v2.py:5`, `upload_d1.py:5`, `make_sql.py:5`, `daily_run.py:6` — prevent running on other machines.
- **`workers/wrangler.toml:8`** — D1 `database_id` is in plain text (not a secret binding).
- **`.dev.vars`** — referenced in `.gitignore` for local Worker secrets but file does not exist.

## Internationalization/language usage

- **No i18n framework, translation files, or locale detection.**
- **Korean hard-coded throughout:**
  - Worker HTML: `<p>한국 사업자의 매일 페인포인트</p>`, all UI labels in Korean.
  - AI prompts in `classify.py`, `classify_v2.py`, `pipeline.py`, `daily_run.py` — written in Korean, requesting Korean output fields.
  - Console/log messages: Korean with some English bracketed prefixes.
  - Comments: Korean section markers (`# ── 1단계: 수집 ──`), Korean inline notes.
- **English used for:**
  - Code identifiers (function names, variable names).
  - JSON keys (`"keyword"`, `"title"`, `"pain_score"`).
  - SQL keywords and column names.
  - Standard library/API references.

## Documentation/comments

- **Python docstrings:** Minimal. `pipeline.py:1-3` has a module-level Korean docstring. `backup3.py` has extensive inline comments and structured constant blocks in Korean.
- **Inline comments:** Korean section separators with `# ── ... ──` pattern (6+ occurrence across collector scripts).
- **No JSDoc/TSDoc** in `workers/worker.js` — zero function-level documentation.
- **No project-level documentation:**
  - No `README.md`, `AGENTS.md`, or `.planning/STATE.md` at project root.
  - No type hints in Python (all collector scripts).
  - No TypeScript or type annotations in the Worker.
  - SQL `create-tables.sql` has no comments on table purpose or columns.
- **`backup3.py`** is the most thoroughly documented file — includes argument parser help strings, function docstrings (Korean), and structured constants with comments.

---

*Convention analysis: 2026-07-03*
