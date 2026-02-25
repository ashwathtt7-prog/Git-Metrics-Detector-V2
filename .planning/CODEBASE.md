# Codebase Map: Git Metrics Detector

**Mapped:** 2026-02-25
**Stack:** Python (FastAPI) + React (Vite) + SQLite + Metabase + Google Gemini LLM

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Git Metrics Detector                                            │
├────────────────┬────────────────┬────────────────┬──────────────┤
│  Workflow UI   │  Workspaces UI │  Visualization │   Metabase   │
│  :3001         │  :3000         │  (embedded)    │   :3003      │
│  React+Vite    │  React+Vite    │  React+Vite    │   Java       │
├────────────────┴────────────────┴────────────────┴──────────────┤
│  Backend API  :8001                                              │
│  FastAPI + Uvicorn                                               │
├──────────────────────────────────────────────────────────────────┤
│  SQLite (backend/data/metrics.db)                                │
│  Tables: workspaces, metrics, metric_entries, analysis_jobs      │
└──────────────────────────────────────────────────────────────────┘
          │                    │
          ▼                    ▼
   GitHub API            Google Gemini LLM
   (repo tree/files)     (analysis pipeline)
```

## Directory Structure

```
Git-metrics-detector/
├── backend/
│   ├── app/                    # FastAPI application
│   │   ├── main.py             # App entry point, CORS, routes
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── database.py         # DB connection setup
│   │   ├── routes/             # API route handlers
│   │   ├── services/           # Business logic
│   │   │   ├── analysis_service.py    # LLM analysis pipeline
│   │   │   ├── metabase_service.py    # Metabase API integration
│   │   │   ├── github_service.py      # GitHub API client
│   │   │   └── mock_data_service.py   # Synthetic data generation
│   │   └── utils/              # Shared utilities
│   ├── data/                   # SQLite DB storage
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment template
│   └── test_*.py               # Various test scripts
├── frontend/
│   ├── workflow/               # Analysis workflow UI (:3001)
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.js
│   ├── dashboard/              # Workspaces browser UI (:3000)
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.js
│   └── visualization/          # Embedded viz components
├── Install.bat / install.py    # Setup automation
├── Run.bat / run.py            # Service launcher
├── PROJECT_CONTEXT.md          # Original project documentation
└── README.md                   # User-facing docs
```

## Key Patterns

### Analysis Pipeline (5 stages)
1. **Repo Structure Scan** — Fetch GitHub tree, emit signals from paths
2. **Fetch Key Files** — Download priority source files for analysis
3. **Extract Metrics** — Multi-pass LLM: overview → batch scanning → candidates
4. **Consolidate** — Deduplicate, rank, merge metrics
5. **Workspace + Dashboard** — Create workspace, generate mock data, publish Metabase dashboard

### Error Handling
- LLM failures → deterministic fallback generators
- Malformed JSON → partial recovery attempts
- Metabase card failures → known-good card fallback set
- GitHub rate limits → token-based authentication support

### Data Flow
```
GitHub Repo URL
  → GitHub API (tree + files)
  → LLM Pass 1 (overview)
  → LLM Pass 2 (batch metric discovery)
  → Consolidation
  → SQLite (workspace + metrics)
  → Mock Data Generator
  → Metabase Dashboard API
  → Public Dashboard URL
```

## Conventions

- **Backend routes**: RESTful, `/api/v1/` prefix
- **Frontend state**: React hooks + polling for job status
- **Config**: `.env` files for secrets, never committed
- **Batch scripts**: Entry point for Windows users, call Python scripts
- **Database**: Single SQLite file, auto-created on first run
- **Ports**: Backend 8001, Workspaces 3000, Workflow 3001, Metabase 3003

## Known Technical Debt

1. LLM JSON parsing is fragile — needs structured output or better recovery
2. Mock data generators could share more temporal patterns
3. Some test files in `backend/` are ad-hoc scripts, not proper test suites
4. `evidence/` directory is optional/experimental, unclear purpose
5. Frontend components could be shared between workflow and dashboard apps
