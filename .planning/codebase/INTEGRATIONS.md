# External Integrations

**Analysis Date:** 2026-07-03

## External APIs / Services

### Naver Open API — Search (kin)

| Field | Detail |
|-------|--------|
| **Endpoint** | `GET https://openapi.naver.com/v1/search/kin.json` |
| **Auth** | HTTP headers `X-Naver-Client-Id` + `X-Naver-Client-Secret` (per-request) |
| **Parameters** | `query`, `display` (max 20), `sort` (`date` or `sim`) |
| **Purpose** | Search Naver Knowledge iN for Q&A matching B2B pain keywords |
| **Used by** | `collector/collect.py`, `collector/collect_v2.py`, `collector/pipeline.py`, `collector/daily_run.py` |
| **Rate limiting** | Implicit 150ms delay between requests in v2 scripts; no exponential backoff |
| **Credential source** | `.env` → `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` |

### OpenAI — Chat Completions API

| Field | Detail |
|-------|--------|
| **Endpoint** | `POST https://api.openai.com/v1/chat/completions` |
| **Auth** | Bearer token via `Authorization` header |
| **Models** | `gpt-5-nano` (primary, used in `pipeline.py`, `classify_v2.py`, `daily_run.py`), `gpt-4o-mini` (in `.env` only) |
| **Features used** | `response_format: {"type": "json_object"}`, `reasoning_effort: "minimal"`, `temperature: 0.2–0.3` |
| **Purpose** | Classify raw Naver posts as actionable/non-actionable business pain points; extract category, pain summary, score |
| **Used by** | `collector/classify.py` (stdlib HTTP), `collector/classify_v2.py` (SDK), `collector/pipeline.py` (stdlib HTTP), `collector/daily_run.py` (SDK) |
| **Batch size** | 10–15 items per API call |
| **Credential source** | `.env` → `OPENAI_API_KEY` |

**Two client implementations coexist:**
- **stdlib HTTP** (`classify.py`, `pipeline.py`): Manual `urllib.request` with JSON body encoding
- **OpenAI Python SDK** (`classify_v2.py`, `daily_run.py`): `from openai import OpenAI`; `client.chat.completions.create()`

### Cloudflare Workers — D1 HTTP Upload (internal)

| Field | Detail |
|-------|--------|
| **Endpoint** | `POST {D1_API_URL}/api/pain` |
| **Auth** | Bearer token via `Authorization: Bearer {D1_API_KEY}` |
| **Purpose** | Insert classified pain points into D1 via Worker HTTP endpoint (alternative to `wrangler d1 execute`) |
| **Used by** | `collector/pipeline.py` |
| **Source configuration** | `.env` → `D1_API_URL`, `D1_API_KEY` (both optional; if unset the upload step is skipped) |

## Data Sources & Formats

### Primary Source: Naver Knowledge iN

- **Query method**: 42 B2B pain keywords from `collector/keywords.json` (e.g., `"사업자 세금 신고 어려워"`, `"매출 정리 어려워"`)
- **Deduplication**: MD5 hash of `link` URL (v2) or URL string set (v1)
- **HTML cleaning**: `re.sub(r"<[^>]+>", "")` (v1) or string `.replace("<b>", "")` (v2 — note: regex is more robust)
- **Data structure collected**:
  ```json
  {"keyword": "...", "title": "...", "description": "...", "link": "...", "collected_at": "..."}
  ```

### Data Pipeline File Formats

| Stage | File Pattern | Format |
|-------|-------------|--------|
| Raw collection | `data/{date}-raw.json` (and `-v2.json`) | JSON array of collected items |
| Classified | `data/{date}-classified.json` (and `-v2.json`) | JSON array of actionable items only |
| SQL upload | `data/{date}-upload.sql` | `INSERT OR IGNORE INTO pain_points ...` |
| Pipeline log | `data/dailypain.log` | Timestamped log lines |

## Cloud Platform Services

### Cloudflare Workers

- **Service name**: `dailypain` (from `wrangler.toml`)
- **Entry point**: `workers/worker.js`
- **Runtime**: Cloudflare Workers (compatibility_date `2024-01-01`)
- **Routes**:
  | Method | Path | Purpose |
  |--------|------|---------|
  | `GET` | `/` | Serve single-page HTML frontend |
  | `POST` | `/api/pain` | Insert pain point (authenticated via Bearer token) |
  | `GET` | `/api/pains` | Query by date + optional category |
  | `GET` | `/api/dates` | List distinct dates with data |
  | `POST` | `/api/star` | Toggle star on a pain point |
  | `GET` | `/api/starred` | List all starred points |
  | `GET` | `/auth/callback` | OAuth placeholder (returns "OK") |
  | `GET` | `/deauth` | OAuth placeholder |
  | `POST` | `/data-deletion` | OAuth placeholder |
- **CORS**: Wide-open (`Access-Control-Allow-Origin: *`)

### Cloudflare D1

- **Database name**: `dailypain-db`
- **Database ID**: `a1d49dc0-273f-4f89-858d-28268d182f32`
- **Binding**: `env.DB` in Workers
- **Access from pipeline**:
  1. **Via Worker HTTP** (`pipeline.py`): POST to `/api/pain` with Bearer token
  2. **Via wrangler CLI** (`upload_d1.py`, `daily_run.py`, `make_sql.py`): `npx wrangler d1 execute dailypain-db --remote --file={sql}` or `--command={sql}`

## Authentication / Authorization

| Integration | Auth Mechanism | Notes |
|-------------|---------------|-------|
| Naver Open API | `X-Naver-Client-Id` + `X-Naver-Client-Secret` headers | Static keys from `.env` |
| OpenAI API | `Authorization: Bearer {key}` header | Static key from `.env` |
| D1 HTTP upload | `Authorization: Bearer {D1_API_KEY}` | Static key from `.env` |
| Workers API (read) | None | `/api/pains`, `/api/dates`, `/api/starred` are public |
| Workers API (write) | Bearer token | `/api/pain` POST requires auth |
| OAuth endpoints | Placeholder | `/auth/callback`, `/deauth`, `/data-deletion` return static responses — no OAuth provider configured |

## Webhooks / Callbacks

None of the webhook-like endpoints are wired to a real external service:

| Endpoint | Response | Status |
|----------|----------|--------|
| `GET /auth/callback` | `"OK"` (text/plain) | Placeholder — no redirect or state validation |
| `GET /deauth` | `{"success": true}` | Placeholder — no session management |
| `POST /data-deletion` | `{"url":..., "confirmation_code":"dp_..."}` | Placeholder — generates timestamped code but does nothing |

**These appear to be pre-configured for a future OAuth integration (e.g., Naver or Threads OAuth) but are not yet connected.**

## Third-Party Dependencies

### Python

| Package | Version Pinned | Used In | Notes |
|---------|---------------|---------|-------|
| `openai` | No | `classify_v2.py`, `daily_run.py` | SDK client for GPT |
| All others | N/A (stdlib) | All Python files | `os`, `json`, `urllib.*`, `re`, `hashlib`, `time`, `subprocess`, `datetime`, `argparse`, `pathlib` |

**No `requirements.txt` or `pyproject.toml` exists.** The `openai` package must be installed globally.

### JavaScript / Workers

- **Zero npm runtime dependencies** — pure Workers runtime API
- **wrangler** is a dev dependency (not captured in any `package.json`)

### Secrets / Credentials Storage

- **`.env`** — all 6 environment variables, loaded at runtime by Python scripts
- **`wrangler.toml`** — contains D1 database ID (non-secret but sensitive infrastructure identifier)
- **`.dev.vars`** — gitignored but not present (fallback Workers secrets file)
- **No secrets manager** — no integration with Cloudflare Workers Secrets, Vault, or similar

## Integration Risks / Notes

1. **Naver API rate limits undetermined**: 150ms sleep between requests is heuristic, no documented rate limit handling or retry/backoff logic.

2. **OpenAI model instability**: `gpt-5-nano` is used across 4 scripts but appears to be an unreleased/preview model name. If it becomes unavailable or changes behavior, classification will break.

3. **SQL injection in `upload_d1.py`**: Uses `str(s).replace("'", "''")` to escape SQL — fragile. The pipeline.py path via Worker API is safer (parameterized binding).

4. **OAuth endpoints are fake**: If a real OAuth provider (Naver, Threads) is attached later, the current placeholder handlers will need full rewrites.

5. **Threads token orphaned**: `THREADS_ACCESS_TOKEN` exists in `.env` but zero code references it — possibly a leftover from an abandoned integration.

6. **No CI/CD**: No pipeline configuration; deployments are manual (`wrangler deploy`). No automated integration tests between collector and API.

7. **Data format duplication**: v1 and v2 scripts coexist but produce different JSON schemas (`actionable` boolean vs `keep` + `is_actionable`). Future maintainers must track which format is current.

8. **Deduplication inconsistency**: v1 uses URL string set; v2 uses MD5 hash of URL. Both work but v2 is slightly more memory-efficient.

---

*Integration audit: 2026-07-03*
