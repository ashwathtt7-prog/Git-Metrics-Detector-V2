# Git Metrics Detector (Metabase Edition) - V2

Analyze any GitHub repository, discover trackable product/engineering metrics, generate realistic synthetic history, and automatically publish a Metabase dashboard for the results.

## Local URLs
- Workflow (Analyze + Generate Mock Data): `http://localhost:3001`
- Workspaces (Browse saved analyses): `http://localhost:3000`
- Backend API docs: `http://localhost:8001/docs`
- Metabase: `http://localhost:3003`

## Prerequisites
- Git
- Python 3.10+ (3.12+ recommended)
- Node.js 18+ (Node 20+ recommended)
- Java 21+ (required to run Metabase)

## Quickstart (2 commands)
### 1) Clone
```bash
git clone https://github.com/ashwathtt7-prog/Git-Metrics-Detector-V2.git
cd Git-Metrics-Detector-V2
```

### 2) Install (handles setup + prompts)
```bash
python install.py
```

`install.py` will:
- Create `backend/venv` + install backend deps
- Run `npm install` for `frontend/workflow` and `frontend/dashboard` (and `evidence/` if present)
- Download `backend/metabase.jar` (if missing)
- Prompt you for:
  - Service account JSON path (optional; copied to `backend/service-account.json`)
  - GitHub token (recommended; avoids rate limits)
  - Metabase admin email/password (or auto-generate a strong password)
- Optionally download a portable Java 21 into `backend/jdk-*` if Java 21+ is not detected

Non-interactive install:
```bash
python install.py --yes
```

### 3) Run
```bash
python run.py
```

Optional: run an automated end-to-end test (analyze -> mock data -> metabase) and exit:
```bash
python run.py --test
```

## Using the app (manual UI flow)
1) Open `http://localhost:3001`
2) Paste a repo URL (recommended test repo): `https://github.com/octocat/Hello-World`
3) Click **Analyze Repo** (you'll be taken to `/analysis/<jobId>` automatically)
4) After analysis completes, click **Generate Mock Data**
5) Click **Continue to Dashboard** (opens a public Metabase dashboard link)

You can also browse saved analyses at `http://localhost:3000`.

## How Metabase setup works
- On first run, Metabase may be "not set up yet".
- When you click **Generate Mock Data**, the backend will:
  - Detect Metabase is uninitialized
  - Auto-bootstrap it using `METABASE_USERNAME` / `METABASE_PASSWORD`
  - Authenticate and publish a dashboard

If you prefer manual setup, open `http://localhost:3003` once and complete the UI wizard, then restart the backend.

## Troubleshooting
### GitHub rate limit / "No readable files found in repository"
- Add a `GITHUB_TOKEN` in `backend/.env` or re-run `python install.py`
- You can also paste the token in the Workflow UI sidebar, then retry

### Metabase won't start
- Verify Java 21+: `java -version`
- No-admin option: unpack a portable JDK under `backend/jdk-*` (the runner auto-detects it)
- Ensure `backend/metabase.jar` exists

### "Metabase credentials not configured or authentication failed"
- Set `METABASE_USERNAME` and `METABASE_PASSWORD` in `backend/.env`
- Restart backend + retry **Generate Mock Data**
- If Metabase was set up with a different admin user/password, update `backend/.env` to match

### Ports already in use
Default ports:
- Backend `8001`, Workspaces `3000`, Workflow `3001`, Metabase `3003`

Stop the processes using those ports (or edit the Vite/Metabase port config).

## Security / secrets
Never commit these files:
- `backend/.env`
- `backend/service-account.json`
- `backend/metabase.jar`
- `backend/jdk-*`

They are ignored via `.gitignore`.
