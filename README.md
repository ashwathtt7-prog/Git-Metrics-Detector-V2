# Git Metrics Detector

An AI-powered tool that analyzes GitHub repositories to discover trackable metrics and automatically generates Apache Superset dashboards for visualization.

## Features

- **Repository Analysis**: Fetches and analyzes code from any public GitHub repository
- **Multi-Provider LLM Support**: Choose between Ollama (local), Google Gemini, OpenAI, or Anthropic
- **AI-Powered Metric Discovery**: Identifies business, engagement, content, performance, and growth metrics
- **LLM-Driven Dashboard Layout**: The LLM decides which chart types best represent your metrics
- **Automatic Superset Integration**: Creates multi-chart dashboards in Apache Superset automatically
- **Workspace Management**: Organizes discovered metrics into browsable workspaces with manual data entry

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Workflow UI    │────▶│   Backend API   │────▶│ Apache Superset │
│  (Port 3000)    │     │   (Port 8000)   │     │   (Port 8088)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
┌─────────────────┐            ▼
│  Dashboard UI   │     ┌─────────────────┐
│  (Port 3001)    │     │   LLM Provider  │
└─────────────────┘     │  (configurable) │
                        └─────────────────┘
```

### Analysis Pipeline

```
Git Repo URL
  │
  ▼
Pass 1 ─── Project Overview (tech stack, domain, architecture)
  │
  ▼
Pass 2 ─── Metrics Discovery (8-25 metrics per batch)
  │
  ▼
Pass 3 ─── Consolidation (if multi-batch, dedup + rank)
  │
  ▼
Pass 4 ─── Chart Suggestions (LLM picks best Superset chart types)
  │
  ▼
Workspace + Superset Dashboard created automatically
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- Git

**For local LLM (recommended for testing):**
- [Ollama](https://ollama.com/download) installed and running

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/ashwathtt7-prog/Git-metrics-detector.git
cd Git-metrics-detector
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### 3. Configure Your LLM Provider

Edit `backend/.env` — pick **one** provider:

#### Option A: Ollama (Recommended for testing — free, no rate limits)

```bash
# Install Ollama from https://ollama.com then pull a model:
ollama pull llama3.1:8b
```

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

#### Option B: Google Gemini

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
```

Get a key at https://aistudio.google.com/apikey

#### Option C: OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

#### Option D: Anthropic Claude

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

#### GitHub Token (optional but recommended)

Without a token, GitHub API limits you to 60 requests/hour. With one, you get 5,000/hour.

```env
GITHUB_TOKEN=your_github_token_here
```

Create one at https://github.com/settings/tokens (needs `repo` scope for private repos, or no scopes for public-only).

### 4. Frontend Setup

```bash
# Workflow frontend
cd frontend/workflow
npm install

# Dashboard frontend
cd ../dashboard
npm install
```

### 5. Apache Superset Setup (Optional)

Superset provides the auto-generated dashboards. If you skip this, the app still works — you just won't get Superset dashboards.

#### Windows (automated)

```bash
python setup_superset.py
```

#### Linux/Mac (manual)

```bash
# Create a separate venv for Superset
python -m venv superset_venv
source superset_venv/bin/activate

pip install apache-superset

# Create data directory
mkdir -p superset_data

# Set config path
export SUPERSET_CONFIG_PATH=$(pwd)/superset_config.py
export FLASK_APP=superset.app:create_app

# Initialize
superset db upgrade
superset fab create-admin \
  --username admin \
  --firstname Admin \
  --lastname User \
  --email admin@example.com \
  --password admin
superset init
```

Create `superset_config.py` in the project root:

```python
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = "your-secret-key-change-in-production"
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "superset_data", "superset.db").replace(os.sep, "/")

FAB_ADD_SECURITY_VIEWS = True
WTF_CSRF_ENABLED = False
ENABLE_CORS = True

CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["/api/*"],
    "origins": ["http://localhost:3001", "http://localhost:3000"],
}

FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "ENABLE_TEMPLATE_PROCESSING": True
}

TALISMAN_ENABLED = False
SESSION_COOKIE_SAMESITE = "Lax"
PREVENT_UNSAFE_DB_CONNECTIONS = False
```

## Running the Application

### Start All Services (Windows)

```bash
start.bat
```

### Start Services Individually

**Backend:**
```bash
cd backend
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

python -m uvicorn app.main:app --reload --port 8000
```

**Workflow Frontend:**
```bash
cd frontend/workflow
npm run dev
```

**Dashboard Frontend:**
```bash
cd frontend/dashboard
npm run dev
```

**Ollama** (if using local LLM):
```bash
ollama serve
# Ollama usually auto-starts on install, check with: ollama list
```

**Apache Superset** (optional):
```bash
# Windows:
start_superset.bat

# Linux/Mac:
export SUPERSET_CONFIG_PATH=$(pwd)/superset_config.py
source superset_venv/bin/activate
superset run -p 8088 --with-threads
```

## Usage

### 1. Analyze a Repository

1. Open http://localhost:3000
2. Enter a GitHub repository URL (e.g., `https://github.com/expressjs/express`)
3. Click "Analyze"
4. Wait for analysis to complete (progress shown in real-time)

### 2. View Discovered Metrics

1. Open http://localhost:3001 (Dashboard)
2. Click on a workspace to see discovered metrics
3. Each metric includes:
   - Name and description
   - Category (business, engagement, content, performance, growth)
   - Data type (number, percentage, boolean, string)
   - Suggested source in the codebase
4. Manually record metric values over time via the dashboard

### 3. Superset Dashboards

1. Open http://localhost:8088
2. Login with `admin` / `admin`
3. Navigate to Dashboards
4. Each analyzed repository gets its own dashboard with LLM-suggested charts:
   - Pie charts for category distribution
   - Bar charts for metric comparisons
   - Tables showing all metrics with details
   - Big number cards for key counts

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/workflow/analyze` | POST | Start repository analysis |
| `/api/workflow/jobs` | GET | List all analysis jobs |
| `/api/workflow/jobs/{id}` | GET | Get job status |
| `/api/workflow/jobs/{id}/metrics` | GET | Get discovered metrics |
| `/api/dashboard/workspaces` | GET | List all workspaces |
| `/api/dashboard/workspaces/{id}` | GET | Get workspace with metrics |
| `/api/dashboard/workspaces/{id}` | DELETE | Delete a workspace |
| `/api/dashboard/metrics/{id}/entries` | GET | Get metric entries |
| `/api/dashboard/metrics/{id}/entries` | POST | Add a metric entry |

## Project Structure

```
Git-metrics-detector/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application
│   │   ├── config.py                  # Settings (all providers configured here)
│   │   ├── database.py                # Async SQLite setup
│   │   ├── models.py                  # SQLAlchemy models
│   │   ├── routers/
│   │   │   ├── workflow.py            # Analysis endpoints
│   │   │   └── dashboard.py           # Dashboard endpoints
│   │   ├── services/
│   │   │   ├── providers/             # LLM provider abstraction
│   │   │   │   ├── base.py            # Abstract base + retry logic
│   │   │   │   ├── factory.py         # Provider factory (reads .env)
│   │   │   │   ├── ollama_provider.py
│   │   │   │   ├── gemini_provider.py
│   │   │   │   ├── openai_provider.py
│   │   │   │   └── anthropic_provider.py
│   │   │   ├── llm_service.py         # Prompts + JSON parsing
│   │   │   ├── analysis_service.py    # Orchestrates the full pipeline
│   │   │   ├── github_service.py      # GitHub API integration
│   │   │   ├── workspace_service.py   # Workspace CRUD
│   │   │   └── superset_service.py    # Superset dashboard creation
│   │   └── utils/
│   │       ├── file_filters.py        # File filtering + priority
│   │       └── token_estimator.py     # Batching for large repos
│   ├── data/                          # SQLite database (auto-created)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── workflow/                      # Analysis UI (port 3000)
│   └── dashboard/                     # Metrics dashboard (port 3001)
├── setup_superset.py                  # Superset auto-setup (Windows)
├── start.bat                          # Start all services (Windows)
├── start_superset.bat                 # Start Superset only (Windows)
└── README.md
```

## LLM Provider Comparison

| Provider | Rate Limits | Cost | Context Window | Best For |
|----------|-------------|------|----------------|----------|
| **Ollama** | None (local) | Free | Model-dependent (128k for llama3.1) | Local testing, demos |
| Gemini | 15 RPM (free tier) | Free tier available | 1M tokens | Large repos |
| OpenAI | Varies by tier | Pay-per-token | 128k (GPT-4o) | Production use |
| Anthropic | Varies by tier | Pay-per-token | 200k (Claude) | High-quality analysis |

### Ollama Model Recommendations

| Model | RAM Needed | Context | JSON Quality | Speed |
|-------|-----------|---------|-------------|-------|
| `llama3.1:8b` | ~5GB | 128k | Good | Fast |
| `mistral:7b` | ~5GB | 32k | Good | Fast |
| `qwen2.5:14b` | ~10GB | 128k | Excellent | Medium |
| `codellama:13b` | ~8GB | 16k | Good (code) | Medium |

## Troubleshooting

### Ollama Issues

- **Connection refused**: Make sure Ollama is running (`ollama serve` or check system tray)
- **Model not found**: Pull the model first: `ollama pull llama3.1:8b`
- **Slow responses**: Local models depend on your hardware. Use a smaller model or ensure GPU acceleration is enabled
- **Bad JSON output**: Some models struggle with structured output. Try `qwen2.5:14b` for better JSON

### GitHub Rate Limiting

- `403 Forbidden`: You've hit the GitHub API rate limit
- Without a token: 60 requests/hour
- With a token: 5,000 requests/hour
- Add `GITHUB_TOKEN` to your `.env` to fix this

### Gemini API Errors

- `API_KEY_INVALID`: Verify your key at https://aistudio.google.com/apikey
- `RESOURCE_EXHAUSTED`: Rate limit hit. The app retries with exponential backoff (10s, 20s, 40s...), but for heavy use switch to Ollama or a paid provider

### Superset Connection Issues

- Ensure Superset is running on port 8088
- Check that the database path in `superset_config.py` is correct
- Verify the `SUPERSET_URL` in backend `.env` matches
- Dashboard creation errors are non-blocking — analysis still completes

## License

MIT License
