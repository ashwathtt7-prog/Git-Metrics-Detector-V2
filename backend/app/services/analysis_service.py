from __future__ import annotations
import asyncio
import contextlib
import json
import os
import traceback
from typing import Optional
from uuid import uuid4
from time import monotonic
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import async_session
from ..models import AnalysisJob
from ..utils.file_filters import get_file_priority
from ..utils.token_estimator import create_batches
from . import github_service, llm_service, workspace_service
from .metabase_service import metabase_service
from ..config import settings


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


def add_log(
    job: AnalysisJob,
    message: str,
    *,
    stage: int | None = None,
    pass_id: str | None = None,
    batch: int | None = None,
    kind: str | None = None,
):
    """Add a timestamped log entry to the job."""
    now = datetime.now().strftime("%H:%M:%S")

    effective_stage = stage if stage is not None else getattr(job, "current_stage", None)
    tag_parts = []
    if effective_stage:
        tag_parts.append(f"S{effective_stage}")
    if pass_id:
        tag_parts.append(pass_id)
    if batch is not None:
        tag_parts.append(f"B{batch}")
    if kind:
        tag_parts.append(kind)

    tag = f"[{'/'.join(tag_parts)}] " if tag_parts else ""
    log_entry = f"[{now}] {tag}{message}"
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
            discovery, discovery_trace = await llm_service.get_first_impressions(file_paths)
            add_log(job, discovery, stage=1, kind="LLM")
            if isinstance(discovery_trace, dict):
                for s in (discovery_trace.get("top_level_signals") or [])[:6]:
                    if isinstance(s, str) and s.strip():
                        add_log(job, f"Signal: {s.strip()}", stage=1, kind="Evidence")
            
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
            add_log(
                job,
                "Top priority fetch list: " + ", ".join(file_paths_to_fetch[:25]),
                stage=2,
                kind="Evidence",
            )

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
            if settings.gemini_service_account_file:
                add_log(job, f"LLM Auth: using Vertex service account file '{settings.gemini_service_account_file}'.", stage=3, kind="Evidence")
            add_log(job, f"LLM Model: {settings.gemini_model}", stage=3, kind="Evidence")
            await session.commit()

            key_files = [f for f in files if get_file_priority(f["path"]) == 0][:10]
            if not key_files: key_files = files[:5]
            add_log(
                job,
                "Feeding key files: " + ", ".join([kf["path"] for kf in key_files[:10]]),
                stage=3,
                pass_id="P0",
                kind="Evidence",
            )

            # Pass 1: Project overview
            add_log(job, "Pass 1: Identifying business domain and technical dependencies...")
            await session.commit()

            async def heartbeat(*, stage: int, pass_id: str, batch: int | None, label: str):
                """Emit periodic progress logs during long LLM calls.

                These are user-visible progress traces (stage/pass/batch + elapsed seconds),
                not internal chain-of-thought.
                """
                started = monotonic()
                try:
                    async with async_session() as hb_session:
                        hb_job = await hb_session.get(AnalysisJob, job_id)
                        if hb_job and hb_job.status not in ("completed", "failed"):
                            add_log(hb_job, f"{label}...", stage=stage, pass_id=pass_id, batch=batch, kind="Progress")
                            await hb_session.commit()
                except Exception:
                    pass
                # Stay alive (so cancellation works). Log periodically so the UI doesn't look stuck.
                try:
                    while True:
                        await asyncio.sleep(1.0)
                        try:
                            async with async_session() as hb_session:
                                hb_job = await hb_session.get(AnalysisJob, job_id)
                                if hb_job and hb_job.status not in ("completed", "failed"):
                                    elapsed = int(monotonic() - started)
                                    add_log(
                                        hb_job,
                                        f"{label}... (elapsed {elapsed}s)",
                                        stage=stage,
                                        pass_id=pass_id,
                                        batch=batch,
                                        kind="Progress",
                                    )
                                    await hb_session.commit()
                        except Exception:
                            pass
                except asyncio.CancelledError:
                    return

            hb_task = asyncio.create_task(heartbeat(stage=3, pass_id="P1", batch=None, label="LLM is analyzing project overview"))
            try:
                project_summary, pass1_trace = await llm_service.analyze_project_overview(file_paths, key_files)
            finally:
                hb_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await hb_task
            if project_summary:
                add_log(job, f"System Discovery: Detected a {project_summary.get('architecture_type', 'standard')} architecture. Core entities: {', '.join(project_summary.get('key_entities', [])[:4])}.")
            if isinstance(pass1_trace, dict):
                for obs in (pass1_trace.get("what_i_saw") or [])[:8]:
                    if isinstance(obs, str) and obs.strip():
                        add_log(job, f"Observation: {obs.strip()}", stage=3, pass_id="P1", kind="LLM")
                for q in (pass1_trace.get("uncertainties") or [])[:3]:
                    if isinstance(q, str) and q.strip():
                        add_log(job, f"Open question: {q.strip()}", stage=3, pass_id="P1", kind="LLM")
            await session.commit()

            # Pass 2: Metrics discovery
            # Keep batches conservative to reduce "empty response" / timeout failures on long prompts.
            batches = create_batches(files, max_tokens=int(llm_service.get_batch_token_limit() * 0.25))
            add_log(job, f"Deep scanning {len(batches)} batches of code for trackable patterns...")
            await session.commit()

            batch_results = []

            async def discover_batch(batch_files: list[dict], batch_no: int, depth: int = 0):
                """Try to discover metrics for a batch; on failure, split the batch a few times."""
                try:
                    hb = asyncio.create_task(heartbeat(stage=3, pass_id="P2", batch=batch_no, label=f"LLM is scanning batch {batch_no}"))
                    try:
                        return await llm_service.discover_metrics(project_summary, batch_files)
                    finally:
                        hb.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await hb
                except Exception as e:
                    if len(batch_files) >= 2 and depth < 2:
                        mid = max(1, len(batch_files) // 2)
                        add_log(
                            job,
                            f"Batch {batch_no} retry: splitting {len(batch_files)} files into {mid}+{len(batch_files)-mid} due to error: {str(e)[:240]}",
                            stage=3,
                            pass_id="P2",
                            batch=batch_no,
                            kind="Retry",
                        )
                        left_metrics, left_trace = await discover_batch(batch_files[:mid], batch_no, depth + 1)
                        right_metrics, right_trace = await discover_batch(batch_files[mid:], batch_no, depth + 1)
                        combined_trace = {}
                        if isinstance(left_trace, dict) or isinstance(right_trace, dict):
                            combined_trace = {
                                "batch_observations": (left_trace or {}).get("batch_observations", []) + (right_trace or {}).get("batch_observations", []),
                                "shortlist_criteria": (left_trace or {}).get("shortlist_criteria", []) or (right_trace or {}).get("shortlist_criteria", []),
                                "files_referenced": (left_trace or {}).get("files_referenced", []) + (right_trace or {}).get("files_referenced", []),
                            }
                        return left_metrics + right_metrics, combined_trace
                    # Last resort: path-only inference (never skip a batch silently).
                    try:
                        paths = [bf.get("path", "") for bf in batch_files if bf.get("path")]
                        add_log(job, f"Batch {batch_no}: falling back to path-only analysis after error: {str(e)[:240]}", stage=3, pass_id="P2", batch=batch_no, kind="Retry")
                        hb = asyncio.create_task(heartbeat(stage=3, pass_id="P2", batch=batch_no, label=f"LLM is inferring metrics from paths for batch {batch_no}"))
                        try:
                            return await llm_service.discover_metrics_from_paths(project_summary, paths)
                        finally:
                            hb.cancel()
                            with contextlib.suppress(asyncio.CancelledError):
                                await hb
                    except Exception as e2:
                        add_log(
                            job,
                            f"Batch {batch_no}: failed after retries (including path-only). Continuing with 0 metrics. Error: {str(e2)[:300]}",
                            stage=3,
                            pass_id="P2",
                            batch=batch_no,
                            kind="Error",
                        )
                        return [], {"batch_observations": [], "shortlist_criteria": [], "files_referenced": []}

            for i, batch in enumerate(batches):
                job.progress_message = f"Pass 2: Scanning batch {i+1}/{len(batches)}..."
                try:
                    add_log(
                        job,
                        f"Batch {i+1}: analyzing {len(batch)} files (sample: {', '.join([bf['path'] for bf in batch[:5]])})",
                        stage=3,
                        pass_id="P2",
                        batch=i + 1,
                        kind="Evidence",
                    )
                    batch_metrics, batch_trace = await discover_batch(batch, i + 1)
                    add_log(
                        job,
                        f"Batch {i+1}: shortlisted {len(batch_metrics)} metric candidates.",
                        stage=3,
                        pass_id="P2",
                        batch=i + 1,
                        kind="LLM",
                    )
                    if isinstance(batch_trace, dict):
                        for obs in (batch_trace.get("batch_observations") or [])[:8]:
                            if isinstance(obs, str) and obs.strip():
                                add_log(job, f"Batch {i+1} observation: {obs.strip()}", stage=3, pass_id="P2", batch=i + 1, kind="LLM")
                        for c in (batch_trace.get("shortlist_criteria") or [])[:6]:
                            if isinstance(c, str) and c.strip():
                                add_log(job, f"Batch {i+1} criterion: {c.strip()}", stage=3, pass_id="P2", batch=i + 1, kind="LLM")
                        for p in (batch_trace.get("files_referenced") or [])[:12]:
                            if isinstance(p, str) and p.strip():
                                add_log(job, f"Batch {i+1} file referenced: {p.strip()}", stage=3, pass_id="P2", batch=i + 1, kind="Evidence")

                    for m in (batch_metrics or []):
                        try:
                            name = m.get("name")
                            cat = m.get("category")
                            src = m.get("suggested_source") or m.get("source_table") or m.get("source_platform")
                            if name:
                                add_log(
                                    job,
                                    f"Candidate: {name} ({cat}) - source hint: {src}",
                                    stage=3,
                                    pass_id="P2",
                                    batch=i + 1,
                                    kind="Metric",
                                )
                                ev = m.get("evidence")
                                if isinstance(ev, list):
                                    for evi in ev[:2]:
                                        if isinstance(evi, dict) and evi.get("path") and evi.get("signal"):
                                            add_log(
                                                job,
                                                f"Evidence: {evi.get('path')} - {evi.get('signal')}",
                                                stage=3,
                                                pass_id="P2",
                                                batch=i + 1,
                                                kind="Evidence",
                                            )
                        except Exception:
                            pass
                    batch_results.append(batch_metrics)
                except Exception as batch_err:
                    job.status = "failed"
                    job.error_message = f"Metric discovery failed in batch {i+1}: {str(batch_err)[:600]}"
                    add_log(job, f"CRITICAL: {job.error_message}", stage=3, pass_id="P2", batch=i + 1, kind="Error")
                    await session.commit()
                    return
                await session.commit()

            # --- Stage 4: Consolidate ---
            job.current_stage = 4
            job.progress_message = "Stage 4: Organizing metric registry..."
            add_log(job, "Pass 3: Consolidating, deduplicating, and ranking metrics...")
            try:
                total_candidates = sum(len(b or []) for b in batch_results or [])
                add_log(job, f"Consolidation input: {len(batch_results)} batches, {total_candidates} total candidates.", stage=4, pass_id="P3", kind="Evidence")
            except Exception:
                pass
            await session.commit()
            hb_task = asyncio.create_task(heartbeat(stage=4, pass_id="P3", batch=None, label="LLM is consolidating metric registry"))
            try:
                metrics, pass3_trace = await llm_service.consolidate_metrics(project_summary, batch_results)
            finally:
                hb_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await hb_task
            if isinstance(pass3_trace, dict):
                for r in (pass3_trace.get("dedup_rules") or [])[:8]:
                    if isinstance(r, str) and r.strip():
                        add_log(job, f"Dedup rule: {r.strip()}", stage=4, pass_id="P3", kind="LLM")
                for merge in (pass3_trace.get("merged") or [])[:8]:
                    if isinstance(merge, dict):
                        frm = merge.get("from")
                        to = merge.get("to")
                        reason = merge.get("reason")
                        if frm and to:
                            add_log(job, f"Merged: {', '.join(frm) if isinstance(frm, list) else frm} -> {to} ({reason})", stage=4, pass_id="P3", kind="LLM")
                for drop in (pass3_trace.get("dropped") or [])[:8]:
                    if isinstance(drop, dict) and drop.get("name"):
                        add_log(job, f"Dropped: {drop.get('name')} ({drop.get('reason')})", stage=4, pass_id="P3", kind="LLM")
            
            add_log(job, f"Metric Registry finalized: {len(metrics)} primary metrics identified.")
            for idx, m in enumerate(metrics or [], start=1):
                try:
                    name = m.get("name")
                    cat = m.get("category")
                    dt = m.get("data_type")
                    src = m.get("suggested_source") or m.get("source_table") or m.get("source_platform")
                    if name:
                        add_log(job, f"Rank {idx}: {name} ({cat}/{dt}) - source: {src}", stage=4, pass_id="P3", kind="Metric")
                except Exception:
                    pass
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
            from ..models import Metric as MetricModel
            from sqlalchemy import select as sa_select
            res = await session.execute(sa_select(MetricModel).where(MetricModel.workspace_id == workspace_id))
            db_metric_rows = res.scalars().all()
            metrics_for_reporting = [
                {
                    "id": m.id,
                    "name": m.name,
                    "description": m.description,
                    "category": m.category,
                    "data_type": m.data_type,
                    "suggested_source": m.suggested_source,
                    "source_table": m.source_table,
                    "source_platform": m.source_platform,
                }
                for m in db_metric_rows
            ]
            tasks = [
                llm_service.generate_mock_data(metrics_for_reporting, project_summary.get("project_name", repo)),
                llm_service.generate_dashboard_plan(metrics_for_reporting, project_summary.get("project_name", repo), workspace_id)
            ]
            
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                mock_res, plan_res = results[0], results[1]

                # 1. Mock Data Injection
                if not isinstance(mock_res, Exception) and mock_res:
                    mock_data, mock_trace = mock_res
                    from ..models import MetricEntry
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

                    db_metrics_by_id = {m["id"]: m["id"] for m in metrics_for_reporting if m.get("id")}
                    def _norm(s: str) -> str:
                        return "".join(ch.lower() for ch in s.strip() if ch.isalnum())
                    db_metrics_by_name = {_norm(m["name"]): m["id"] for m in metrics_for_reporting if m.get("name") and m.get("id")}
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
                            session.add(MetricEntry(
                                id=str(uuid4()), metric_id=metric_id, value=str(entry.get("value", "")),
                                recorded_at=_safe_ts(entry.get("recorded_at"), fallback_days_ago=(29 - (idx % 30))),
                            ))
                    await session.commit()
                    add_log(job, "Injected synthetic history for trend visualization.")
                    if isinstance(mock_trace, dict):
                        for p in (mock_trace.get("patterns") or [])[:8]:
                            if isinstance(p, str) and p.strip():
                                add_log(job, f"Mock pattern: {p.strip()}", stage=5, kind="LLM")

                # 2. METABASE INTEGRATION !!!
                if not isinstance(plan_res, Exception) and plan_res:
                    plan_data, plan_trace = plan_res
                    add_log(job, "Configuring Metabase Open-Source Visualization Suite...")
                    
                    # Store plan in workspace for later use
                    from ..models import Workspace
                    w = await session.get(Workspace, workspace_id)
                    if w:
                        cfg = plan_data if isinstance(plan_data, dict) else {"plan": plan_data}
                        if isinstance(plan_trace, dict) and plan_trace:
                            cfg["trace"] = plan_trace
                        w.dashboard_config = json.dumps(cfg)
                        await session.commit()
                        if isinstance(plan_trace, dict):
                            for d in (plan_trace.get("design_choices") or [])[:10]:
                                if isinstance(d, str) and d.strip():
                                    add_log(job, f"Dashboard design: {d.strip()}", stage=5, kind="LLM")

                    # Integration with real Metabase API
                    try:
                        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/metrics.db"))
                        mb_db_id = await metabase_service.setup_database(db_path)
                        if mb_db_id:
                            mb_url = await metabase_service.create_dashboard(
                                project_summary.get("project_name", repo),
                                mb_db_id,
                                plan_data,
                                workspace_id=workspace_id,
                            )
                            if mb_url:
                                add_log(job, f"Metabase Dashboard LIVE: {mb_url}")
                                # Store the actual URL
                                cfg2 = {"metabase_url": mb_url, "plan": plan_data}
                                if isinstance(plan_trace, dict) and plan_trace:
                                    cfg2["trace"] = plan_trace
                                w.dashboard_config = json.dumps(cfg2)
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
