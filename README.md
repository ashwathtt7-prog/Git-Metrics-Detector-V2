
# Git Metrics Detector

Analyzes GitHub repositories to discover and track meaningful metrics using LLMs.

## Project Structure

- `backend/`: FastAPI application (Python)
- `frontend/dashboard/`: Dashboard frontend (React/Vite) - Port 3000
- `frontend/workflow/`: Workflow frontend (React/Vite) - Port 3001

## Prerequisites

- Python 3.10+
- Node.js 18+
- Git

## Setup & Running

### 1. Backend Setup

The backend handles the repository analysis and LLM interactions.

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment (optional but recommended):**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the `backend/` directory with your API keys:
    ```ini
    GEMINI_API_KEY=your_gemini_key
    GROQ_API_KEY=your_groq_key
    OPENROUTER_API_KEY=your_openrouter_key
    GITHUB_TOKEN=your_github_token_(optional)
    ```

5.  **Run the Backend Server:**
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```
    The API will be available at `http://localhost:8000`.

### 2. Frontend Setup

#### Dashboard App (Displays Metrics)

1.  **Navigate to the dashboard directory:**
    ```bash
    cd frontend/dashboard
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the Dashboard:**
    ```bash
    npm run dev
    ```
    The dashboard will run on `http://localhost:3000`.

#### Workflow App (Starts Analysis)

1.  **Navigate to the workflow directory:**
    ```bash
    cd frontend/workflow
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the Workflow App:**
    ```bash
    npm run dev
    ```
    The workflow app will run on `http://localhost:3001`.

## Usage Flow

1.  Open the **Workflow App** at [http://localhost:3001](http://localhost:3001).
2.  Enter a GitHub repository URL (e.g., `https://github.com/fastapi/fastapi`).
3.  Click **Analyze** and wait for the process to complete.
4.  Once finished, click **Go to Dashboard** or open [http://localhost:3000](http://localhost:3000) to view the discovered metrics.
