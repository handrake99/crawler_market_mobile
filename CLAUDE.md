# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 응답 언어 지침

모든 결과값과 설명은 **반드시 한글**로 작성한다. 코드, 명령어, 파일명 등 기술적 식별자는 영문 그대로 유지하되, 설명 텍스트는 예외 없이 한글로 작성한다.

## Project Overview

An AI-powered iOS app market research automation tool. It scrapes the iTunes App Store, uses Google Gemini to filter promising niche apps, and presents results through a web dashboard. The pipeline can run on a daily cron schedule or be manually triggered via UI.

## Commands

All commands run from `app_market_agent/` using the local venv:

```bash
# Start the web server (dashboard at http://localhost:9000)
cd app_market_agent && ./.venv/bin/python server.py

# Run the full analysis pipeline manually
cd app_market_agent && ./.venv/bin/python main.py

# Quick pipeline test with a single keyword
cd . && ./.venv/bin/python test_pipeline.py
```

Install dependencies (if venv is missing):
```bash
cd app_market_agent
python3 -m venv .venv
./.venv/bin/pip install fastapi uvicorn sqlalchemy pydantic google-generativeai requests python-dotenv google-play-scraper
```

## Architecture

### Data Flow

**Automated pipeline (`main.py` → `AppMarketAgent.run()`):**
1. `store_scraper.py` → searches iTunes API with 3 random niche keywords, returns up to 40 candidate apps
2. `ai_analyzer.py` → Gemini 2.5 Flash evaluates each app on 3 criteria: niche market, revenue model, simplicity (feasible for 1-2 devs); approved apps stored
3. Results persisted in SQLite as `RunHistory` + `AppItem` records
4. Email report sent via SMTP

**On-demand deep analysis (`server.py` → `/api/collect_detail`):**
1. `store_scraper.py` fetches 1–3 star and 5-star reviews from iTunes RSS
2. `ai_analyzer.py` extracts pain points, satisfaction points, requested features per country (US/KR)
3. Results stored in `AppDetail` (one-to-one with `AppItem`)

### Key Files

| File | Role |
|------|------|
| `app_market_agent/main.py` | Pipeline orchestration entry point |
| `app_market_agent/server.py` | FastAPI backend + all REST endpoints |
| `app_market_agent/index.html` | Vue.js 3 SPA frontend (single file, ~1000 lines) |
| `app_market_agent/models.py` | SQLAlchemy ORM: `RunHistory`, `AppItem`, `AppDetail` |
| `app_market_agent/store_scraper.py` | iTunes Search API + RSS review scraper |
| `app_market_agent/ai_analyzer.py` | Gemini API calls with 4s rate-limit delays |
| `app_market_agent/database.py` | SQLite connection (`app_market.db`) |

### Database Schema

- `RunHistory` — one record per pipeline run, stores console log output
- `AppItem` — apps found per run, includes multi-region JSON in `country_data`, AI evaluation reasons, `is_favorite`/`is_hidden` flags
- `AppDetail` — deep review analysis results (per-country reviews + AI extraction), one-to-one with `AppItem`

### Frontend

Vue.js 3 via CDN (no build step). Two main views:
- **Run History tab**: lists past pipeline runs; click a run to see its apps and logs
- **All Apps tab**: filterable list of all discovered apps with search, favorite/hide filters

App detail modal shows metadata, multi-country stats, and deep review analysis (triggered on demand).

### Environment

Requires `app_market_agent/.env`:
```
GEMINI_API_KEY=...
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=...
SENDER_PASSWORD=...
```

### Niche Keywords

Defined in `main.py` as a Python list (`NICHE_KEYWORDS`). 3 random keywords are selected per pipeline run to vary the search results. Adding new app categories = add keywords here.
