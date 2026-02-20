from __future__ import annotations
import asyncio
import json
import os
import traceback
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import async_session
from ..models import AnalysisJob
from ..utils.file_filters import get_file_priority
from ..utils.token_estimator import create_batches
from . import github_service, llm_service, workspace_service
from .metabase_service import metabase_service


async def create_job(session: AsyncSession, repo_url: str, github_token: Optional[str]) -> AnalysisJob:
    """Create a new analysis job record."""
    owner, repo = github_service.parse_repo_url(repo_url)
    now = datetime.now(timezone.utc).isoformat()

    job = AnalysisJob(
        id=str(uuid4()),
        repo_url=repo_url.strip(),
        repo_owner=owner,
        repo_name=repo,
        status="pending",
        total_files=0,
        analyzed_files=0,
        created_at=now,
    )
    session.add(job)
    await session.commit()
    return job


def add_log(job: AnalysisJob, message: str):
    """Add a timestamped log entry to the job."""
    now = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{now}] {message}"
    if not job.logs:
        job.logs = json.dumps([log_entry])
    else:
        logs = json.loads(job.logs)
        logs.append(log_entry)
        job.logs = json.dumps(logs)


async def run_analysis(job_id: str, repo_url: str, github_token: Optional[str]):
    """Background task: fetch repo, analyze with Gemini AI, create workspace."""
    async with async_session() as session:
        try:
            job = await session.get(AnalysisJob, job_id)
            if not job:
                return

            # --- Stage 1: Validation ---
            job.current_stage = 1
            job.status = "fetching"
            job.progress_message = "Stage 1: Scanning repository structure..."
            add_log(job, f"Connecting to {repo_url}...")
            await session.commit()

            owner, repo = github_service.parse_repo_url(repo_url)
            file_paths = await github_service.fetch_repo_tree(owner, repo, github_token)
            job.total_files = len(file_paths)
            
            # Real Discovery Log!
            discovery = await llm_service.get_first_impressions(file_paths)
            add_log(job, discovery)
            
            add_log(job, f"Indexing complete. Processed {len(file_paths)} file nodes.")
            await session.commit()

            # --- Stage 2: Fetching Data ---
            job.current_stage = 2
            job.progress_message = "Stage 2: Fetching critical logic files..."
            add_log(job, "Prioritizing files for deep analysis...")
            await session.commit()

            async def on_progress(completed: int):
                job.analyzed_files = completed
                await session.commit()

            MAX_FILES_TO_FETCH = 200
            file_paths_to_fetch = file_paths[:MAX_FILES_TO_FETCH] if len(file_paths) > MAX_FILES_TO_FETCH else file_paths

            files = await github_service.fetch_files_batch(
                owner, repo, file_paths_to_fetch, github_token, on_progress
            )

            if not files:
                job.status = "failed"
                job.error_message = "No readable files found in repository"
                add_log(job, "CRITICAL: No readable files found. Aborting.")
                await session.commit()
                return

            add_log(job, f"Stage 2 complete: {len(files)} files buffered.")
            await session.commit()

            # --- Stage 3: Processing ---
            job.current_stage = 3
            job.status = "analyzing"
            job.progress_message = "Stage 3: Extracting metrics from codebase..."
            add_log(job, "Starting LLM Reasoning Core...")
            await session.commit()

            key_files = [f for f in files if get_file_priority(f["path"]) == 0][:10]
            if not key_files: key_files = files[:5]

            # Pass 1: Project overview
            add_log(job, "Pass 1: Identifying business domain and technical dependencies...")
            await session.commit()
            
            project_summary, pass1_thought = await llm_service.analyze_project_overview(file_paths, key_files)
            if project_summary:
                add_log(job, f"System Discovery: Detected a {project_summary.get('architecture_type', 'standard')} architecture. Core entities: {', '.join(project_summary.get('key_entities', [])[:4])}.")
            if pass1_thought:
                # Extract first two punchy sentences from the thought block
                insight = ". ".join(pass1_thought.strip().split(".")[:2])
                add_log(job, f"LLM Insight: {insight}.")
            await session.commit()

            # Pass 2: Metrics discovery
            batches = create_batches(files, max_tokens=llm_service.get_batch_token_limit())
            add_log(job, f"Deep scanning {len(batches)} batches of code for trackable patterns...")
            await session.commit()

            batch_results = []
            for i, batch in enumerate(batches):
                job.progress_message = f"Pass 2: Scanning batch {i+1}/{len(batches)}..."
                batch_metrics, batch_thought = await llm_service.discover_metrics(project_summary, batch)
                if batch_thought:
                    # Log more "discovery-like" things
                    add_log(job, f"Batch {i+1} Discovery: Found {len(batch_metrics)} indicators related to {batch_metrics[0]['category'] if batch_metrics else 'logic'}.")
                batch_results.append(batch_metrics)
                await session.commit()

            # --- Stage 4: Consolidate ---
            job.current_stage = 4
            job.progress_message = "Stage 4: Organizing metric registry..."
            add_log(job, "Filtering candidate metrics for feasibility and impact...")
            await session.commit()
            metrics, pass3_thought = await llm_service.consolidate_metrics(project_summary, batch_results)
            
            add_log(job, f"Metric Registry finalized: {len(metrics)} primary metrics identified.")
            await session.commit()

            # --- Stage 5: Reporting & Workspace Creation ---
            job.current_stage = 5
            job.progress_message = "Stage 5: Creating workspace environment..."
            add_log(job, f"Naming workspace: {project_summary.get('project_name', repo)}")
            await session.commit()

            workspace_id = await workspace_service.create_workspace_with_metrics(
                session=session, name=project_summary.get("project_name", f"{owner}/{repo}"), 
                repo_url=repo_url, description=project_summary.get("description", ""), 
                metrics_data=metrics, dashboard_layout=None,
            )
            
            job.workspace_id = workspace_id
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.progress_message = "Registry is live. Launching background reporting..."
            add_log(job, "Workspace created. Connecting visualizers...")
            await session.commit()

            # FINAL PASS: Parallel Reporting & METABASE INTEGRATION
            tasks = [
                llm_service.generate_mock_data(metrics, project_summary.get("project_name", repo), model="gemini-2.0-flash"),
                llm_service.generate_dashboard_plan(metrics, project_summary.get("project_name", repo), workspace_id, model="gemini-2.0-flash")
            ]
            
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                mock_res, plan_res = results[0], results[1]

                # 1. Mock Data Injection
                if not isinstance(mock_res, Exception) and mock_res:
                    mock_data, _ = mock_res
                    from ..models import MetricEntry, Metric as MetricModel
                    from sqlalchemy import select as sa_select
                    res = await session.execute(sa_select(MetricModel).where(MetricModel.workspace_id == workspace_id))
                    db_metrics = {m.name: m.id for m in res.scalars().all()}
                    for md in mock_data:
                        metric_id = db_metrics.get(md.get("metric_name", ""))
                        if metric_id:
                            for entry in md.get("entries", []):
                                session.add(MetricEntry(
                                    id=str(uuid4()), metric_id=metric_id, value=str(entry.get("value", "")),
                                    recorded_at=entry.get("recorded_at", datetime.now(timezone.utc).isoformat())
                                ))
                    await session.commit()
                    add_log(job, "Injected synthetic history for trend visualization.")

                # 2. METABASE INTEGRATION !!!
                if not isinstance(plan_res, Exception) and plan_res:
                    plan_data, _ = plan_res
                    add_log(job, "Configuring Metabase Open-Source Visualization Suite...")
                    
                    # Store plan in workspace for later use
                    from ..models import Workspace
                    w = await session.get(Workspace, workspace_id)
                    if w:
                        w.dashboard_config = json.dumps(plan_data)
                        await session.commit()

                    # Integration with real Metabase API
                    try:
                        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/metrics.db"))
                        mb_db_id = await metabase_service.setup_database(db_path)
                        if mb_db_id:
                            mb_url = await metabase_service.create_dashboard(project_summary.get("project_name", repo), mb_db_id, plan_data)
                            if mb_url:
                                add_log(job, f"Metabase Dashboard LIVE: {mb_url}")
                                # Store the actual URL
                                w.dashboard_config = json.dumps({"metabase_url": mb_url, "plan": plan_data})
                                await session.commit()
                            else:
                                add_log(job, "Metabase connection failed. Reaching out locally...")
                        else:
                            add_log(job, "Metabase database registration failed.")
                    except Exception as me:
                        add_log(job, f"Metabase API Error: {str(me)}")

            except Exception as e:
                add_log(job, f"Background optimization error: {str(e)}")
            
            add_log(job, "Analysis complete. Visualization suite ready.")
            await session.commit()

        except Exception as e:
            try:
                job = await session.get(AnalysisJob, job_id)
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    await session.commit()
            except Exception: pass
            traceback.print_exc()
            add_log(job, f"CRITICAL ERROR: {str(e)}")
            await session.commit()
