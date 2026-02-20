
import asyncio
import os
import sys

sys.path.append(os.getcwd())
from app.database import async_session
from app.models import AnalysisJob
from sqlalchemy import select

async def check():
    async with async_session() as session:
        res = await session.execute(select(AnalysisJob).order_by(AnalysisJob.created_at.desc()).limit(5))
        jobs = res.scalars().all()
        print(f"Checking {len(jobs)} recent jobs:")
        for j in jobs:
            print(f"ID: {j.id} | Status: {j.status} | URL: '{j.repo_url}'")

if __name__ == "__main__":
    asyncio.run(check())
