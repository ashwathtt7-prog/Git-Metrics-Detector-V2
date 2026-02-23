# How to Install and Run Git Metrics Detector (Metabase Edition)

This guide sets up and runs the Git Metrics Detector application (backend + two UIs + Metabase).

## Prerequisites
- Python 3.9+
- Node.js 18+
- Git
- Java 11+ (for Metabase; can be portable/non-admin)

## Metabase jar
Download `metabase.jar` from https://www.metabase.com/start/ and place it at `backend/metabase.jar`.

## 1) Backend setup
```bash
cd backend
python -m venv venv
```

Activate:
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

Install deps:
```bash
pip install -r requirements.txt
```

Config:
- Copy `backend/.env.example` → `backend/.env`
- Fill your LLM keys (or set `GEMINI_SERVICE_ACCOUNT_FILE`)
- Set Metabase creds (`METABASE_USERNAME` / `METABASE_PASSWORD`)

## 2) Frontend setup
```bash
cd frontend/workflow
npm install
cd ../dashboard
npm install
```

## 3) Start everything
- Windows: `start_all.bat`
- macOS/Linux: `./start.sh` (starts Metabase only if `backend/metabase.jar` exists and `java` is available)

## 4) URLs
- Workflow (start here): http://localhost:3001
- Workspaces: http://localhost:3000
- Backend API: http://localhost:8001/docs
- Metabase: http://localhost:3003
