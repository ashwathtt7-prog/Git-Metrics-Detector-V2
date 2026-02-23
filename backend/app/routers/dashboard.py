from typing import List
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timezone
from uuid import uuid4
from ..database import get_session
from ..schemas import (
    WorkspaceResponse, WorkspaceDetailResponse, MetricResponse,
    MetricEntryCreate, MetricEntryResponse,
)
from ..models import Workspace, Metric, MetricEntry, AnalysisJob

router = APIRouter()


@router.get("/workspaces", response_model=List[WorkspaceResponse])
async def list_workspaces(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Workspace).order_by(Workspace.created_at.desc())
    )
    workspaces = result.scalars().all()

    def _extract_metabase_url(dashboard_config: str | None) -> str | None:
        if not dashboard_config or not isinstance(dashboard_config, str):
            return None
        s = dashboard_config.strip()
        if not s.startswith("{"):
            return None
        try:
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                if parsed.get("metabase_url"):
                    return parsed.get("metabase_url")
                plan = parsed.get("plan")
                if isinstance(plan, dict) and plan.get("metabase_url"):
                    return plan.get("metabase_url")
        except Exception:
            return None
        return None

    responses = []
    for ws in workspaces:
        count_result = await session.execute(
            select(func.count()).where(Metric.workspace_id == ws.id)
        )
        metric_count = count_result.scalar() or 0
        responses.append(
            WorkspaceResponse(
                id=ws.id, name=ws.name, repo_url=ws.repo_url,
                description=ws.description, created_at=ws.created_at,
                updated_at=ws.updated_at, metric_count=metric_count,
                metabase_url=_extract_metabase_url(ws.dashboard_config),
            )
        )
    return responses


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceDetailResponse)
async def get_workspace(workspace_id: str, session: AsyncSession = Depends(get_session)):
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    result = await session.execute(
        select(Metric).where(Metric.workspace_id == workspace_id).order_by(Metric.display_order)
    )
    db_metrics = result.scalars().all()
    metrics = []
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
                created_at=m.created_at, source_table=m.source_table,
                source_platform=m.source_platform, entries=entries
            )
        )

    return WorkspaceDetailResponse(
        id=ws.id, name=ws.name, repo_url=ws.repo_url,
        description=ws.description, created_at=ws.created_at,
        updated_at=ws.updated_at, metrics=metrics,
        dashboard_config=ws.dashboard_config,
    )


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str, session: AsyncSession = Depends(get_session)):
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await session.delete(ws)
    await session.commit()
    return {"status": "deleted"}


@router.get("/workspaces/{workspace_id}/metrics", response_model=List[MetricResponse])
async def get_workspace_metrics(workspace_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Metric).where(Metric.workspace_id == workspace_id).order_by(Metric.display_order)
    )
    return [
        MetricResponse(
            id=m.id, workspace_id=m.workspace_id, name=m.name,
            description=m.description, category=m.category, data_type=m.data_type,
            suggested_source=m.suggested_source, display_order=m.display_order,
            created_at=m.created_at, source_table=m.source_table,
            source_platform=m.source_platform,
        )
        for m in result.scalars().all()
    ]


@router.post("/metrics/{metric_id}/entries", response_model=MetricEntryResponse)
async def add_metric_entry(
    metric_id: str,
    entry: MetricEntryCreate,
    session: AsyncSession = Depends(get_session),
):
    metric = await session.get(Metric, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    now = datetime.now(timezone.utc).isoformat()
    new_entry = MetricEntry(
        id=str(uuid4()),
        metric_id=metric_id,
        value=entry.value,
        recorded_at=now,
        notes=entry.notes,
    )
    session.add(new_entry)
    await session.commit()

    return MetricEntryResponse(
        id=new_entry.id, metric_id=new_entry.metric_id,
        value=new_entry.value, recorded_at=new_entry.recorded_at,
        notes=new_entry.notes,
    )


@router.get("/metrics/{metric_id}/entries", response_model=List[MetricEntryResponse])
async def get_metric_entries(metric_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(MetricEntry)
        .where(MetricEntry.metric_id == metric_id)
        .order_by(MetricEntry.recorded_at.desc())
    )
    return [
        MetricEntryResponse(
            id=e.id, metric_id=e.metric_id, value=e.value,
            recorded_at=e.recorded_at, notes=e.notes,
        )
        for e in result.scalars().all()
    ]


# --- Analytics Endpoints ---

@router.get("/analytics/overview")
async def get_analytics_overview(session: AsyncSession = Depends(get_session)):
    ws_count = (await session.execute(select(func.count()).select_from(Workspace))).scalar()
    metric_count = (await session.execute(select(func.count()).select_from(Metric))).scalar()
    entry_count = (await session.execute(select(func.count()).select_from(MetricEntry))).scalar()

    cat_result = await session.execute(
        select(Metric.category, func.count()).group_by(Metric.category)
    )
    category_distribution = [
        {"category": row[0] or "uncategorized", "count": row[1]}
        for row in cat_result.all()
    ]

    dtype_result = await session.execute(
        select(Metric.data_type, func.count()).group_by(Metric.data_type)
    )
    datatype_distribution = [
        {"data_type": row[0] or "unknown", "count": row[1]}
        for row in dtype_result.all()
    ]

    ws_metric_result = await session.execute(
        select(Workspace.name, Metric.category, func.count())
        .join(Metric, Workspace.id == Metric.workspace_id)
        .group_by(Workspace.name, Metric.category)
    )
    workspace_metrics = [
        {"workspace": row[0], "category": row[1] or "uncategorized", "count": row[2]}
        for row in ws_metric_result.all()
    ]

    entries_result = await session.execute(
        select(
            func.substr(MetricEntry.recorded_at, 1, 10).label("date"),
            func.count(),
        )
        .group_by("date")
        .order_by("date")
        .limit(30)
    )
    entry_trends = [
        {"date": row[0], "count": row[1]}
        for row in entries_result.all()
    ]

    jobs_result = await session.execute(
        select(AnalysisJob.status, func.count()).group_by(AnalysisJob.status)
    )
    job_stats = [
        {"status": row[0], "count": row[1]}
        for row in jobs_result.all()
    ]

    return {
        "totals": {
            "workspaces": ws_count,
            "metrics": metric_count,
            "entries": entry_count,
        },
        "category_distribution": category_distribution,
        "datatype_distribution": datatype_distribution,
        "workspace_metrics": workspace_metrics,
        "entry_trends": entry_trends,
        "job_stats": job_stats,
    }


@router.get("/analytics/workspace/{workspace_id}")
async def get_workspace_analytics(
    workspace_id: str, session: AsyncSession = Depends(get_session)
):
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    cat_result = await session.execute(
        select(Metric.category, func.count())
        .where(Metric.workspace_id == workspace_id)
        .group_by(Metric.category)
    )
    category_distribution = [
        {"category": row[0] or "uncategorized", "count": row[1]}
        for row in cat_result.all()
    ]

    dtype_result = await session.execute(
        select(Metric.data_type, func.count())
        .where(Metric.workspace_id == workspace_id)
        .group_by(Metric.data_type)
    )
    datatype_distribution = [
        {"data_type": row[0] or "unknown", "count": row[1]}
        for row in dtype_result.all()
    ]

    # Get all metrics for workspace
    metrics_result = await session.execute(
        select(Metric).where(Metric.workspace_id == workspace_id).order_by(Metric.display_order)
    )
    metrics = metrics_result.scalars().all()

    metric_values = []
    
    import re
    def extract_number(s):
        if s is None: return 0
        # Try to find the first number (integer or decimal)
        match = re.search(r"([-+]?\d*\.?\d+)", str(s))
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return 0
        return 0

    for metric in metrics:
        # Get latest entry
        latest_entry_result = await session.execute(
            select(MetricEntry)
            .where(MetricEntry.metric_id == metric.id)
            .order_by(MetricEntry.recorded_at.desc())
            .limit(1)
        )
        latest_entry = latest_entry_result.scalar_one_or_none()
        
        value = 0
        if latest_entry:
            value = extract_number(latest_entry.value)
        
        metric_values.append({
            "metric": metric.name,
            "category": metric.category or "uncategorized",
            "value": value,
            "display_value": latest_entry.value if latest_entry else "N/A"
        })

    return {
        "category_distribution": category_distribution,
        "datatype_distribution": datatype_distribution,
        "metric_values": metric_values,
    }
