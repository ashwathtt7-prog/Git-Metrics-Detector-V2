import asyncio
import os
import re
from uuid import uuid4
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.database import init_db, async_session
from app.models import AnalysisJob, Workspace, Metric, MetricEntry
from app.services.analysis_service import run_analysis, create_job
from app.services import llm_service
from app.services.metabase_service import metabase_service


REPO_URL = os.getenv("TEST_REPO_URL", "https://github.com/octocat/Hello-World")


def _norm(s: str) -> str:
    return "".join(ch.lower() for ch in (s or "").strip() if ch.isalnum())


async def main():
    print(f"[E2E] Repo: {REPO_URL}")
    await init_db()

    async with async_session() as session:
        job = await create_job(session, REPO_URL, None)
        job_id = job.id
        print(f"[E2E] Job: {job_id}")

    await run_analysis(job_id, REPO_URL, None)

    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
        if not job:
            raise RuntimeError("Job not found after run_analysis")
        print(f"[E2E] Job status: {job.status}")
        if job.status != "completed":
            raise RuntimeError(job.error_message or "Analysis failed")

        ws = await session.get(Workspace, job.workspace_id)
        if not ws:
            raise RuntimeError("Workspace not found after analysis")

        res = await session.execute(select(Metric).where(Metric.workspace_id == ws.id))
        metrics = res.scalars().all()
        print(f"[E2E] Metrics: {len(metrics)}")

        metrics_data = [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "category": m.category,
                "data_type": m.data_type,
                "source_table": m.source_table,
                "source_platform": m.source_platform,
            }
            for m in metrics
        ]

    mock_data, trace = await llm_service.generate_mock_data(metrics_data, ws.name)
    print(f"[E2E] Mock trace patterns: {len((trace or {}).get('patterns') or [])}")

    async with async_session() as session:
        res = await session.execute(select(Metric).where(Metric.workspace_id == ws.id))
        metrics = res.scalars().all()
        db_metrics_by_id = {m.id: m.id for m in metrics}
        db_metrics_by_name = {_norm(m.name): m.id for m in metrics if m.name}

        entries_added = 0
        for md in mock_data or []:
            metric_id = (md.get("metric_id") or "").strip()
            metric_name = (md.get("metric_name") or "").strip()
            if metric_id and metric_id in db_metrics_by_id:
                metric_id = metric_id
            else:
                metric_id = db_metrics_by_name.get(_norm(metric_name), "")
            if not metric_id:
                continue

            for entry in md.get("entries", []) or []:
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
        print(f"[E2E] Entries added: {entries_added}")

    plan, plan_trace = await llm_service.generate_dashboard_plan(metrics_data, ws.name, ws.id)
    plan_data = plan if isinstance(plan, dict) else {"plan": plan}
    print(f"[E2E] Plan cards: {len(plan_data.get('cards') or [])}")

    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "metrics.db"))
    mb_db_id = await metabase_service.setup_database(db_path)
    if not mb_db_id:
        raise RuntimeError("Metabase DB registration failed")

    mb_url = await metabase_service.create_dashboard(ws.name, mb_db_id, plan_data, workspace_id=ws.id)
    if not mb_url:
        raise RuntimeError("Metabase dashboard creation returned no URL")
    print(f"[E2E] Metabase URL: {mb_url}")

    m = re.search(r"/public/dashboard/([a-f0-9\\-]+)$", mb_url)
    if not m:
        print("[E2E] Dashboard URL is not public; skipping public validation.")
        return

    uuid = m.group(1)
    async with httpx.AsyncClient() as client:
        pub = await client.get(f"{metabase_service.base_url}/api/public/dashboard/{uuid}", timeout=10.0)
        pub.raise_for_status()
        dashcards = (pub.json() or {}).get("dashcards") or []
        print(f"[E2E] Public dashcards: {len(dashcards)}")
        if len(dashcards) == 0:
            raise RuntimeError("Public dashboard has 0 dashcards (expected > 0)")


if __name__ == "__main__":
    asyncio.run(main())
