
import asyncio
import os
import sys

sys.path.append(os.getcwd())
from app.database import async_session
from app.models import AnalysisJob

async def check():
    async with async_session() as session:
        from sqlalchemy import select
        res = await session.execute(select(AnalysisJob).order_by(AnalysisJob.created_at.desc()).limit(1))
        job = res.scalar_one_or_none()
        if job:
            print(f"JOB_STATUS:{job.status}")
            print(f"JOB_ERROR:{job.error_message}")
            print(f"JOB_STAGE:{job.current_stage}")
        else:
            print("JOB_NOT_FOUND")

if __name__ == "__main__":
    asyncio.run(check())
