# Technology Stack

**Analysis Date:** 2026-07-03

## Overview

DailyPain is a two-subsystem project: a **Python 3 data pipeline** that collects Naver Knowledge iN posts, classifies them via OpenAI, and uploads to Cloudflare D1; and a **Cloudflare Workers JavaScript API** that serves the classified pain points via HTTP endpoints with an embedded frontend.

## Languages / Runtimes

| Language | Version | Where Used |
|----------|---------|------------|
| **Python** | 3.14.5 | Collector/classifier pipeline (`collector/*.py`, `backup3.py`) |
| **JavaScript (ES modules)** | Workers runtime | API server (`workers/worker.js`) |
| **Node.js** | v25.2.1 | Local dev tooling (wrangler CLI) |

## Frameworks / Libraries

| Category | Tool | Purpose |
|----------|------|---------|
| **AI classification** | `openai` Python SDK (v1+) | GPT chat completions (`gpt-5-nano` / `gpt-4o-mini`) |
| **API server** | None | Workers uses native `fetch` handler (no framework) |
| **HTTP client (stdlib)** | `urllib.request` | All Naver API + OpenAI calls (no `requests` library) |

## Build / Deployment Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **wrangler** | 11.6.2 | Cloudflare Workers deploy + D1 database management |
| **npx** | bundled | Invokes `wrangler d1 execute` for SQL uploads |

## Package Management

| Platform | Manager | Lockfile | Notes |
|----------|---------|----------|-------|
| **Python** | None | N/A | No `requirements.txt`, `pyproject.toml`, or `Pipfile` detected |
| **Node** | npm | Missing | `node_modules/` gitignored; no `package-lock.json` |

**Implication:** Python dependencies (`openai`) must be installed globally or manually. Environment is not reproducible without additional setup.

## Data Stores

| Store | Type | Detail |
|-------|------|--------|
| **Cloudflare D1** | SQLite-compatible (edge) | Database `dailypain-db` (id `a1d49dc0-273f-4f89-858d-28268d182f32`). Tables: `pain_points`, `daily_stats`. Binding `DB` in `wrangler.toml`. |
| **Local filesystem** | JSON + SQL files | `data/` directory: daily raw/classified JSON dumps, upload SQL files, pipeline log (`dailypain.log`) |

### D1 Schema (`sql/create-tables.sql`)

- **`pain_points`**: `id`, `source` (default `naver_kin`), `source_url` (UNIQUE), `keyword`, `title`, `description`, `category`, `pain_summary`, `pain_score`, `solution_hint`, `is_actionable`, `collected_at`, `classified_at`, `created_at`
- **`daily_stats`**: `id`, `date` (UNIQUE), `total_collected`, `total_actionable`, `top_categories`, `created_at`
- **Indexes**: `idx_pain_category`, `idx_pain_score` (DESC), `idx_pain_date`, `idx_pain_actionable`

## Environment Variables Summary

| Variable | Source | Used By | Notes |
|----------|--------|---------|-------|
| `NAVER_CLIENT_ID` | `.env` | `collect*.py`, `pipeline.py`, `daily_run.py` | Naver Open API client ID |
| `NAVER_CLIENT_SECRET` | `.env` | `collect*.py`, `pipeline.py`, `daily_run.py` | Naver Open API client secret |
| `OPENAI_API_KEY` | `.env` | `classify*.py`, `pipeline.py`, `daily_run.py` | OpenAI API key |
| `OPENAI_MODEL` | `.env` | Not actively referenced | Set to `gpt-4o-mini` but code uses `gpt-5-nano` |
| `D1_API_URL` | `.env` | `pipeline.py` | Optional — HTTP endpoint for direct D1 upload |
| `D1_API_KEY` | `.env` | `pipeline.py` | Optional — Bearer token for D1 upload endpoint |
| `THREADS_ACCESS_TOKEN` | `.env` | Not used in code | Present in `.env` but never referenced — possibly legacy |

`.env` is loaded at runtime by individual Python scripts via manual line parsing. Workers use `wrangler.toml` / Cloudflare bindings (no `.dev.vars` detected).

## Version-Compatibility Notes

- **Workers compatibility_date**: `2024-01-01` — stable Worker runtime
- **OpenAI model `gpt-5-nano`**: Appears to be a preview/experimental model name. `gpt-4o-mini` is in `.env` but not consistently used.
- **Python 3.14.5**: Recent — no `.python-version` to enforce runtime.
- **No lockfiles**: Python env and npm dependencies are not pinned, risking drift.
- **Data format drift**: v1 vs v2 scripts produce different JSON structures (`actionable` boolean vs `keep` + `is_actionable`).

## Configuration Files

| File | Purpose |
|------|---------|
| `workers/wrangler.toml` | Worker name, entry point, D1 binding |
| `collector/keywords.json` | 42 B2B pain point keywords for Naver search |
| `sql/create-tables.sql` | D1 table + index DDL |
| `.gitignore` | Excludes `.env`, `node_modules/`, `__pycache__/`, `venv/`, `data/`, `*.log` |
| `.env` | All secrets and API keys (gitignored) |

---

*Stack analysis: 2026-07-03*
