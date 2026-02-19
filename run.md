# How to Install and Run Git Metrics Detector

 This guide provides step-by-step instructions to set up and run the Git Metrics Detector application, including the Backend, Dashboard, Workflow, and Evidence services.

 ## Prerequisites

 Ensure you have the following installed on your system:
 - **Python 3.10+**
 - **Node.js 18+**
 - **Git**

 ---

 ## 1. Backend Setup

 The backend is built with FastAPI and handles repository analysis.

 1.  Navigate to the `backend` directory:
     ```bash
     cd backend
     ```

 2.  Create a virtual environment:
     ```bash
     python -m venv venv
     ```

 3.  Activate the virtual environment:
     - **Windows:**
       ```bash
       .\venv\Scripts\activate
       ```
     - **Mac/Linux:**
       ```bash
       source venv/bin/activate
       ```

 4.  Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

 5.  **Configure Environment Variables:**
     Create a `.env` file in the `backend/` directory and add your API keys:
     ```ini
     GEMINI_API_KEY=your_gemini_key
     GROQ_API_KEY=your_groq_key
     OPENROUTER_API_KEY=your_openrouter_key
     GITHUB_TOKEN=your_github_token  # Optional but recommended for higher rate limits
     ```

 ---

 ## 2. Frontend Setup (Dashboard & Workflow)

 The frontend consists of two React applications (Dashboard and Workflow) and an Evidence project.

 ### Dashboard App
 1.  Navigate to the dashboard directory:
     ```bash
     cd frontend/dashboard
     ```
 2.  Install dependencies:
     ```bash
     npm install
     ```

 ### Workflow App
 1.  Navigate to the workflow directory:
     ```bash
     cd frontend/workflow
     ```
 2.  Install dependencies:
     ```bash
     npm install
     ```

 ### Evidence Analytics (Optional but Recommended)
 1.  Navigate to the evidence directory:
     ```bash
     cd evidence
     ```
 2.  Install dependencies:
     ```bash
     npm install
     ```

 ---

 ## 3. Running the Application

 You can run the application using the automated script (Windows) or manually.

 ### Option A: Using `start.bat` (Windows Recommended)
 This script automatically checks permissions, activates the virtual environment, and starts all services in separate windows.

 1.  Go to the root directory of the project.
 2.  Double-click `start.bat` or run it from the terminal:
     ```bash
     .\start.bat
     ```

 ### Option B: Manual Startup
 Run each service in a separate terminal window.

 **1. Backend:**
 ```bash
 cd backend
 # Activate venv first!
 uvicorn app.main:app --reload --port 8000
 ```

 **2. Dashboard:**
 ```bash
 cd frontend/dashboard
 npm run dev -- --host
 ```

 **3. Workflow:**
 ```bash
 cd frontend/workflow
 npm run dev -- --host
 ```

 **4. Evidence:**
 ```bash
 cd evidence
 npm run dev
 ```

 ---

 ## 4. Accessing the Application

 Once the services are running, you can access them at:

 - **Workflow App (Start Here):** [http://localhost:3001](http://localhost:3001) - Use this to input a GitHub repo URL and start analysis.
 - **Dashboard:** [http://localhost:3000](http://localhost:3000) - View the generated metrics.
 - **Backend API:** [http://localhost:8000/docs](http://localhost:8000/docs) - Interactive API documentation.
 - **Evidence:** [http://localhost:3002](http://localhost:3002) - Analytics reports.
