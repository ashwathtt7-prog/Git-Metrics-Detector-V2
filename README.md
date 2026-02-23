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

## Step-by-step (from scratch)
### 1) Clone
```bash
git clone https://github.com/ashwathtt7-prog/Git-Metrics-Detector-V2.git
cd Git-Metrics-Detector-V2
```

### 2) Create `backend/.env`
Copy the template:
- `backend/.env.example` -> `backend/.env`

Minimum settings (to "definitely work"):
- LLM:
  - Set `LLM_PROVIDER=gemini` and configure one of the Gemini options below (recommended), OR
  - Use `LLM_PROVIDER=ollama` and ensure Ollama is running locally.
- Metabase (needed for dashboards):
  - `METABASE_URL=http://localhost:3003`
  - `METABASE_USERNAME=...`
  - `METABASE_PASSWORD=...` (use a strong password)
- GitHub token (strongly recommended):
  - `GITHUB_TOKEN=...` (avoids GitHub rate-limit failures)

Gemini option A (Vertex via service account):
1) Put your service account JSON at `backend/service-account.json`
2) Set:
   - `LLM_PROVIDER=gemini`
   - `GEMINI_SERVICE_ACCOUNT_FILE=service-account.json`
   - (optional) `GEMINI_MODEL=gemini-2.0-flash`

Gemini option B (AI Studio API key):
- `LLM_PROVIDER=gemini`
- `GEMINI_API_KEY=...`

### 3) Download Metabase (jar)
This repo does not commit Metabase binaries. Download to `backend/metabase.jar`.

- PowerShell (Windows):
  ```powershell
  Invoke-WebRequest -Uri "https://downloads.metabase.com/latest/metabase.jar" -OutFile "backend\\metabase.jar"
  ```
- macOS/Linux:
  ```bash
  curl -L "https://downloads.metabase.com/latest/metabase.jar" -o backend/metabase.jar
  ```

### 4) Start the stack
The start scripts auto-create the Python venv, install backend deps, and install frontend packages on first run.

Windows:
- `start_all.bat` (backend + both UIs + Metabase)
- `start.bat` (backend + both UIs + Evidence; no Metabase)

macOS/Linux:
```bash
./start.sh
```

If Metabase is already running elsewhere, set `METABASE_URL` accordingly.

### 5) Run an end-to-end analysis
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
- Set `GITHUB_TOKEN` in `backend/.env` (recommended)
- Or paste the token in the Workflow UI sidebar, then retry

### Metabase won't start
- Verify Java 21+: `java -version`
- Windows (no-admin): unpack a portable JDK under `backend/jdk-*` (the scripts auto-detect `backend/jdk-*/bin/java.exe`)
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
