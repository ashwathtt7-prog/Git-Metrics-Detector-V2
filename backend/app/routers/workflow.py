from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_session
from ..config import settings
from ..schemas import AnalyzeRequest, JobResponse, JobMetricsResponse, MetricResponse
from ..models import AnalysisJob, Metric
from ..services.analysis_service import create_job, run_analysis

router = APIRouter()


@router.post("/analyze", response_model=JobResponse)
async def start_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    token = settings.github_token or None
    job = await create_job(session, request.repo_url, token)
    background_tasks.add_task(run_analysis, job.id, request.repo_url, token)
    return JobResponse(
        id=job.id,
        repo_url=job.repo_url,
        repo_owner=job.repo_owner,
        repo_name=job.repo_name,
        status=job.status,
        total_files=job.total_files,
        analyzed_files=job.analyzed_files,
        created_at=job.created_at,
    )


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(AnalysisJob).order_by(AnalysisJob.created_at.desc()).limit(20)
    )
    jobs = result.scalars().all()
    return [
        JobResponse(
            id=j.id, repo_url=j.repo_url, repo_owner=j.repo_owner,
            repo_name=j.repo_name, status=j.status, error_message=j.error_message,
            total_files=j.total_files, analyzed_files=j.analyzed_files,
            created_at=j.created_at, completed_at=j.completed_at,
            workspace_id=j.workspace_id,
        )
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    job = await session.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        id=job.id, repo_url=job.repo_url, repo_owner=job.repo_owner,
        repo_name=job.repo_name, status=job.status, error_message=job.error_message,
        total_files=job.total_files, analyzed_files=job.analyzed_files,
        created_at=job.created_at, completed_at=job.completed_at,
        workspace_id=job.workspace_id,
    )


@router.get("/jobs/{job_id}/metrics", response_model=JobMetricsResponse)
async def get_job_metrics(job_id: str, session: AsyncSession = Depends(get_session)):
    job = await session.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    metrics = []
    if job.workspace_id:
        result = await session.execute(
            select(Metric)
            .where(Metric.workspace_id == job.workspace_id)
            .order_by(Metric.display_order)
        )
        metrics = [
            MetricResponse(
                id=m.id, workspace_id=m.workspace_id, name=m.name,
                description=m.description, category=m.category, data_type=m.data_type,
                suggested_source=m.suggested_source, display_order=m.display_order,
                created_at=m.created_at,
            )
            for m in result.scalars().all()
        ]

    return JobMetricsResponse(
        job=JobResponse(
            id=job.id, repo_url=job.repo_url, repo_owner=job.repo_owner,
            repo_name=job.repo_name, status=job.status, error_message=job.error_message,
            total_files=job.total_files, analyzed_files=job.analyzed_files,
            created_at=job.created_at, completed_at=job.completed_at,
            workspace_id=job.workspace_id,
        ),
        metrics=metrics,
        workspace_id=job.workspace_id,
    )
