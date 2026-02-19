from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db


async def _fix_stale_jobs():
    """Mark any jobs left in transient states from previous runs as failed."""
    from .database import async_session
    from .models import AnalysisJob
    from sqlalchemy import update

    async with async_session() as session:
        await session.execute(
            update(AnalysisJob)
            .where(AnalysisJob.status.in_(["pending", "fetching", "analyzing"]))
            .values(
                status="failed",
                error_message="Analysis interrupted by server restart. Please try again.",
            )
        )
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _fix_stale_jobs()
    yield


app = FastAPI(title="Git Metrics Detector", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routers import workflow, dashboard

app.include_router(workflow.router, prefix="/api/workflow", tags=["Workflow"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
