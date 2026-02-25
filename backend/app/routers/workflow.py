from typing import List
import json
import importlib
import inspect
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Response
from fastapi.responses import HTMLResponse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
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
                    insights=m.insights,
                    entries=entries
                )
            )

    return JobMetricsResponse(
        job=_job_response(job),
        metrics=metrics,
        workspace_id=job.workspace_id,
    )

@router.post("/metrics/{metric_id}/insights")
async def generate_single_metric_insights(
    metric_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Generate detailed business insights for a single metric on demand."""
    metric = await session.get(Metric, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    # If already has insights, return them
    if metric.insights:
        return {"status": "cached", "insights": json.loads(metric.insights)}

    # Need workspace context for project
    ws = await session.get(Workspace, metric.workspace_id)
    project_summary = {}
    if ws:
        project_summary = {
            "project_name": ws.name,
            "description": ws.description or "",
        }

    # Gather all metrics in the workspace for correlation context (include evidence for rich insights)
    res = await session.execute(select(Metric).where(Metric.workspace_id == metric.workspace_id))
    all_metrics = res.scalars().all()
    metrics_data = [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "category": m.category,
            "data_type": m.data_type,
            "suggested_source": m.suggested_source,
            "source_table": m.source_table,
            "source_platform": m.source_platform,
            "evidence": json.loads(m.evidence) if m.evidence else [],
        }
        for m in all_metrics
    ]

    try:
        insights_list = await llm_service.generate_metric_insights(metrics_data, project_summary)

        # Store insights for ALL metrics in the workspace (batch benefit)
        def _norm(s: str) -> str:
            return "".join(ch.lower() for ch in s.strip() if ch.isalnum())

        insights_by_name = {}
        for ins in insights_list:
            if isinstance(ins, dict) and ins.get("metric_name"):
                insights_by_name[_norm(ins["metric_name"])] = ins

        for m in all_metrics:
            key = _norm(m.name)
            if key in insights_by_name:
                m.insights = json.dumps(insights_by_name[key])

        await session.commit()

        # Return the requested metric's insights
        target_key = _norm(metric.name)
        if target_key in insights_by_name:
            return {"status": "generated", "insights": insights_by_name[target_key]}
        else:
            return {"status": "generated", "insights": None}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insight generation failed: {str(e)}")


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
            
            if "metabase_error" in plan_data and mb_url:
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


@router.get("/workspaces/{workspace_id}/dashboard-data")
async def get_dashboard_data(
    workspace_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Return all metric data formatted for React Recharts dashboard."""
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    res = await session.execute(
        select(Metric)
        .where(Metric.workspace_id == workspace_id)
        .options(selectinload(Metric.entries))
        .order_by(Metric.display_order)
    )
    metrics = res.scalars().all()

    # Build chart-ready data for each metric
    charts = []
    category_counts: dict[str, int] = {}
    total_entries = 0

    for m in metrics:
        cat = m.category or "other"
        category_counts[cat] = category_counts.get(cat, 0) + 1

        entries_data = []
        for e in sorted(m.entries, key=lambda x: x.recorded_at):
            # Try to parse value as number for charting
            try:
                val = float(e.value)
            except (ValueError, TypeError):
                val = e.value
            entries_data.append({
                "date": e.recorded_at[:10] if e.recorded_at else "",
                "value": val,
                "notes": e.notes,
            })
            total_entries += 1

        # Parse insights if available
        insights_obj = None
        if m.insights:
            try:
                insights_obj = json.loads(m.insights)
            except Exception:
                pass

        charts.append({
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "category": cat,
            "data_type": m.data_type,
            "platform": m.source_platform,
            "source": m.suggested_source,
            "entries": entries_data,
            "entry_count": len(entries_data),
            "insights": insights_obj,
            "latest_value": entries_data[-1]["value"] if entries_data else None,
        })

    # Category distribution for pie chart
    category_distribution = [
        {"name": cat, "value": count}
        for cat, count in category_counts.items()
    ]

    # Metabase URL if available
    metabase_url = None
    if ws.dashboard_config:
        try:
            cfg = json.loads(ws.dashboard_config)
            metabase_url = cfg.get("metabase_url")
        except Exception:
            pass

    return {
        "workspace": {
            "id": ws.id,
            "name": ws.name,
            "repo_url": ws.repo_url,
            "description": ws.description,
        },
        "summary": {
            "total_metrics": len(metrics),
            "total_entries": total_entries,
            "categories": category_counts,
        },
        "category_distribution": category_distribution,
        "charts": charts,
        "metabase_url": metabase_url,
    }


@router.get("/metabase-view/{uuid}", response_class=HTMLResponse)
async def metabase_proxy(uuid: str):
    """
    Backend Proxy for Metabase Public Dashboards.
    This allows us to inject custom CSS to fix the 'white background' problem
    and apply our premium Red & White aesthetic.
    """
    from ..services.metabase_service import metabase_service
    base_url = metabase_service.base_url.rstrip("/")
    target_url = f"{base_url}/public/dashboard/{uuid}"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(target_url, follow_redirects=True, timeout=10.0)
            if resp.status_code != 200:
                return f"<h1>Metabase Offline</h1><p>Status: {resp.status_code}</p>"
            
            html = resp.text
            
            custom_head = f"""
            <base href="{base_url}/">
            <style>
                /* Aggressive Background Overrides for Metabase OSS */
                html, body, #root, .EmbedFrame, .Dashboard, .Dashboard-container, 
                .public-dashboard, .DashboardGrid, .PinnedSection, .Scalar, .TableInteractive,
                .application, .scroll-shadow-container, .scroll-view {{
                    background: radial-gradient(circle at 20% 20%, #fffafa, transparent),
                                radial-gradient(circle at 80% 80%, #fff5f5, transparent),
                                #ffffff !important;
                    background-attachment: fixed !important;
                    background-color: #ffffff !important;
                }}

                /* Remove Metabase's hardcoded background colors on sections */
                .css-1f9v8u0, .css-1v0u0wz, .css-14v0u0wz, div[class^="css-"], header, nav {{
                    background-color: transparent !important;
                }}

                /* Refined Premium Card Shadows (Red Tint) */
                .DashCard, .Card, .cell {{
                    background-color: #ffffff !important;
                    border-radius: 16px !important;
                    box-shadow: 0 10px 25px -5px rgba(220, 38, 38, 0.06) !important;
                    border: 1px solid rgba(220, 38, 38, 0.08) !important;
                    transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
                }}
                .DashCard:hover, .Card:hover {{
                    transform: translateY(-4px) !important;
                    box-shadow: 0 20px 35px -10px rgba(220, 38, 38, 0.12) !important;
                    border-color: rgba(220, 38, 38, 0.2) !important;
                }}

                /* Force Text and Axis Legibility */
                .axis line, .axis path, .grid line {{
                    stroke: #f1f5f9 !important;
                }}
                text {{ fill: #475569 !important; }}

                /* UI Cleanup */
                .EmbedFooter, .EmbedHeader, .Nav {{ display: none !important; }}
                .Header {{ background: transparent !important; border-bottom: none !important; box-shadow: none !important; }}
                
                /* Selection/Scroll refinement */
                ::selection {{ background: #fee2e2; color: #b91c1c; }}
            </style>
            """
            
            # Use a more reliable injection point: at the beginning of the <head> segment
            if "<head>" in html:
                html = html.replace("<head>", f"<head>{custom_head}")
            elif "</head>" in html:
                html = html.replace("</head>", f"{custom_head}</head>")
            else:
                html = custom_head + html
                
            return html
        except Exception as e:
            return f"<h1>Proxy Error</h1><p>{str(e)}</p>"
