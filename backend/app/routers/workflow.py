from typing import List
import json
import importlib
import inspect
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
from datetime import datetime, timezone, timedelta

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


@router.get("/debug/runtime")
async def debug_runtime():
    """Return non-sensitive runtime diagnostics for local development."""
    try:
        ms_mod = importlib.import_module("app.services.metabase_service")
        from ..services.metabase_service import metabase_service
        auth_src = ""
        try:
            auth_src = inspect.getsource(ms_mod.MetabaseService._authenticate)
        except Exception:
            auth_src = ""

        setup_src = ""
        try:
            setup_src = inspect.getsource(ms_mod.MetabaseService.setup_database)
        except Exception:
            setup_src = ""

        return {
            "settings": {
                "metabase_url": settings.metabase_url,
                "metabase_username_set": bool(settings.metabase_username),
                "metabase_password_set": bool(settings.metabase_password),
                "gemini_service_account_file": settings.gemini_service_account_file,
            },
            "metabase_service": {
                "module_file": getattr(ms_mod, "__file__", None),
                "base_url": getattr(metabase_service, "base_url", None),
                "username_set": bool(getattr(metabase_service, "username", "")),
                "password_set": bool(getattr(metabase_service, "password", "")),
                "session_token_set": bool(getattr(metabase_service, "session_token", "")),
                "auth_refresh_enabled": ("Refresh credentials" in auth_src),
                "setup_raises_on_no_headers": ("credentials not configured" in setup_src.lower()),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"debug_runtime failed: {type(e).__name__}: {str(e)[:200]}")


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
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "category": m.category,
            "data_type": m.data_type,
            "source_table": m.source_table,
            "source_platform": m.source_platform,
        } for m in metrics
    ]

    # 2. Generate mock entries (LLM with deterministic fallback)
    try:
        mock_data, trace = await llm_service.generate_mock_data(metrics_data, ws.name)
        
        entries_added = 0
        db_metrics_by_id = {m.id: m.id for m in metrics}
        def _norm(s: str) -> str:
            return "".join(ch.lower() for ch in s.strip() if ch.isalnum())
        db_metrics_by_name = {_norm(m.name): m.id for m in metrics if m.name}
        
        now_utc = datetime.now(timezone.utc)
        min_ts = now_utc - timedelta(days=45)
        max_ts = now_utc + timedelta(days=2)

        def _safe_ts(raw: object, *, fallback_days_ago: int) -> str:
            if isinstance(raw, str) and raw.strip():
                s = raw.strip().replace("Z", "+00:00")
                try:
                    dtp = datetime.fromisoformat(s)
                    if dtp.tzinfo is None:
                        dtp = dtp.replace(tzinfo=timezone.utc)
                    if min_ts <= dtp <= max_ts:
                        return dtp.astimezone(timezone.utc).isoformat()
                except Exception:
                    pass
            return (now_utc - timedelta(days=fallback_days_ago)).replace(hour=12, minute=0, second=0, microsecond=0).isoformat()

        for md in mock_data:
            metric_id = md.get("metric_id") or ""
            metric_name = md.get("metric_name") or ""
            if metric_id and metric_id in db_metrics_by_id:
                metric_id = metric_id
            else:
                metric_id = db_metrics_by_name.get(_norm(metric_name), "")
            if not metric_id:
                continue
            
            for idx, entry in enumerate(md.get("entries", [])):
                me = MetricEntry(
                    id=str(uuid4()),
                    metric_id=metric_id,
                    value=str(entry.get("value", "")),
                    recorded_at=_safe_ts(entry.get("recorded_at"), fallback_days_ago=(29 - (idx % 30))),
                    notes=entry.get("notes"),
                )
                session.add(me)
                entries_added += 1
        
        await session.commit()

        # 3. Ensure Metabase dashboard exists (matches expected UI workflow)
        metabase_url = None
        metabase_error = None

        # If already created, return it.
        if ws.dashboard_config and ws.dashboard_config.startswith("{"):
            try:
                existing = json.loads(ws.dashboard_config)
                if isinstance(existing, dict) and existing.get("metabase_url"):
                    metabase_url = existing.get("metabase_url")
            except Exception:
                pass

        if not metabase_url:
            try:
                plan, plan_trace = await llm_service.generate_dashboard_plan(metrics_data, ws.name, workspace_id)
                plan_data = plan if isinstance(plan, dict) else {"plan": plan}

                try:
                    import os
                    from ..services.metabase_service import metabase_service

                    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/metrics.db"))
                    mb_db_id = await metabase_service.setup_database(db_path)
                    if mb_db_id:
                        mb_url = await metabase_service.create_dashboard(ws.name, mb_db_id, plan_data, workspace_id=workspace_id)
                        if mb_url:
                            metabase_url = mb_url
                            ws.dashboard_config = json.dumps({"metabase_url": mb_url, "plan": plan_data, "trace": plan_trace})
                            await session.commit()
                        else:
                            metabase_error = "Metabase dashboard creation returned no URL."
                    else:
                        metabase_error = "Metabase database registration failed (auth or connectivity issue)."
                except Exception as me:
                    metabase_error = f"Metabase API error: {str(me)}"
            except Exception as pe:
                metabase_error = f"Dashboard plan generation failed: {str(pe)}"

        return {
            "status": "success",
            "entries_added": entries_added,
            "trace": trace,
            "metabase_url": metabase_url,
            "metabase_error": metabase_error,
        }
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
    
    plan_data = None
    plan_trace = None

    # Reuse any existing plan (even if Metabase creation previously failed), otherwise generate a new one.
    if isinstance(existing_config, dict) and (existing_config.get("cards") or existing_config.get("plan")):
        plan_data = existing_config.get("plan") or existing_config
        plan_trace = existing_config.get("trace")
    else:
        try:
            plan, trace = await llm_service.generate_dashboard_plan(metrics_data, ws.name, workspace_id)
            plan_data = plan if isinstance(plan, dict) else {"plan": plan}
            plan_trace = trace
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    metabase_error = None
    mb_url = None
    try:
        import os
        from ..services.metabase_service import metabase_service
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/metrics.db"))
        mb_db_id = await metabase_service.setup_database(db_path)
        if mb_db_id:
            mb_url = await metabase_service.create_dashboard(ws.name, mb_db_id, plan_data, workspace_id=workspace_id)
            if mb_url:
                plan_data["metabase_url"] = mb_url
                if "metabase_error" in plan_data:
                    plan_data.pop("metabase_error", None)
            else:
                metabase_error = "Metabase dashboard creation returned no URL."
        else:
            metabase_error = "Metabase database registration failed (auth or connectivity issue)."
    except Exception as me:
        metabase_error = f"Metabase API error: {str(me)}"

    if metabase_error:
        plan_data["metabase_error"] = metabase_error

    if isinstance(plan_trace, dict):
        plan_data["trace"] = plan_trace

    ws.dashboard_config = json.dumps(plan_data)
    await session.commit()
    return plan_data
