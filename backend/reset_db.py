import asyncio
import os
import sys

sys.path.append(os.getcwd())

from sqlalchemy import delete

from app.database import async_session, init_db
from app.models import AnalysisJob, Workspace, Metric, MetricEntry


async def main():
    await init_db()
    async with async_session() as session:
        # Delete in FK-safe order
        await session.execute(delete(MetricEntry))
        await session.execute(delete(Metric))
        await session.execute(delete(Workspace))
        await session.execute(delete(AnalysisJob))
        await session.commit()
    print("OK: cleared AnalysisJob, Workspace, Metric, MetricEntry tables.")


if __name__ == "__main__":
    asyncio.run(main())

