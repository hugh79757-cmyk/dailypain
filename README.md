# DailyPain

한국 사업자의 B2B 페인포인트를 수집·분류·대시보드로 제공하는 도구입니다.
네이버 지식인에서 키워드 검색 → OpenAI 분류 → Cloudflare D1 저장 → 대시보드 조회.

## Architecture

```
Naver KIN → Python Pipeline → Cloudflare D1 → Workers API → Dashboard
    (collect)     (classify)     (store)       (serve)       (UI)
```

- **Pipeline** (`collector/daily_run.py`): Python 3.14, 하루 1회 실행
- **API + Dashboard** (`workers/worker.js`): Cloudflare Workers, D1 바인딩

## Prerequisites

- Python 3.14+
- Node.js 22+
- Naver Open API client ID + secret ([Naver Developers](https://developers.naver.com/apps/#/register))
- OpenAI API key ([OpenAI Platform](https://platform.openai.com/api-keys))
- Cloudflare account + D1 database

## Setup

### 1. Python environment
```bash
pip install -e ".[dev]"    # Install dependencies including dev tools
```

### 2. Node.js environment
```bash
npm ci
```

### 3. Environment variables
```bash
cp .env.example .env
# Edit .env with your API keys:
#   NAVER_CLIENT_ID=your_naver_client_id
#   NAVER_CLIENT_SECRET=your_naver_client_secret
#   OPENAI_API_KEY=your_openai_api_key
#   D1_API_URL=https://dailypain.your-worker.workers.dev
#   D1_API_KEY=your_api_token
```

### 4. Worker secrets
```bash
echo "your-api-token" | npx wrangler secret put API_TOKEN
```

### 5. Database
```bash
npx wrangler d1 execute dailypain-db --remote --file=sql/create-tables.sql
npx wrangler deploy --config workers/wrangler.toml
```

## Usage

### Run the pipeline
```bash
python collector/daily_run.py
```
수집 → 분류 → D1 업로드가 순차 실행됩니다. 로그는 `data/dailypain.log`에 기록됩니다.

### Run tests
```bash
python -m pytest               # Python tests (-v for verbose)
npx vitest run                 # Worker tests
python -m pytest --cov         # With coverage report
```

### Lint
```bash
ruff check                     # Python lint
npx eslint workers/worker.js   # JS lint
```

### Deploy Worker
```bash
npm run deploy
```

## Project Structure

```
├── collector/
│   ├── daily_run.py       # Main pipeline (canonical)
│   ├── pipeline.py         # Alternative pipeline
│   └── keywords.json       # 42 Naver search keywords
├── workers/
│   ├── worker.js           # Worker entry point (API + UI)
│   └── wrangler.toml       # Worker configuration
├── sql/
│   └── create-tables.sql   # D1 DDL
├── tests/
│   ├── conftest.py         # Pytest fixtures
│   ├── test_daily_run.py   # Python unit tests
│   └── worker.test.js      # Worker unit tests
├── data/                   # Runtime artifacts (gitignored)
├── .env                    # Secrets (gitignored)
└── .dev.vars              # Local Worker secrets (gitignored)
```

## Logs

`data/dailypain.log` — 자동 로테이션 (5MB 제한, 3개 백업 보관)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Pipeline | Python 3.14.5 + openai SDK |
| API/UI | Cloudflare Workers (ES module) |
| Database | Cloudflare D1 (SQLite) |
| External APIs | Naver Open API, OpenAI Chat Completions |
| Testing | pytest, vitest |
| Lint | ruff, eslint |
| CI | GitHub Actions |
