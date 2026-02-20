from typing import List
import json
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from ..database import get_session
from ..config import settings
from ..schemas import AnalyzeRequest, JobResponse, JobMetricsResponse, MetricResponse, MetricEntryResponse
from ..models import AnalysisJob, Metric, Workspace, MetricEntry
from ..services.analysis_service import create_job, run_analysis, add_log
from ..services.github_service import list_user_repos
from ..services import llm_service
from uuid import uuid4
from datetime import datetime, timezone

router = APIRouter()


def _job_response(job: AnalysisJob) -> JobResponse:
    return JobResponse(
        id=job.id, repo_url=job.repo_url, repo_owner=job.repo_owner,
        repo_name=job.repo_name, status=job.status, error_message=job.error_message,
        total_files=job.total_files, analyzed_files=job.analyzed_files,
        created_at=job.created_at, completed_at=job.completed_at,
        workspace_id=job.workspace_id, progress_message=job.progress_message,
        current_stage=job.current_stage, logs=job.logs,
    )


@router.post("/analyze", response_model=JobResponse)
async def start_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    # Check for existing completed job with this URL
    if not request.force:
        result = await session.execute(
            select(AnalysisJob).where(AnalysisJob.repo_url == request.repo_url.strip())
            .where(AnalysisJob.status == "completed")
            .order_by(AnalysisJob.created_at.desc())
        )
        existing = result.scalar_one_or_none()
        if existing:
            # We return a 409 Conflict with the existing job ID
            raise HTTPException(
                status_code=409, 
                detail={
                    "message": "This repository has already been analyzed.",
                    "job_id": existing.id,
                    "workspace_id": existing.workspace_id
                }
            )
    else:
        # If force=True, we delete previous jobs and their workspaces for this URL
        # To avoid primary key / foreign key confusion, we'll delete workspaces first
        # But our models have workspace_id in AnalysisJob. 
        # Actually, let's just find them and delete.
        repo_url_clean = request.repo_url.strip()
        
        # 1. Find all workspaces for this repo
        ws_result = await session.execute(select(Workspace).where(Workspace.repo_url == repo_url_clean))
        workspaces = ws_result.scalars().all()
        for ws in workspaces:
            await session.delete(ws) # This will cascade to metrics and entries
        
        # 2. Delete all jobs for this repo
        await session.execute(delete(AnalysisJob).where(AnalysisJob.repo_url == repo_url_clean))
        
        await session.commit()
        print(f"[Workflow] Cleaned up previous data for {repo_url_clean} before re-analysis")

    token = request.github_token or settings.github_token or None
    job = await create_job(session, request.repo_url, token)
    background_tasks.add_task(run_analysis, job.id, request.repo_url, token)
    return _job_response(job)


@router.get("/repos")
async def get_user_repos(token: str = ""):
    """List GitHub repos accessible with the given token."""
    effective_token = token or settings.github_token
    if not effective_token:
        raise HTTPException(status_code=400, detail="GitHub token required")
    try:
        repos = await list_user_repos(effective_token)
        return repos
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {str(e)}")


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(session: AsyncSession = Depends(get_session)):
    """Return the list of unique repositories analyzed, showing only the latest job for each."""
    # Subquery to find the latest created_at for each repo_url
    subq = (
        select(
            AnalysisJob.repo_url, 
            func.max(AnalysisJob.created_at).label("latest")
        )
        .group_by(AnalysisJob.repo_url)
        .subquery()
    )
    
    # Query to join back and get full Job details for those latest timestamps
    query = (
        select(AnalysisJob)
        .join(subq, (AnalysisJob.repo_url == subq.c.repo_url) & (AnalysisJob.created_at == subq.c.latest))
        .order_by(AnalysisJob.created_at.desc())
        .limit(30)
    )
    
    result = await session.execute(query)
    jobs = result.scalars().all()
    return [_job_response(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    job = await session.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_response(job)


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
        db_metrics = result.scalars().all()
        
        for m in db_metrics:
            # Fetch entries for this metric
            entries_result = await session.execute(
                select(MetricEntry)
                .where(MetricEntry.metric_id == m.id)
                .order_by(MetricEntry.recorded_at.desc())
            )
            entries = [
                MetricEntryResponse(
                    id=e.id, metric_id=e.metric_id, value=e.value,
                    recorded_at=e.recorded_at, notes=e.notes
                )
                for e in entries_result.scalars().all()
            ]

            metrics.append(
                MetricResponse(
                    id=m.id, workspace_id=m.workspace_id, name=m.name,
                    description=m.description, category=m.category, data_type=m.data_type,
                    suggested_source=m.suggested_source, display_order=m.display_order,
                    created_at=m.created_at,
                    source_table=m.source_table, source_platform=m.source_platform,
                    entries=entries
                )
            )

    return JobMetricsResponse(
        job=_job_response(job),
        metrics=metrics,
        workspace_id=job.workspace_id,
    )

@router.post("/workspaces/{workspace_id}/mock-data")
async def generate_more_mock_data(
    workspace_id: str,
    session: AsyncSession = Depends(get_session)
):
    # 1. Fetch Workspace and Metrics
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    res = await session.execute(select(Metric).where(Metric.workspace_id == workspace_id))
    metrics = res.scalars().all()
    metrics_data = [
        {
            "name": m.name,
            "description": m.description,
            "category": m.category,
            "data_type": m.data_type
        } for m in metrics
    ]

    # 2. Call LLM
    try:
        mock_data, thought = await llm_service.generate_mock_data(metrics_data, ws.name)
        
        entries_added = 0
        db_metrics = {m.name: m.id for m in metrics}
        
        for md in mock_data:
            metric_name = md.get("metric_name", "")
            metric_id = db_metrics.get(metric_name)
            if not metric_id: continue
            
            for entry in md.get("entries", []):
                me = MetricEntry(
                    id=str(uuid4()),
                    metric_id=metric_id,
                    value=str(entry.get("value", "")),
                    recorded_at=entry.get("recorded_at", datetime.now(timezone.utc).isoformat()),
                    notes=entry.get("notes"),
                )
                session.add(me)
                entries_added += 1
        
        await session.commit()
        return {"status": "success", "entries_added": entries_added, "thought": thought}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/metabase-plan")
async def get_metabase_plan(
    workspace_id: str,
    session: AsyncSession = Depends(get_session)
):
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    existing_config = None
    if ws.dashboard_config and ws.dashboard_config.startswith("{"):
        try:
            existing_config = json.loads(ws.dashboard_config)
            if existing_config.get("metabase_url"):
                return existing_config
        except:
            pass
            
    res = await session.execute(select(Metric).where(Metric.workspace_id == workspace_id))
    metrics = res.scalars().all()
    metrics_data = [
        {
            "name": m.name,
            "description": m.description,
            "category": m.category,
            "data_type": m.data_type,
            "source_table": m.source_table,
            "source_platform": m.source_platform
        } for m in metrics
    ]
    
    try:
        plan, thought = await llm_service.generate_dashboard_plan(metrics_data, ws.name, workspace_id)
        plan_data = plan if isinstance(plan, dict) else {"plan": plan}
        
        try:
            import os
            from ..services import metabase_service
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/metrics.db"))
            mb_db_id = await metabase_service.setup_database(db_path)
            if mb_db_id:
                mb_url = await metabase_service.create_dashboard(ws.name, mb_db_id, plan_data)
                if mb_url:
                    plan_data["metabase_url"] = mb_url
        except Exception as me:
            print(f"Metabase creation error: {me}")
        
        ws.dashboard_config = json.dumps(plan_data)
        await session.commit()
        return plan_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
