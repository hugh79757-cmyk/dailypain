# Architecture

**Analysis Date:** 2026-07-03

## High-level overview

`DailyPain` is a small data-pipeline + serverless-dashboard application that:

1. Collects Naver Knowledge iN (`kin`) search results for B2B pain-related keywords.
2. Uses OpenAI (`gpt-5-nano`) to classify which questions represent actionable business pain points.
3. Stores the top results in Cloudflare D1.
4. Serves them through a Cloudflare Worker that also renders a single-page HTML dashboard.

Everything is file-based and script-driven: the Python collector runs locally (or from a dashboard trigger), writes artifacts to `data/`, then uploads to D1. The Worker has no build step and serves both the JSON API and the UI from one file.

## Components & responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Worker (API + UI) | CORS handling, JSON API, embedded dashboard HTML, D1 queries | `workers/worker.js` |
| Worker config | D1 binding, project name, compatibility date | `workers/wrangler.toml` |
| Daily orchestrator | Collect → classify → SQL generation → D1 upload + logging | `collector/daily_run.py` |
| Legacy integrated pipeline | Standalone collect/classify/upload via Worker `POST /api/pain` | `collector/pipeline.py` |
| Collector (v1) | Search Naver Kin and write raw JSON | `collector/collect.py` |
| Collector (v2) | Search with `b2b_pain_keywords`, hash-based deduplication, write `-raw-v2.json` | `collector/collect_v2.py` |
| Classifier (v1) | OpenAI batch classification, writes `-classified.json` | `collector/classify.py` |
| Classifier (v2) | Stricter B2B SaaS filter using the `openai` SDK, writes `-classified-v2.json` | `collector/classify_v2.py` |
| SQL generator | Converts classified JSON into `INSERT OR IGNORE` statements | `collector/make_sql.py` |
| D1 uploader | Uploads top 50 items via per-row `wrangler d1 execute` calls | `collector/upload_d1.py` |
| Keyword list | Search phrases used by collectors | `collector/keywords.json` |
| Database schema | D1 table/index definitions | `sql/create-tables.sql` |
| Context exporter | Backs up / exports repo context with secret masking | `backup3.py` |
| Secrets file | Holds API keys and DB credentials (not read for this doc) | `.env` |

## Data flow: collect → classify → upload → serve

### 1. Collect
- `collector/daily_run.py` (or `collect.py` / `collect_v2.py`) calls Naver Open API `https://openapi.naver.com/v1/search/kin.json` for each phrase in `collector/keywords.json`.
- Results are deduplicated by `link` (or MD5 hash in v2) and written to `data/{date}-raw.json` (`-raw-v2.json` for v2).

### 2. Classify
- `collector/daily_run.py` sends batches of 15 rows to OpenAI (`gpt-5-nano`, `json_object` response).
- `collector/classify.py` and `collector/classify_v2.py` do similar batch classification.
- The model returns `keep`/`actionable`, `category`, `pain_summary`, `pain_score`, `solution_hint`.
- Classified rows are written to `data/{date}-classified.json` (or `-classified-v2.json`).

### 3. Upload
- `collector/daily_run.py` generates `data/{date}-upload.sql` with up to 50 `INSERT OR IGNORE` statements and runs:
  ```
  npx wrangler d1 execute dailypain-db --remote --file={sql_path}
  ```
  from `workers/`.
- `collector/upload_d1.py` does the same for `data/{date}-classified.json` but executes one SQL statement per item.
- `collector/pipeline.py` uploads via HTTP `POST {D1_API_URL}/api/pain` with a `Bearer {D1_API_KEY}` header.

### 4. Serve
- `workers/worker.js` handles all requests.
- It reads from the D1 binding `env.DB` and returns JSON, or returns the embedded dashboard HTML for the root path.

## Request lifecycle

All traffic enters through `workers/worker.js`:

1. CORS preflight and headers are attached to every response.
2. Path routing:
   - `POST /api/pain` — insert one pain point (Worker parses JSON; currently no auth check, but `pipeline.py` sends an `Authorization` header).
   - `GET /api/pains?date=YYYY-MM-DD&category=...` — list up to 50 pain points for a date, optionally filtered by category, ordered by `pain_score DESC`.
   - `GET /api/dates` — list last 30 distinct dates.
   - `POST /api/star` + `GET /api/starred` — toggle and list starred items.
   - `/auth/callback`, `/deauth`, `/data-deletion` — placeholders for OAuth/app-meta callbacks.
   - Fallback — returns the dashboard HTML from the inline `getHTML()` function.
3. Database access is always through `env.DB.prepare(...).bind(...).all()` / `.run()`.

## Deployment topology

- **Edge function:** Cloudflare Worker (`dailypain`), configured by `workers/wrangler.toml`.
- **Database:** Cloudflare D1 (`dailypain-db`) bound as `DB`.
- **Scheduled/background work:** Python collector scripts run locally or from another host. There is no Cloudflare Cron / Queue / Workflow in the repo.
- **External APIs:** Naver Search API (collector), OpenAI Chat Completions API (collector).
- **Public URL referenced:** `https://dailypain.hugh79757.workers.dev` (hard-coded in `collector/upload_d1.py`).

## Data model summary

Source: `sql/create-tables.sql`

### `pain_points`
- `id` — primary key, autoincrement.
- `source` — default `'naver_kin'`.
- `source_url` — unique URL of the Naver Kin question.
- `keyword` — search phrase that found the item.
- `title`, `description` — cleaned title/snippet from Naver Kin.
- `category` — business domain assigned by the classifier.
- `pain_summary` — one-sentence problem summary.
- `pain_score` — integer 0-100.
- `solution_hint` — one-sentence SaaS idea.
- `is_actionable` — boolean flag.
- `collected_at`, `classified_at` — ISO timestamps.
- `created_at` — auto timestamp.

### `daily_stats`
- Defined but not written to by any current script.

### Indexes
- `idx_pain_category`, `idx_pain_score`, `idx_pain_date`, `idx_pain_actionable` on `pain_points`.

## API surface

| Method | Path | Params / Body | Response |
|--------|------|---------------|----------|
| `OPTIONS` | `*` | — | CORS-only 204 |
| `POST` | `/api/pain` | `{date,keyword,category,title,description,pain_summary,pain_score,solution_hint,source_url,source}` | `{ok:true}` or `{error}` |
| `GET` | `/api/pains` | `?date=YYYY-MM-DD` (default today), `?category=...` | Array of rows |
| `GET` | `/api/dates` | — | Array of date strings |
| `POST` | `/api/star` | `{id}` | `{ok:true}` (toggles `starred`) |
| `GET` | `/api/starred` | — | Array of starred rows |
| `GET` | `/auth/callback` | — | Plain-text `OK` |
| `GET/POST` | `/deauth` | — | `{success:true}` |
| `GET/POST` | `/data-deletion` | — | `{url,confirmation_code}` |
| `GET` | `/` | — | Dashboard HTML |

## Architectural constraints

- **No auth on Worker endpoints:** `POST /api/pain` inserts directly; only the optional `Authorization` header from `pipeline.py` is not validated.
- **Single-file Worker:** API, HTML, CSS, and client-side JavaScript are all in `workers/worker.js`.
- **`daily_stats` table is unused:** Only `pain_points` receives inserts.
- **v1 and v2 collectors/classifiers coexist but are disconnected:** `daily_run.py` does not use `-v2` artifacts; `collect_v2.py`/`classify_v2.py` produce files that are not uploaded by `daily_run.py`.
- **Upload uses shell calls to `wrangler`:** `daily_run.py` and `upload_d1.py` invoke the Wrangler CLI via `subprocess.run`, relying on local `npx` and the user's Cloudflare auth.
- **`.`env is required at runtime:** Collectors parse `.env` manually with string splitting (no `python-dotenv`).
- **`data/` is gitignored:** Artifacts are not committed by default.
