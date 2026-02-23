# Git Metrics Detector (Metabase Edition)

AI-powered repo analysis that discovers trackable metrics and generates realistic synthetic history, then builds a Metabase dashboard automatically.

## No-admin guarantee (important)
This project is designed to run without administrator access:
- Python runs inside a virtual environment (user-space)
- Node.js runs normally (user-space)
- Metabase runs via `java -jar` (you can use an existing Java install or a portable JDK ZIP; no system install required)
- Uses only unprivileged ports (3000/3001/3003/8001)

If you’re on locked-down hardware:
- Use a user-level Python install (e.g., Microsoft Store Python on Windows) and create the venv normally.
- Use a portable Node.js ZIP distribution (no installer) if you can’t install Node globally.
- Use a portable JDK ZIP for Metabase if you can’t install Java globally.

## User flow
1. Open the Workflow app: `http://localhost:3001`
2. Paste a GitHub repo URL → **Analyze Repo**
3. Review discovered metrics → **Generate Mock Data**
4. Click **Continue to Dashboard** → opens the workspace dashboard in Metabase
5. Use the Workspaces app (`http://localhost:3000`) to browse all analyzed repos and open their Metabase links

## Services / ports
- Workflow UI (start here): `http://localhost:3001`
- Workspaces UI: `http://localhost:3000`
- Backend API: `http://localhost:8001/docs`
- Metabase: `http://localhost:3003`

## Prerequisites
- Python 3.9+
- Node.js 18+
- Git
- Java 11+ (only for Metabase; can be portable/non-admin)

## Metabase binary (required for dashboards)
This repo does not commit Metabase binaries. To enable automatic dashboard creation:
1. Download `metabase.jar` from https://www.metabase.com/start/
2. Place it at `backend/metabase.jar`

`start_all.bat` / `start.sh` will skip Metabase if the jar isn’t present.

## Quick start (Windows)
1. Clone
   - `git clone https://github.com/ashwathtt7-prog/Git-metrics-detector.git`
   - `cd Git-metrics-detector`
2. Configure backend env
   - Copy `backend/.env.example` → `backend/.env`
   - Fill your LLM provider keys OR set `GEMINI_SERVICE_ACCOUNT_FILE` (Vertex service account)
   - Set `METABASE_USERNAME` / `METABASE_PASSWORD` to match the Metabase admin user you will create
3. Install deps (first time only)
   - Backend:
     - `cd backend`
     - `python -m venv venv`
     - `venv\Scripts\activate`
     - `pip install -r requirements.txt`
   - Frontend:
     - `cd ..\frontend\workflow` → `npm install`
     - `cd ..\dashboard` → `npm install`
4. Start everything
   - `start_all.bat` (backend + both UIs + Metabase)
   - Or `start.bat` (backend + both UIs; run Metabase separately)

## Quick start (macOS/Linux)
1. Clone and configure `backend/.env` like above.
2. Run `./start.sh`
   - Starts backend (8001), workflow (3001), workspaces (3000)
   - Starts Metabase only if `backend/metabase.jar` exists and `java` is available

## Metabase setup (first run)
1. Start Metabase (port 3003)
2. Open `http://localhost:3003` and complete the initial setup wizard
3. Create an admin user with the same email/password you set in `backend/.env`
4. Re-run **Generate Mock Data** → the backend will create a shareable dashboard URL

## Secrets & service accounts (read this before sharing the repo)
This repository intentionally does **not** contain any credentials.

- `backend/.env` is **local-only** and is ignored by git.
  - On a new machine, you must create it by copying `backend/.env.example` → `backend/.env`.
  - If you hand this repo to another person (or an LLM), they must ask you for the correct values to put in `backend/.env`.
- `backend/service-account.json` (Gemini Vertex service account) is **local-only** and is ignored by git.
  - If you want to use a Gemini service account, place the JSON file at `backend/service-account.json`
  - Then set in `backend/.env`:
    - `GEMINI_SERVICE_ACCOUNT_FILE=service-account.json`

Never commit:
- `backend/.env`
- `backend/service-account.json`

## Reset / fresh start
To remove all analyzed repos/workspaces from the app DB:
- `cd backend`
- `venv\Scripts\python.exe reset_db.py`

## Secrets safety
- Never commit `backend/.env` or any service account JSON (they’re ignored by `.gitignore`).

## More details
- See `PROJECT_CONTEXT.md` for architecture, API surface, database schema, and troubleshooting.
