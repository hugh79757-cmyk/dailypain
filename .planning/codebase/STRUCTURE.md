# Codebase Structure

**Analysis Date:** 2026-07-03

## Directory layout

```
/Users/twinssn/Projects/dailypain/
├── .planning/
│   └── codebase/          # GSD mapping outputs (this doc lives here)
├── collector/             # Python data-collection and classification scripts
├── data/                  # Generated daily JSON/SQL artifacts and log
├── docs/                  # Empty directory
├── sql/                   # Database DDL
├── workers/               # Cloudflare Worker code and config
├── .env                   # Secrets (gitignored, not read for this doc)
├── .gitignore
├── backup3.py             # Repo context exporter
└── .DS_Store
```

## File inventory (grouped by directory)

### `collector/`
- `collector/daily_run.py` — Main orchestrator: collect, classify, create SQL, upload via Wrangler, write log.
- `collector/pipeline.py` — Standalone collect/classify/upload pipeline that posts to Worker `/api/pain`.
- `collector/collect.py` — Naver Kin collector (v1); writes `data/{date}-raw.json`.
- `collector/collect_v2.py` — Naver Kin collector (v2); uses `b2b_pain_keywords`, writes `data/{date}-raw-v2.json`.
- `collector/classify.py` — OpenAI classifier (v1); writes `data/{date}-classified.json`.
- `collector/classify_v2.py` — OpenAI classifier (v2); stricter filter, uses `openai` SDK, writes `data/{date}-classified-v2.json`.
- `collector/upload_d1.py` — Uploads top 50 classified items via `wrangler d1 execute` per item.
- `collector/make_sql.py` — Generates `data/{date}-upload.sql` from classified JSON.
- `collector/keywords.json` — Search phrase dictionary (`b2b_pain_keywords`).

### `workers/`
- `workers/worker.js` — Cloudflare Worker entry point: API routes + embedded dashboard.
- `workers/wrangler.toml` — Worker/D1 configuration.
- `workers/.wrangler/cache/wrangler-account.json` — Generated Wrangler cache file.

### `sql/`
- `sql/create-tables.sql` — DDL for `pain_points` and `daily_stats` tables plus indexes.

### `data/`
- `data/{YYYY-MM-DD}-raw.json` — Collected Naver Kin results (v1).
- `data/{YYYY-MM-DD}-raw-v2.json` — Collected Naver Kin results (v2).
- `data/{YYYY-MM-DD}-classified.json` — Classified actionable pain points (v1).
- `data/{YYYY-MM-DD}-classified-v2.json` — Classified actionable pain points (v2).
- `data/{YYYY-MM-DD}-upload.sql` — Generated `INSERT OR IGNORE` statements.
- `data/dailypain.log` — Timestamped run log from `daily_run.py`.

### Root files
- `backup3.py` — Context-backup utility that exports selected source files with secret masking.
- `.env` — Environment secrets (gitignored; existence only noted here).
- `.gitignore` — Ignores `.DS_Store`, `node_modules/`, `.dev.vars`, `.env`, `*.log`, `__pycache__/`, `venv/`, `.venv/`, `data/`.
- `.DS_Store` — macOS metadata file.

## Module boundaries

- **`collector/` depends on external APIs and `.env`; it does not import any local package modules.** Each script duplicates `.env` parsing and path construction.
- **`workers/` is self-contained.** `worker.js` has no external build-time dependencies; it only uses the Workers runtime `env.DB` binding.
- **`sql/` is documentation / migration DDL.** No tool applies it automatically in the current scripts.
- **`data/` is the interchange layer** between Python scripts and D1 (JSON and SQL artifacts).
- **`backup3.py` is standalone tooling** and is not invoked by the pipeline.

## Entry points

- **Daily run (recommended):** `collector/daily_run.py`
- **Legacy integrated pipeline:** `collector/pipeline.py`
- **Worker runtime entry:** `workers/worker.js` (as declared by `workers/wrangler.toml` `main = "worker.js"`)
- **Manual collection:** `collector/collect.py` or `collector/collect_v2.py`
- **Manual classification:** `collector/classify.py` or `collector/classify_v2.py`
- **Manual upload:** `collector/upload_d1.py` or `collector/make_sql.py` + `wrangler d1 execute`
- **Backup export:** `backup3.py`

## Generated/data artifacts

Location: `data/`

| Pattern | Produced by | Consumed by |
|---------|-------------|-------------|
| `{date}-raw.json` | `collect.py`, `daily_run.py` | `classify.py`, `daily_run.py` |
| `{date}-raw-v2.json` | `collect_v2.py` | `classify_v2.py` |
| `{date}-classified.json` | `classify.py`, `daily_run.py` | `upload_d1.py`, `make_sql.py`, `daily_run.py` |
| `{date}-classified-v2.json` | `classify_v2.py` | Nothing currently |
| `{date}-upload.sql` | `make_sql.py`, `daily_run.py` | `wrangler d1 execute` |
| `dailypain.log` | `daily_run.py` | Human-readable / debugging |

`data/` is listed in `.gitignore`, so these artifacts are normally not committed.

## Notable file roles

- `collector/daily_run.py` — The only script that performs the full end-to-end daily workflow; it also generates the SQL file and shells out to Wrangler.
- `collector/pipeline.py` — Serves as an alternative upload path that bypasses SQL generation and posts directly to the Worker. Useful if D1 HTTP access is preferred over local Wrangler CLI.
- `workers/worker.js` — Contains the entire backend and frontend: route handling, D1 queries, CORS, and the dashboard's HTML/CSS/JS in one function.
- `sql/create-tables.sql` — Defines the schema; the `daily_stats` table exists but is not populated by any script.
- `backup3.py` — Not part of the product; provides a snapshot of the repository with sensitive-value masking.
