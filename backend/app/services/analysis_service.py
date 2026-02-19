from __future__ import annotations
import asyncio

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


import json

def add_log(job: AnalysisJob, message: str):
    """Add a timestamped log entry to the job."""
    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
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
            job.progress_message = "Stage 1: Validating repository and scanning structure..."
            add_log(job, "Initializing git connection...")
            add_log(job, f"Target repository: {repo_url}")
            await session.commit()

            owner, repo = github_service.parse_repo_url(repo_url)
            file_paths = await github_service.fetch_repo_tree(owner, repo, github_token)
            job.total_files = len(file_paths)
            add_log(job, f"Found {len(file_paths)} total files in repository tree.")
            add_log(job, "Stage 1 complete.")
            await session.commit()

            # --- Stage 2: Fetching Data ---
            job.current_stage = 2
            job.progress_message = "Stage 2: Fetching relevant file contents..."
            add_log(job, "Identifying branch architecture...")
            add_log(job, "Streaming file contents to analysis buffer...")
            await session.commit()

            # --- Step 2: Fetch file contents ---
            async def on_progress(completed: int):
                job.analyzed_files = completed
                await session.commit()

            # Cap files to fetch for very large repos (files are already priority-sorted)
            MAX_FILES_TO_FETCH = 200
            if len(file_paths) > MAX_FILES_TO_FETCH:
                print(f"Large repo detected ({len(file_paths)} files). Fetching top {MAX_FILES_TO_FETCH} priority files.")
                file_paths_to_fetch = file_paths[:MAX_FILES_TO_FETCH]
            else:
                file_paths_to_fetch = file_paths

            files = await github_service.fetch_files_batch(
                owner, repo, file_paths_to_fetch, github_token, on_progress
            )

            if not files:
                job.status = "failed"
                job.error_message = "No readable files found in repository"
                add_log(job, "CRITICAL: No readable files found. Aborting.")
                await session.commit()
                return

            add_log(job, f"Fetch complete. {len(files)} files buffered.")
            add_log(job, "Stage 2 complete.")
            await session.commit()

            # --- Stage 3: Processing ---
            job.current_stage = 3
            job.status = "analyzing"
            job.progress_message = "Stage 3: Running AI-powered metrics discovery..."
            add_log(job, "Starting LLM Thought Process...")
            add_log(job, f"Using LLM: {llm_service.__name__ if hasattr(llm_service, '__name__') else 'Selected Provider'}")
            await session.commit()

            # Separate key files for project overview
            key_files = [f for f in files if get_file_priority(f["path"]) == 0]
            if not key_files:
                key_files = files[:5]
            
            # Cap Pass 1 to avoid exceeding TPM on small models/tiers
            key_files = key_files[:10]

            # Pass 1: Project overview
            add_log(job, "Pass 1: Understanding project intent and technical stack...")
            await session.commit()
            project_summary = await llm_service.analyze_project_overview(
                file_paths, key_files
            )
            add_log(job, f"Project identified as: {project_summary.get('project_name', 'Unknown')}")
            add_log(job, f"Tech stack detected: {', '.join(project_summary.get('tech_stack', []))}")

            # Pass 2: Metrics discovery (with batching if needed)
            batches = create_batches(files, max_tokens=llm_service.get_batch_token_limit())

            if len(batches) == 1:
                job.progress_message = "Pass 2: Discovering metrics..."
                await session.commit()
                metrics = await llm_service.discover_metrics(project_summary, batches[0])
            else:
                batch_results = []
                for i, batch in enumerate(batches):
                    job.progress_message = f"Pass 2: Discovering metrics (batch {i+1}/{len(batches)})..."
                    await session.commit()
                    batch_metrics = await llm_service.discover_metrics(project_summary, batch)
                    batch_results.append(batch_metrics)
                    
                    # Add a small delay between batches to avoid RPM/TPM exhaustion
                    if i < len(batches) - 1:
                        await asyncio.sleep(2)
                # Pass 3: Consolidate
                add_log(job, "Pass 3: Consolidating unique metrics and cleaning overlap...")
                await session.commit()
                metrics = await llm_service.consolidate_metrics(project_summary, batch_results)

            if not metrics:
                job.status = "failed"
                job.error_message = "LLM did not return any metrics"
                add_log(job, "ERROR: LLM failed to extract meaningful metrics.")
                await session.commit()
                return
            
            add_log(job, f"Metrics discovered: {len(metrics)} items.")
            add_log(job, "Stage 3 complete.")
            await session.commit()

            # --- Stage 4: Reporting ---
            job.current_stage = 4
            job.progress_message = "Stage 4: Generating custom visualization and workspace..."
            add_log(job, "Initializing workspace creation...")
            await session.commit()

            # --- Step 4: Create workspace ---
            project_name = project_summary.get("project_name", f"{owner}/{repo}")
            description = project_summary.get("description", "")

            job.progress_message = "Creating workspace..."
            await session.commit()
            workspace_id = await workspace_service.create_workspace_with_metrics(
                session=session,
                name=project_name,
                repo_url=repo_url,
                description=description,
                metrics_data=metrics,
                dashboard_layout=None, # Deprecated
            )

            # --- Pass 4: Generate Dashboard Code ---
            add_log(job, "Designing project-specific visualization components...")
            await session.commit()
            
            try:
                dashboard_code = await llm_service.generate_dashboard_code(project_summary, metrics, workspace_id)
                
                # Path to frontend/dashboard/src/dashboards/Workspace_{id}.tsx
                # We assume the directory exists (we created it)
                # D:\git-metrics-detector\v1\Git-metrics-detector\frontend\dashboard\src\dashboards
                # But we need absolute path logic relative to project root or use current file location
                import os
                
                # Go up from: backend/app/services/analysis_service.py -> backend/app/services -> backend/app -> backend -> root
                # Then down to frontend/dashboard/src/dashboards
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
                dash_dir = os.path.join(project_root, "frontend", "dashboard", "src", "dashboards")
                os.makedirs(dash_dir, exist_ok=True)
                
                file_path = os.path.join(dash_dir, f"Workspace_{workspace_id}.tsx")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(dashboard_code)
                    
                # Store the filename in the workspace record (re-using dashboard_config field or adding a new one)
                # For now let's just use the existence of the file or update dashboard_config to point to it
                # Actually, updating dashboard_config to "custom_code" is a good flag
                ws = await session.get(AnalysisJob, job_id)
                if ws: # Reload workspace ? No, ws is job.
                    # Update workspace record
                    from ..models import Workspace
                    w = await session.get(Workspace, workspace_id)
                    if w:
                        w.dashboard_config = "custom_code"
                        session.add(w)
                        await session.commit()

            except Exception as e:
                print(f"Failed to generate dashboard code: {e}")
                traceback.print_exc()


            # --- Step 5: Mark complete ---
            # Re-fetch job since workspace_service committed
            job = await session.get(AnalysisJob, job_id)
            job.workspace_id = workspace_id
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            add_log(job, "Analysis complete. Dashboard is ready.")
            await session.commit()

        except Exception as e:
            # Re-fetch job in case session state is stale
            try:
                job = await session.get(AnalysisJob, job_id)
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    await session.commit()
            except Exception:
                pass
            traceback.print_exc()
