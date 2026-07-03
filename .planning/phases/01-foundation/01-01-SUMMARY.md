---
phase: 01-foundation
plan: 01
wave: 1
subsystem: foundation
tags:
  - schema
  - reproducibility
  - portability
  - cleanup
requires: []
provides:
  - sql/create-tables.sql (date + starred columns)
  - requirements.txt (openai dependency)
  - pyproject.toml (build config + pip install -e . support)
  - package.json (wrangler devDependency)
  - .python-version (3.14.5 pin)
  - collector/daily_run.py (no absolute paths)
affects:
  - sql/create-tables.sql
  - collector/daily_run.py
tech-stack:
  added:
    - "requirements.txt → openai>=1.0.0"
    - "pyproject.toml → setuptools build_meta"
    - "package.json → wrangler@^4.94.0"
    - ".python-version → 3.14.5"
  patterns:
    - "pathlib.Path(__file__).resolve() for relative path resolution"
key-files:
  created:
    - requirements.txt
    - pyproject.toml
    - package.json
    - .python-version
  modified:
    - sql/create-tables.sql
    - collector/daily_run.py
  removed:
    - collector/collect.py
    - collector/collect_v2.py
    - collector/classify.py
    - collector/classify_v2.py
    - collector/upload_d1.py
    - collector/make_sql.py
    - backup3.py
    - backup_20260307_141200.txt
decisions:
  - "wrangler version corrected from STACK.md's 11.6.2 to 4.94.0 (npm latest compatible)"
  - "pyproject.toml build backend changed from setuptools.backends._legacy to setuptools.build_meta (not available in current setuptools)"
  - "pyproject.toml added [tool.setuptools.packages.find] include collector* to avoid flat-layout conflict"
metrics:
  duration_minutes: 5
  completed_date: "2026-07-03"
---

# Phase 01 Plan 01: Foundation — Reproducibility, Portability, Schema-Correctness

Made the DailyPain project reproducible, portable, and schema-correct. Added missing DDL columns, created Python and Node.js dependency manifests, removed redundant collector scripts and backup artifacts, and replaced hardcoded absolute paths in the canonical pipeline entry point.

## Tasks Executed

### Task 1: Fix D1 schema — add `date` and `starred` columns
- **File:** `sql/create-tables.sql`
- Added `date TEXT NOT NULL DEFAULT ''` after `source_url TEXT UNIQUE`
- Added `starred BOOLEAN DEFAULT 0` before `created_at`
- Added `CREATE INDEX IF NOT EXISTS idx_pain_starred ON pain_points(starred)` after `idx_pain_date`
- Schema now matches what `worker.js` and `daily_run.py` actually use

### Task 2: Create dependency manifests
- **`requirements.txt`** — declares `openai>=1.0.0`
- **`pyproject.toml`** — setuptools build config with `pip install -e .` support
- **`package.json`** — wrangler devDependency with `deploy`, `dev`, `d1:execute` scripts
- **`.python-version`** — pins Python to `3.14.5`

### Task 3: Consolidate collector scripts and remove backup artifacts
- `git rm` removed 6 redundant collector scripts (`collect.py`, `collect_v2.py`, `classify.py`, `classify_v2.py`, `upload_d1.py`, `make_sql.py`)
- Deleted 2 backup artifacts (`backup3.py`, `backup_20260307_141200.txt`) from disk (not git-tracked)
- Only `daily_run.py`, `pipeline.py`, `keywords.json` remain in `collector/`

### Task 4: Remove hardcoded absolute paths from `daily_run.py`
- Replaced 3 absolute `/Users/twinssn/Projects/dailypain` paths with `Path(__file__).resolve()` relative resolution
- Paths fixed: `.env` loading (line 10), `data_dir` (line 20), `cwd` for wrangler subprocess (line 157)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] wrangler version mismatch in package.json**
- **Found during:** Task 2 verification (npm install failed)
- **Issue:** STACK.md documented wrangler@11.6.2, but npm only has wrangler up to 4.107.0. The version `^11.6.2` in package.json caused `npm install --package-lock-only` to fail with ETARGET.
- **Fix:** Changed to `^4.94.0` — matches the globally-installed wrangler version (`npx wrangler --version` returns 4.94.0).
- **Files modified:** `package.json`

**2. [Rule 3 — Blocking] pyproject.toml build backend not available**
- **Found during:** `pip install -e . --dry-run` verification
- **Issue:** `setuptools.backends._legacy:_Backend` does not exist in current setuptools. Also, flat-layout discovery conflicted with multiple top-level directories (`sql/`, `data/`, `workers/`, `collector/`).
- **Fix:** Changed build-backend to `setuptools.build_meta`, added `[tool.setuptools.packages.find] include = ["collector*"]`.
- **Files modified:** `pyproject.toml`

## Verification Results

| # | Check | Result |
|---|-------|--------|
| 1 | Schema: `date TEXT` (1 match in pain_points) | ✅ PASS (2 total including daily_stats) |
| 2 | Schema: `starred BOOLEAN` | ✅ PASS |
| 3 | Schema: `idx_pain_starred` | ✅ PASS |
| 4 | Manifests: requirements.txt, package.json, .python-version | ✅ PASS |
| 5 | No absolute paths in daily_run.py | ✅ PASS (0 matches) |
| 6 | Redundant scripts removed | ✅ PASS |
| 7 | Backup artifacts removed | ✅ PASS |
| 8 | Canonical scripts preserved | ✅ PASS |
| 9 | Python deps resolvable (pip install -r) | ✅ PASS (dry-run) |
| 10 | Node deps installable (npm install --package-lock-only) | ✅ PASS |
| 11 | pip install -e . works | ✅ PASS (dry-run) |
| 12 | wrangler deploy --dry-run validates | ✅ PASS |

## Success Criteria Checklist

- [x] `sql/create-tables.sql` declares `date TEXT NOT NULL DEFAULT ''` and `starred BOOLEAN DEFAULT 0` columns
- [x] `sql/create-tables.sql` has `CREATE INDEX IF NOT EXISTS idx_pain_starred`
- [x] `requirements.txt` exists with `openai>=1.0.0`
- [x] `package.json` exists with wrangler devDependency and `"deploy"` script
- [x] `.python-version` contains `3.14.5`
- [x] No hardcoded `/Users/twinssn/Projects/dailypain` paths remain in `collector/daily_run.py`
- [x] `collector/` contains only `daily_run.py`, `pipeline.py`, and `keywords.json`
- [x] `backup3.py` and `backup_20260307_141200.txt` are removed from the repo/disk
- [x] `pip install -e .` succeeds (via pyproject.toml)
- [x] `npm install --package-lock-only` validates package.json
- [x] `npx wrangler deploy --dry-run` validates successfully

## Self-Check: PASSED

All files verified:
- `sql/create-tables.sql` — exists, 33 lines, contains date+starred+index
- `requirements.txt` — exists, 1 line, contains `openai`
- `pyproject.toml` — exists, 15 lines, valid TOML
- `package.json` — exists, valid JSON, contains `wrangler`
- `.python-version` — exists, contains `3.14.5`
- `collector/daily_run.py` — exists, 166 lines, zero absolute paths
- `collector/pipeline.py` — exists, preserved
- `collector/keywords.json` — exists, preserved
- All 6 redundant scripts: confirmed deleted
- Both backup artifacts: confirmed deleted
