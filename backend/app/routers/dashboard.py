from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
from uuid import uuid4
from ..database import get_session
from ..schemas import (
    WorkspaceResponse, WorkspaceDetailResponse, MetricResponse,
    MetricEntryCreate, MetricEntryResponse,
)
from ..models import Workspace, Metric, MetricEntry

router = APIRouter()


@router.get("/workspaces", response_model=List[WorkspaceResponse])
async def list_workspaces(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Workspace).order_by(Workspace.created_at.desc())
    )
    workspaces = result.scalars().all()

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
    metrics = [
        MetricResponse(
            id=m.id, workspace_id=m.workspace_id, name=m.name,
            description=m.description, category=m.category, data_type=m.data_type,
            suggested_source=m.suggested_source, display_order=m.display_order,
            created_at=m.created_at,
        )
        for m in result.scalars().all()
    ]

    return WorkspaceDetailResponse(
        id=ws.id, name=ws.name, repo_url=ws.repo_url,
        description=ws.description, created_at=ws.created_at,
        updated_at=ws.updated_at, metrics=metrics,
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
            created_at=m.created_at,
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
