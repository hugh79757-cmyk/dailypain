# DailyPain — Agent Context

## What This Project Does

DailyPain is a B2B pain-point discovery tool. It:
1. Collects Naver Knowledge iN (지식인) posts matching B2B pain keywords
2. Classifies each post via OpenAI (GPT-5-nano) as actionable/non-actionable
3. Stores actionable items in Cloudflare D1
4. Serves a searchable dashboard via Cloudflare Workers

## Architecture (2 subsystems)

| Subsystem | Language | Entry Point | Purpose |
|-----------|----------|-------------|---------|
| **Pipeline** | Python 3.14 | `collector/daily_run.py` | Collect → classify → upload to D1 |
| **API + Dashboard** | JavaScript (Workers) | `workers/worker.js` | REST API + embedded HTML dashboard |

## Key Files

| File | Role |
|------|------|
| `collector/daily_run.py` | Canonical pipeline (collect, classify, upload) |
| `collector/pipeline.py` | Alternative pipeline (HTTP-upload variant) |
| `collector/keywords.json` | Naver search keywords (42 B2B pain phrases) |
| `workers/worker.js` | Worker: REST API + HTML dashboard |
| `workers/wrangler.toml` | Worker config + D1 binding |
| `sql/create-tables.sql` | D1 DDL (`pain_points` table + indexes) |
| `tests/test_daily_run.py` | Python unit tests |
| `tests/worker.test.js` | Worker unit tests |

## External APIs

| API | Auth | Used In |
|-----|------|---------|
| Naver Open API (kin search) | `X-Naver-Client-Id` + `X-Naver-Client-Secret` | daily_run.py, pipeline.py |
| OpenAI Chat Completions | `Authorization: Bearer` | daily_run.py, pipeline.py |
| Cloudflare D1 | `env.DB` binding (Workers) | worker.js |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NAVER_CLIENT_ID` | Yes | Naver API client ID |
| `NAVER_CLIENT_SECRET` | Yes | Naver API client secret |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `D1_API_URL` | For upload | Worker base URL (e.g., https://dailypain.example.com) |
| `D1_API_KEY` | For upload | Worker API_TOKEN (matches `wrangler secret put API_TOKEN`) |

## Setup
```bash
pip install -e .
npm ci
cp .env.example .env       # fill in secrets
npx wrangler secret put API_TOKEN
```

## Testing
```bash
python -m pytest          # Python tests
npx vitest run            # Worker tests
ruff check                # Python lint
npx eslint workers/worker.js  # JS lint
```

## Key Patterns
- `retry_with_backoff()` wraps all external API calls (exponential backoff: 1s, 2s, 4s)
- `isinstance(r, dict)` guard prevents `AttributeError` on malformed AI responses
- HTTP upload to Worker `/api/pain` with Bearer auth (no f-string SQL anywhere)
- CORS restricted to known Worker origin only
