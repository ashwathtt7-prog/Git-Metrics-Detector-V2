# Project context: Git Metrics Detector (Metabase Edition)

This document explains what the project is, how it’s structured, and how the end-to-end workflow works. It is intended for maintainers and contributors.

## What this project does
- Takes a GitHub repository URL.
- Uses an LLM to infer a project overview and a list of trackable metrics.
- Creates a Workspace (a saved analysis + metric registry).
- Generates realistic synthetic time-series values (mock data) so charts look meaningful immediately.
- Creates a Metabase dashboard (public link) to visualize the workspace.

## High-level workflow (end-to-end)
1. **Workflow UI** (`frontend/workflow`, port 3001)
   - User pastes a GitHub repo URL and starts analysis.
   - UI polls job status and streams job logs.
2. **Backend** (`backend/app`, port 8001)
   - Fetches repo tree + selected key files from GitHub.
   - Runs analysis passes (overview → batch metric discovery → consolidation).
   - Writes results into SQLite (`backend/data/metrics.db`).
3. **Mock data generation**
   - Generates 24–32 daily-ish points per metric (last ~30 days).
   - Has deterministic fallback generators that produce metric-specific variability (error spikes, cache dips, noisy latency, seasonality, etc.).
4. **Metabase dashboard creation** (`backend/app/services/metabase_service.py`, Metabase on port 3003)
   - Registers the SQLite DB in Metabase (once).
   - Creates a dashboard and cards from an LLM “dashboard plan”.
   - Ensures public sharing is enabled and returns a shareable URL.

## Components (folders)
- `backend/`
  - FastAPI app + analysis pipeline
  - SQLite DB stored at `backend/data/metrics.db` (local dev)
  - Metabase helper scripts (optional)
- `frontend/workflow/` (port 3001)
  - “Analyze repo” UI + stage timeline + logs + mock-data + “Continue to Dashboard”
- `frontend/dashboard/` (port 3000)
  - “Workspaces” UI: list analyzed repos and link to their Metabase dashboard URLs
- `evidence/` (optional)
  - Extra analytics/reporting playground (not required for core flow)

## Ports
- Backend: `8001`
- Workflow UI: `3001`
- Workspaces UI: `3000`
- Metabase: `3003`

## Analysis stages (what the user sees)
The backend stores a job log list (timestamped strings). The UI groups logs by stage tags like `[S3/P2/B4/LLM]`.

- Stage 1: Repo structure scan
  - Fetches file tree; emits “signals” based on paths.
- Stage 2: Fetch key files
  - Fetches the highest-priority source files for deep analysis.
- Stage 3: Extract metrics (multi-pass + batching)
  - Pass 1: project overview (domain/stack)
  - Pass 2: batch scanning for metric candidates (with trace: observations, criteria, files referenced)
  - Important: if an LLM call fails for a batch, the pipeline falls back to path-only inference and/or deterministic heuristics so the batch is not silently “skipped”.
- Stage 4: Consolidate
  - Deduplicates and ranks metrics; logs merge/drop reasons.
- Stage 5: Workspace + visualization
  - Creates workspace + stores metric registry
  - Generates mock time-series
  - Creates Metabase dashboard + stores `metabase_url` into the workspace config

## Database schema (SQLite)
Tables used by the app:
- `workspaces`
  - `dashboard_config` stores JSON like `{ "metabase_url": "...", "plan": {...}, "trace": {...} }`
- `metrics`
  - Metric definitions: name/category/data_type/suggested_source etc.
- `metric_entries`
  - Synthetic or real metric time-series values (stored as strings, cast to numeric in queries)
- `analysis_jobs`
  - Track status/progress/logs for each analysis run

## Metabase integration notes
The backend uses Metabase’s API:
- Auth: `POST /api/session` with `METABASE_USERNAME` / `METABASE_PASSWORD`
- DB registration: `GET/POST /api/database`
- Dashboard creation: `POST /api/dashboard`
- Card creation: `POST /api/card`
- Add cards to dashboard: `PUT /api/dashboard/:id/cards`
- Public link: `POST /api/dashboard/:id/public_link`

LLM plans sometimes contain placeholders like `{workspace_id}` in SQL. The Metabase service patches those values and also falls back to a known-good set of cards if the planned cards fail to create, preventing empty dashboards.

## Configuration & secrets
Config is loaded from `backend/.env` (ignored by git):
- LLM provider keys and/or Gemini service account path
- GitHub token (optional)
- Metabase credentials

Never commit:
- `backend/.env`
- `backend/service-account.json`

## “No admin access” goal
The project avoids needing admin rights by:
- Using user-space Python venv + npm installs
- Using only unprivileged ports
- Running Metabase via `java -jar` (portable Java is supported)

## Common troubleshooting
- **Metabase dashboard is empty**: usually card creation failed (SQL error or missing workspace_id filter). The backend falls back to safe cards; re-generate mock data and retry “Continue to Dashboard”.
- **LLM batch failures / empty responses**: long prompts can cause provider issues. The backend truncates file content per file and falls back deterministically if providers fail.
- **Fresh start**: run `backend/reset_db.py` to delete all jobs/workspaces/metrics/entries.
