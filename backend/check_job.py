
import asyncio
import os
import sys
import json

sys.path.append(os.getcwd())

from app.database import async_session
from app.models import AnalysisJob

async def check():
    async with async_session() as session:
        from sqlalchemy import select
        res = await session.execute(select(AnalysisJob).order_by(AnalysisJob.created_at.desc()).limit(1))
        job = res.scalar_one_or_none()
        if job:
            print(f"ID: {job.id} | Status: {job.status} | Stage: {job.current_stage}")
            print(f"Error: {job.error_message}")
            if job.logs:
                logs = json.loads(job.logs)
                print(f"Total Logs: {len(logs)}")
                for l in logs[-5:]:
                    print(l)
        else:
            print("No jobs found.")

if __name__ == "__main__":
    asyncio.run(check())
