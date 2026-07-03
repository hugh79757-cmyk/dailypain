# DailyPain — Roadmap

**Goal:** Stabilize existing codebase for production readiness
**Phases:** 3

---

## Phase 1: 기반정비 (Foundation)

**Theme:** Make the project reproducible, portable, and schema-correct

### Tasks
1. Create `pyproject.toml` (or `requirements.txt`) with all Python deps
2. Create `package.json` for Workers tooling
3. Remove hardcoded absolute paths → use `Path(__file__).resolve()` patterns
4. Fix `sql/create-tables.sql` — add `date` and `starred` columns
5. Consolidate collector scripts: remove v1/v2 duplicates, keep `pipeline.py` or `daily_run.py` as canonical
6. Remove `backup3.py`, `backup_20260307_141200.txt` from repo
7. Add `.python-version` for runtime enforcement

**Success Criteria:** `pip install -e .` succeeds; `npx wrangler deploy` works; schema file matches actual D1 table

---

## Phase 2: 보안 + 안정성 (Security & Reliability)

**Theme:** Eliminate security holes and make the pipeline resilient

### Tasks
1. Replace all f-string SQL with parameterized queries/prepared statements
   - `workers/worker.js` (use `?` placeholders)
   - `collector/upload_d1.py`, `collector/make_sql.py`, `collector/daily_run.py`
2. Add authentication to Worker API (shared secret or Cloudflare Access)
3. Replace manual `.env` parsing with `os.environ` / python-dotenv
4. Add retry with exponential backoff for Naver API + OpenAI calls
5. Validate OpenAI response JSON structure before indexing
6. Handle malformed AI responses gracefully (log + skip, don't crash)
7. Narrow/remove wildcard CORS headers
8. Fix stub endpoints (`/auth/callback`, `/deauth`, `/data-deletion`) or remove them
9. Move `database_id` from `wrangler.toml` to secrets

**Success Criteria:** No SQL injection vectors; all POST endpoints require auth; pipeline recovers from API failures; no crash on malformed AI response

---

## Phase 3: 테스트 + 정리 (Testing & Cleanup)

**Theme:** Add automated quality gates and final polish

### Tasks
1. Set up test frameworks: `pytest` for Python, `vitest` for Workers
2. Write unit tests for:
   - `classify_batch()` response parsing (regression test for the `AttributeError` crash)
   - SQL generation functions
   - Worker route handlers
   - Naver API response normalization
3. Set up GitHub Actions CI (run tests on push/PR)
4. Add lint config: `ruff` (Python), `eslint` (JS)
5. Add `AGENTS.md` for LLM context
6. Add `README.md` with setup/run instructions
7. Configure log rotation for `data/dailypain.log`
8. Remove unused `daily_stats` table writes (or implement them)

**Success Criteria:** `pytest` passes with ≥70% coverage; CI passes on every PR; lint passes cleanly

---

## Future Opportunities (post-stabilization)

- Additional data sources (blog, cafe, community)
- Real-time alerts on high-pain-score items
- User authentication (multi-tenant)
- Dashboard UX improvements
- Korean PIPA compliance audit
