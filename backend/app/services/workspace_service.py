from __future__ import annotations

from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Workspace, Metric


async def create_workspace_with_metrics(
    session: AsyncSession,
    name: str,
    repo_url: str,
    description: str,
    metrics_data: list[dict],
) -> str:
    """Create a workspace and its metrics atomically. Returns workspace_id."""
    now = datetime.now(timezone.utc).isoformat()
    workspace_id = str(uuid4())

    workspace = Workspace(
        id=workspace_id,
        name=name,
        repo_url=repo_url,
        description=description,
        created_at=now,
        updated_at=now,
    )
    session.add(workspace)

    for i, m in enumerate(metrics_data):
        metric = Metric(
            id=str(uuid4()),
            workspace_id=workspace_id,
            name=m.get("name", "Unnamed Metric"),
            description=m.get("description"),
            category=m.get("category"),
            data_type=m.get("data_type", "number"),
            suggested_source=m.get("suggested_source"),
            display_order=i,
            created_at=now,
        )
        session.add(metric)

    await session.commit()
    return workspace_id
