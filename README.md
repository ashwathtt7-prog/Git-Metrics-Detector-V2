# Git Metrics Detector

An AI-powered tool that analyzes GitHub repositories to discover trackable metrics and automatically generates Superset dashboards for visualization.

## Features

- **Repository Analysis**: Fetches and analyzes code files from any public GitHub repository
- **AI-Powered Metric Discovery**: Uses Google Gemini to identify business, engagement, content, performance, and growth metrics
- **Workspace Management**: Organizes discovered metrics into workspaces
- **Automatic Superset Integration**: Creates dashboards and charts in Apache Superset automatically

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Workflow UI    │────▶│   Backend API   │────▶│  Apache Superset│
│  (Port 3000)    │     │   (Port 8000)   │     │   (Port 8088)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Google Gemini  │
                        │      API        │
                        └─────────────────┘
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- Git

## Setup

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

Edit `.env` with your API keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GITHUB_TOKEN=your_github_token_here
DATABASE_URL=sqlite+aiosqlite:///./data/metrics.db

SUPERSET_URL=http://localhost:8088
SUPERSET_USERNAME=admin
SUPERSET_PASSWORD=admin
```

**Getting API Keys:**
- **Gemini API Key**: https://aistudio.google.com/apikey
- **GitHub Token**: https://github.com/settings/tokens (create a Personal Access Token with `repo` scope)

### 3. Frontend Setup

```bash
# Workflow frontend
cd frontend/workflow
npm install

# Dashboard frontend
cd ../dashboard
npm install
```

### 4. Apache Superset Setup

```bash
# Create virtual environment for Superset
python -m venv superset_venv

# Activate virtual environment
# Windows:
superset_venv\Scripts\activate
# Linux/Mac:
source superset_venv/bin/activate

# Install Superset
pip install apache-superset

# Install additional dependencies
pip install flask-cors google-auth pillow
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

FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "ENABLE_TEMPLATE_PROCESSING": True
}

TALISMAN_ENABLED = False
SESSION_COOKIE_SAMESITE = "Lax"
```

Initialize Superset:

```bash
# Create data directory
mkdir superset_data

# Initialize database
set SUPERSET_CONFIG_PATH=%CD%\superset_config.py
set FLASK_APP=superset.app:create_app
superset db upgrade

# Create admin user
superset fab create-admin --username admin --firstname Admin --lastname User --email admin@example.com --password admin

# Initialize
superset init
```

## Running the Application

### Start Backend

```bash
cd backend
venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Start Workflow Frontend

```bash
cd frontend/workflow
npm run dev
```

### Start Dashboard Frontend

```bash
cd frontend/dashboard
npm run dev
```

### Start Apache Superset

```bash
set SUPERSET_CONFIG_PATH=%CD%\superset_config.py
set FLASK_APP=superset.app:create_app
superset run -p 8088 --with-threads
```

## Usage

### 1. Analyze a Repository

1. Open http://localhost:3000
2. Enter a GitHub repository URL (e.g., `https://github.com/expressjs/express`)
3. Click "Analyze"
4. Wait for analysis to complete (progress shown in real-time)

### 2. View Results

1. Open http://localhost:3001 (Dashboard)
2. Click on a workspace to see discovered metrics
3. Each metric includes:
   - Name and description
   - Category (business, engagement, content, performance, growth)
   - Data type (number, percentage, boolean, string)
   - Suggested source in the codebase

### 3. Superset Dashboards

1. Open http://localhost:8088
2. Login with `admin` / `admin`
3. Navigate to Dashboards
4. Each analyzed repository gets its own dashboard with visualizations

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflow/analyze` | POST | Start repository analysis |
| `/api/workflow/jobs` | GET | List all analysis jobs |
| `/api/workflow/jobs/{id}` | GET | Get job status |
| `/api/workflow/jobs/{id}/metrics` | GET | Get discovered metrics |
| `/api/dashboard/workspaces` | GET | List all workspaces |
| `/api/dashboard/workspaces/{id}` | GET | Get workspace with metrics |

## Project Structure

```
git-metrics-detector/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Settings configuration
│   │   ├── database.py          # Database setup
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── routers/
│   │   │   ├── workflow.py      # Analysis endpoints
│   │   │   └── dashboard.py     # Dashboard endpoints
│   │   ├── services/
│   │   │   ├── github_service.py    # GitHub API integration
│   │   │   ├── llm_service.py       # Gemini AI integration
│   │   │   ├── analysis_service.py  # Analysis orchestration
│   │   │   ├── workspace_service.py # Workspace management
│   │   │   └── superset_service.py  # Superset integration
│   │   └── utils/
│   │       ├── file_filters.py      # File filtering logic
│   │       └── token_estimator.py   # Token batching
│   ├── data/                    # SQLite database
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── workflow/                # Analysis UI (port 3000)
│   │   ├── src/
│   │   └── package.json
│   └── dashboard/               # Metrics dashboard (port 3001)
│       ├── src/
│       └── package.json
├── superset_config.py           # Superset configuration
└── README.md
```

## Troubleshooting

### GitHub Rate Limiting

If you see `403 Forbidden` errors, you've hit the GitHub API rate limit. Solutions:
- Wait 1 hour for rate limit reset
- Use a valid GitHub token with `repo` scope
- Use authenticated requests (unlimited for public repos)

### Gemini API Errors

- `API_KEY_INVALID`: Verify your API key at https://aistudio.google.com/apikey
- `RESOURCE_EXHAUSTED`: You've hit the rate limit. Wait or upgrade your plan.

### Superset Connection Issues

- Ensure Superset is running on port 8088
- Check that the database path in `superset_config.py` is correct
- Verify the `SUPERSET_URL` in backend `.env` matches

## License

MIT License
