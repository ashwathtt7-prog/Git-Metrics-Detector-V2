
import asyncio
import os
import sys
from uuid import uuid4

# Ensure app is in path
sys.path.append(os.getcwd())

from app.database import init_db, async_session
from app.models import AnalysisJob
from app.services.analysis_service import run_analysis, create_job

async def test():
    print("--- 🚀 Starting Full Analysis Test ---")
    
    # 1. Initialize DB
    await init_db()
    print("DB Initialized.")
    
    # 2. Create a test job
    # Using a moderate sized public repo
    test_repo = "https://github.com/expressjs/express"
    print(f"Testing with repo: {test_repo}")
    
    async with async_session() as session:
        job = await create_job(session, test_repo, None)
        job_id = job.id
        print(f"Created Job ID: {job_id}")

    # 3. Run Analysis
    print("Starting background analysis task...")
    try:
        # We run it directly in foreground for testing
        await run_analysis(job_id, test_repo, None)
        
        # 4. Check results
        async with async_session() as session:
            job = await session.get(AnalysisJob, job_id)
            print(f"\n--- Analysis Results ---")
            print(f"Status: {job.status}")
            if job.status == "completed":
                print("✅ Analysis SUCCESS!")
                print(f"Workspace ID: {job.workspace_id}")
            else:
                print(f"❌ Analysis FAILED!")
                print(f"Error: {job.error_message}")
            
            # Print last 5 logs
            if job.logs:
                import json
                logs = json.loads(job.logs)
                print("\nLast Logs:")
                for log in logs[-10:]:
                    print(log)
                    
    except Exception as e:
        print(f"Test FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
