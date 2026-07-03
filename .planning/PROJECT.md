# DailyPain — Project Context

**Initialized:** 2026-07-03
**Status:** Brownfield (codebase exists, no GSD structure)
**Priority:** Stabilization-first

## Purpose

DailyPain collects B2B pain points from Naver Knowledge iN, classifies them via OpenAI, and serves a searchable dashboard through Cloudflare Workers + D1. The goal is to identify recurring business problems that can be addressed with software solutions.

## Current State (from codebase map)

- **Data Pipeline** (Python 3.14): Collects Naver Knowledge iN posts, classifies with OpenAI (GPT-5-nano/GPT-4o-mini), uploads to D1
- **API Server** (Cloudflare Workers JS): Serves pain points via HTTP with embedded HTML dashboard
- **Database** (Cloudflare D1): `pain_points` and `daily_stats` tables
- **Key Issues:** No tests, no dependency manifests, hardcoded paths, schema mismatch, SQL injection risk, no auth, duplicated scripts

## Stack

| Component | Technology |
|-----------|-----------|
| Pipeline | Python 3.14.5 (stdlib + openai SDK) |
| API/UI | Cloudflare Workers (ES module) |
| Database | Cloudflare D1 (SQLite-compatible) |
| External APIs | Naver Open API, OpenAI Chat Completions |
| Tooling | wrangler 11.6.2, npx |

## Workflow Preferences

- **Mode:** Interactive (대화형)
- **Research:** Skip (codebase map sufficient)
- **Domain:** B2B pain point collection, Korean market
