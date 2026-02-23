from __future__ import annotations

import json
import re
import logging
import random
from datetime import datetime, timedelta, timezone

from .llm.provider_chain import LLMProviderChain
from .llm.gemini_provider import GeminiProvider
from .llm.groq_provider import GroqProvider
from .llm.openrouter_provider import OpenRouterProvider
from .llm.ollama_provider import OllamaProvider
from ..config import settings

logger = logging.getLogger(__name__)

_chain: LLMProviderChain | None = None


def _get_chain() -> LLMProviderChain:
    global _chain
    if _chain is None:
        gemini = GeminiProvider()

        # If a Gemini service account file is configured and resolvable, force ALL calls
        # to use Vertex Gemini (no provider fallback). This matches the UI expectation
        # that analysis is consistent and avoids mixing providers.
        sa_path = None
        try:
            sa_path = gemini._get_service_account_path()  # type: ignore[attr-defined]
        except Exception:
            sa_path = None

        if settings.gemini_service_account_file and not sa_path:
            raise RuntimeError(
                f"GEMINI_SERVICE_ACCOUNT_FILE is set to '{settings.gemini_service_account_file}', "
                "but the file could not be found. Fix the path before running analysis."
            )

        if sa_path:
            _chain = LLMProviderChain([gemini])
        else:
            providers = [
                gemini,
                OpenRouterProvider(),
                GroqProvider(),
                OllamaProvider(),
            ]

            preferred = (settings.llm_provider or "").strip().lower()
            if preferred:
                order = {
                    "gemini": GeminiProvider,
                    "openrouter": OpenRouterProvider,
                    "groq": GroqProvider,
                    "ollama": OllamaProvider,
                }
                preferred_cls = order.get(preferred)
                if preferred_cls:
                    providers.sort(key=lambda p: 0 if isinstance(p, preferred_cls) else 1)

            _chain = LLMProviderChain(providers)
    return _chain


def get_batch_token_limit() -> int:
    """Return the safe token limit for batching, based on available providers."""
    return _get_chain().get_max_context_tokens()


def _format_files_for_prompt(files: list[dict]) -> str:
    parts = []
    for f in files:
        content = f.get("content") or ""
        if not isinstance(content, str):
            content = str(content)
        max_chars = int(getattr(settings, "llm_max_file_chars", 6000) or 6000)
        if max_chars > 0 and len(content) > max_chars:
            omitted = len(content) - max_chars
            content = content[:max_chars] + f"\n\n...[truncated {omitted} chars]...\n"
        parts.append(f"--- {f['path']} ---\n{content}\n")
    return "\n".join(parts)


def _heuristic_metric_fallback(
    *,
    project_summary: dict | None,
    file_paths: list[str],
    max_metrics: int = 12,
) -> tuple[list[dict], dict]:
    """Deterministic, no-LLM metric proposal used when providers fail.

    This is intentionally conservative: it produces actionable defaults and references
    file/path signals (no code snippets) so the UI can still show "what it saw".
    """
    def norm(s: str) -> str:
        return "".join(ch.lower() for ch in (s or "").strip() if ch.isalnum())

    paths = [p for p in file_paths if isinstance(p, str) and p.strip()]
    paths_l = [p.lower() for p in paths]

    signals: list[str] = []
    def has_any(keys: list[str]) -> bool:
        return any(any(k in p for k in keys) for p in paths_l)

    if has_any(["package.json", "pnpm-lock", "yarn.lock", "vite.config", "next.config"]):
        signals.append("Detected Node/JS frontend/backend signals (package.json / Vite/Next).")
    if has_any(["requirements.txt", "pyproject.toml", "poetry.lock", "pipfile"]):
        signals.append("Detected Python signals (requirements/pyproject).")
    if has_any(["dockerfile", "docker-compose", ".github/workflows"]):
        signals.append("Detected deployment/CI signals (Docker / GitHub Actions).")
    if has_any(["migrations", "schema", "prisma", "sequelize", "alembic"]):
        signals.append("Detected database schema/migration signals (migrations/schema tooling).")
    if has_any(["routes", "controller", "handler", "api/", "routers", "endpoints"]):
        signals.append("Detected API surface signals (routes/controllers/handlers).")
    if has_any(["auth", "login", "signup", "jwt", "oauth"]):
        signals.append("Detected authentication signals (auth/login/jwt/oauth).")
    if has_any(["redis", "cache"]):
        signals.append("Detected caching signals (redis/cache).")
    if has_any(["stripe", "payment", "billing", "invoice", "subscription"]):
        signals.append("Detected billing signals (stripe/payment/subscription).")

    # Domain-ish hints from project summary if present
    domain = ""
    entities: list[str] = []
    if isinstance(project_summary, dict):
        domain = str(project_summary.get("domain") or "").strip()
        ent = project_summary.get("key_entities") or []
        if isinstance(ent, list):
            entities = [str(e) for e in ent if isinstance(e, (str, int, float))]

    observations = signals[:8] if signals else ["No strong framework/domain signals from paths; using safe default metric set."]

    # Build metric list (avoid duplicates by normalized name)
    metrics: list[dict] = []
    seen: set[str] = set()

    def add_metric(
        name: str,
        description: str,
        category: str,
        data_type: str,
        suggested_source: str,
        *,
        source_table: str = "metric_entries",
        source_platform: str = "SQLite",
        evidence_paths: list[str] | None = None,
    ):
        key = norm(name)
        if not key or key in seen:
            return
        seen.add(key)
        ev = []
        for p in (evidence_paths or [])[:3]:
            ev.append({"path": p, "signal": "Path signal used for heuristic fallback."})
        metrics.append(
            {
                "name": name,
                "description": description,
                "category": category,
                "data_type": data_type,
                "suggested_source": suggested_source,
                "source_table": source_table,
                "source_platform": source_platform,
                "estimated_value": "",
                "evidence": ev,
            }
        )

    top_paths = paths[:25]

    # Always include core performance/health metrics (works for any app)
    add_metric(
        "API Error Rate",
        "Percentage of requests resulting in 4xx/5xx errors.",
        "performance",
        "percentage",
        "Instrument HTTP layer / middleware; aggregate status codes over time.",
        evidence_paths=top_paths,
    )
    add_metric(
        "API Latency (P95)",
        "95th percentile response time for API requests.",
        "performance",
        "number",
        "Record request duration in middleware; compute P95 daily.",
        evidence_paths=top_paths,
    )
    add_metric(
        "Request Volume",
        "Total API requests per day.",
        "performance",
        "number",
        "Count requests at the HTTP entrypoint (routes/controllers).",
        evidence_paths=top_paths,
    )

    # Add auth/business hints
    if has_any(["auth", "login", "signup", "jwt", "oauth"]):
        add_metric(
            "Login Success Rate",
            "Percentage of login attempts that succeed.",
            "engagement",
            "percentage",
            "Track auth/login endpoints; success vs failure counts.",
            evidence_paths=[p for p in paths if "auth" in p.lower() or "login" in p.lower()][:25],
        )
        add_metric(
            "Active Users (Daily)",
            "Unique users active per day (based on session/auth events).",
            "engagement",
            "number",
            "Derive from session creation or authenticated requests.",
            evidence_paths=[p for p in paths if "auth" in p.lower() or "user" in p.lower()][:25],
        )

    if has_any(["stripe", "payment", "billing", "invoice", "subscription"]) or "billing" in domain.lower():
        add_metric(
            "Payment Success Rate",
            "Percentage of payment intents/charges that succeed.",
            "business",
            "percentage",
            "Track payment provider callbacks or billing service results.",
            evidence_paths=[p for p in paths if any(k in p.lower() for k in ["stripe", "payment", "billing"])][:25],
        )
        add_metric(
            "New Subscriptions (Daily)",
            "Count of new subscriptions created per day.",
            "growth",
            "number",
            "Track subscription creation events in billing workflows.",
            evidence_paths=[p for p in paths if "subscription" in p.lower()][:25],
        )

    if has_any(["redis", "cache"]):
        add_metric(
            "Cache Hit Rate",
            "Percentage of cache lookups that are hits.",
            "performance",
            "percentage",
            "Instrument cache wrapper; hits/(hits+misses).",
            evidence_paths=[p for p in paths if "cache" in p.lower() or "redis" in p.lower()][:25],
        )

    if has_any(["migrations", "schema", "prisma", "sequelize", "alembic"]) or has_any(["db", "database"]):
        add_metric(
            "Database Query Latency (Avg)",
            "Average latency of database queries.",
            "performance",
            "number",
            "Instrument ORM/database client timings; average daily.",
            evidence_paths=[p for p in paths if any(k in p.lower() for k in ["migrations", "schema", "prisma", "alembic", "db"])][:25],
        )

    # If key entities are present, add a generic "entity created" metric for the first 1-2 entities
    for ent in entities[:2]:
        ent_s = str(ent).strip()
        if not ent_s:
            continue
        add_metric(
            f"New {ent_s} Created (Daily)",
            f"Count of new {ent_s} records created per day.",
            "content" if ent_s.lower() in ["post", "comment", "article", "document"] else "business",
            "number",
            f"Track create operations for {ent_s} (DB insert or create endpoint).",
            evidence_paths=top_paths,
        )

    # Ensure at least a small set
    if len(metrics) < 6:
        add_metric(
            "Background Job Failures",
            "Count of background/async job failures per day.",
            "performance",
            "number",
            "Track task runner/job queue errors (worker logs).",
            evidence_paths=top_paths,
        )
        add_metric(
            "Feature Adoption (Top Feature)",
            "Daily count of a key feature action (project-specific).",
            "engagement",
            "number",
            "Track a core endpoint/event that represents feature usage.",
            evidence_paths=top_paths,
        )

    metrics = metrics[:max_metrics]
    trace = {
        "fallback": True,
        "fallback_reason": "LLM providers failed; generated a heuristic metric set from file-path signals.",
        "batch_observations": observations,
        "shortlist_criteria": [
            "Prefer metrics that can be measured from request logs / DB events",
            "Include at least 3 performance/health indicators",
            "Add domain/auth/billing metrics when path signals exist",
            "Reference only file/path evidence (no code snippets)",
        ],
        "files_referenced": paths[: min(15, len(paths))],
    }
    return metrics, trace


def _parse_json_with_thought(raw: str) -> tuple[dict, str]:
    """Parse LLM JSON response and extract legacy <thinking> block (if present).

    Note: We prefer returning shareable trace info inside the JSON payload (under a
    `trace` key). The <thinking> tag is treated as legacy and should not be shown
    to end users as a "full thought process".
    """
    if not raw or not isinstance(raw, str):
        raise ValueError(f"LLM returned empty or non-string response: {type(raw)}")
    thought = ""
    # Search for thinking block - case insensitive and handle missing closing tag
    thought_match = re.search(r"<thinking>([\s\S]*?)(?:</thinking>|$)", raw, re.IGNORECASE)
    if thought_match:
        thought = thought_match.group(1).strip()
    
    # Remove thinking block to find JSON
    # Be more careful: only remove until the start of a JSON block if possible
    json_start = raw.find("```json")
    if json_start == -1:
        json_start = raw.find("{")
    
    if json_start != -1:
        # Extract thought from before the JSON
        pre_json = raw[:json_start]
        thought_match = re.search(r"<thinking>([\s\S]*?)(?:</thinking>|$)", pre_json, re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()
        clean_raw = raw[json_start:].strip()
    else:
        # Fallback to old behavior
        clean_raw = re.sub(r"<thinking>[\s\S]*?(?:</thinking>|$)", "", raw, flags=re.IGNORECASE).strip()

    # Try direct JSON load
    if clean_raw:
        try:
            return json.loads(clean_raw), thought
        except json.JSONDecodeError:
            pass

    # Try finding JSON in markdown blocks (use greedy match for inner content)
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", clean_raw)
    if not match:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_raw)
    
    if match:
        try:
            return json.loads(match.group(1)), thought
        except json.JSONDecodeError:
            pass

    # Try finding the first { and last }
    match = re.search(r"(\{[\s\S]*\})", clean_raw)
    if not match:
        # If no closing bracket, maybe it's truncated? 
        # Try to find the start and then append closing brackets
        start_match = re.search(r"(\{[\s\S]*)", clean_raw)
        if start_match:
            candidate = start_match.group(1).strip()
            # Crude recovery: count open brackets/braces and append missing ones
            open_braces = candidate.count("{") - candidate.count("}")
            open_brackets = candidate.count("[") - candidate.count("]")
            candidate += "}" * max(0, open_braces)
            candidate += "]" * max(0, open_brackets)
            try:
                return json.loads(candidate), thought
            except:
                pass
    else:
        candidate = match.group(1)
        try:
            return json.loads(candidate), thought
        except json.JSONDecodeError:
            # Last ditch: try to fix common JSON errors like trailing commas
            try:
                # Remove trailing commas before closing braces/brackets
                fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
                return json.loads(fixed), thought
            except json.JSONDecodeError:
                pass

    # Even more desperate: try to find "mock_data": [...] or "metrics": [...]
    for key in ["mock_data", "metrics", "cards"]:
        match = re.search(rf'"{key}"\s*:\s*(\[[\s\S]*\])', clean_raw)
        if match:
            try:
                data = json.loads(match.group(1))
                return {key: data}, thought
            except:
                pass

    logger.error(f"Failed to parse JSON from LLM. Raw response length: {len(raw)}")
    logger.debug(f"Raw response: {raw}")
    raise ValueError(f"Could not parse LLM response as JSON. This usually happens when the AI provides too much text or invalid formatting. Raw preview: {raw[:200]}...")


def _parse_json_response(raw: str) -> dict:
    """Legacy parser for backward compatibility."""
    res, _ = _parse_json_with_thought(raw)
    return res


def _parse_json_with_trace(raw: str) -> tuple[dict, dict]:
    """Parse JSON and extract a shareable `trace` object (if present)."""
    res, _legacy_thought = _parse_json_with_thought(raw)
    trace: dict = {}
    if isinstance(res, dict):
        candidate = res.get("trace")
        if isinstance(candidate, dict):
            trace = candidate
    return res, trace


async def _call_llm(prompt: str, model: str | None = None) -> str:
    chain = _get_chain()
    return await chain.generate(prompt, model_override=model)


async def analyze_project_overview(file_tree: list[str], key_files: list[dict]) -> tuple[dict, dict]:
    """Pass 1: Get a high-level understanding of the project."""
    tree_str = "\n".join(file_tree)
    files_str = _format_files_for_prompt(key_files)

    prompt = f"""You are an expert software analyst. You are given the contents of a software repository. Your job is to understand what this project does, its technology stack, its domain, and its architecture.

Here is the repository file tree:
{tree_str}

Here are the key files:
{files_str}

Respond in the following format:
```json
{{
  "trace": {{
    "what_i_saw": ["3-8 short, specific observations with file/path evidence"],
    "key_files_used": ["list of key file paths you relied on most"],
    "uncertainties": ["0-3 open questions / uncertainties (optional)"]
  }},
  "project_name": "string",
  "description": "A 2-3 sentence summary of what this project does",
  "domain": "string (e.g., e-commerce, social media, SaaS, developer tool, etc.)",
  "tech_stack": ["list", "of", "technologies"],
  "architecture_type": "string (e.g., monolith, microservices, serverless, SPA+API, etc.)",
  "key_entities": ["list of core domain entities (e.g., User, Product, Order, etc.)"],
  "has_frontend": true,
  "has_backend": true,
  "has_database": true
}}"""

    def fallback() -> tuple[dict, dict]:
        # Minimal, deterministic fallback so the rest of the pipeline can proceed.
        tree_sample = [p for p in (file_tree or []) if isinstance(p, str) and p.strip()][:120]
        key_paths = [kf.get("path") for kf in (key_files or []) if isinstance(kf, dict) and kf.get("path")]
        project_name = ""
        if tree_sample:
            # Try to infer name from the top-level folder naming (best-effort).
            project_name = (tree_sample[0].split("/")[0] if "/" in tree_sample[0] else "").strip()
        trace = {
            "fallback": True,
            "what_i_saw": [
                f"Repository tree sample contains {len(tree_sample)} paths (used for fallback classification).",
                f"Key files provided: {', '.join([str(p) for p in key_paths[:8]])}" if key_paths else "No key files provided.",
            ],
            "key_files_used": [str(p) for p in key_paths[:12]],
            "uncertainties": ["LLM overview failed; domain/stack may be incomplete."],
        }
        summary = {
            "project_name": project_name or "Unknown Project",
            "description": "Project overview unavailable due to LLM failure; continuing with best-effort metric discovery.",
            "domain": "unknown",
            "tech_stack": [],
            "architecture_type": "unknown",
            "key_entities": [],
            "has_frontend": True,
            "has_backend": True,
            "has_database": True,
        }
        return summary, trace

    try:
        raw = await _call_llm(prompt)
        result, trace = _parse_json_with_trace(raw)
        if isinstance(result, dict) and isinstance(result.get("trace"), dict):
            result.pop("trace", None)
        if isinstance(result, dict) and result.get("project_name"):
            return result, trace
        return fallback()
    except Exception as e:
        logger.warning(f"[Overview] LLM failed, using fallback: {type(e).__name__}: {str(e)[:200]}")
        return fallback()


async def discover_metrics(project_summary: dict, files: list[dict]) -> tuple[list[dict], dict]:
    """Pass 2: Discover trackable metrics from the codebase."""
    summary_str = json.dumps(project_summary, indent=2)
    files_str = _format_files_for_prompt(files)

    prompt = f"""You are an expert software analyst specializing in identifying trackable business and technical metrics for software projects.

PROJECT CONTEXT:
{summary_str}

CODEBASE FILES:
{files_str}

Based on your analysis of this codebase, identify all meaningful metrics that could be tracked for this project. Consider:

1. **Business/Domain Metrics**: Metrics specific to what this application does (e.g., for e-commerce: product count, order volume, cart abandonment rate)
2. **User Engagement Metrics**: How users interact with the application (e.g., page views, click-through rates, session duration, feature adoption)
3. **Content Metrics**: What content the application manages (e.g., number of posts, media uploads, categories)
4. **Technical/Performance Metrics**: Code quality and system health indicators (e.g., API response times, error rates, test coverage)
5. **Growth Metrics**: Indicators of project/user growth (e.g., new user signups, active users, retention rate)

For each metric, provide:
- A clear, concise name
- A description of what it measures and why it matters
- A category (one of: business, engagement, content, performance, growth)
- The data type (number, percentage, boolean, string)
- A suggested source: where in the codebase or infrastructure this metric could be measured (reference specific files, database tables, or API endpoints you found in the code)
- A source_table: the specific database table, API endpoint, or data collection where this metric can be found (e.g., 'users', 'orders', 'api_access_logs', '/api/v1/metrics'). Infer from the codebase.
- A source_platform: the platform or system where this data lives (e.g., 'PostgreSQL', 'GCP BigQuery', 'Oracle DB', 'MongoDB', 'REST API', 'Application Logs', 'GitHub API'). Infer from the detected tech stack.

Respond in the following format:
```json
{{
  "trace": {{
    "batch_observations": ["3-8 short, specific observations with file/path evidence"],
    "shortlist_criteria": ["3-6 criteria you used to keep vs drop metrics"],
    "files_referenced": ["up to 15 file paths you relied on most"]
  }},
  "metrics": [
      {{
        "name": "string",
        "description": "string",
        "category": "business|engagement|content|performance|growth",
        "data_type": "number|percentage|boolean|string",
        "suggested_source": "string describing where to measure this",
        "source_table": "string - the specific database table, API endpoint, or data collection",
        "source_platform": "string - the infrastructure platform (e.g., GCP, AWS, Oracle, PostgreSQL, MongoDB)",
        "estimated_value": "string or number",
        "evidence": [
          {{
            "path": "file path / endpoint / table name (no code snippets)",
            "signal": "what you saw there that justifies this metric"
          }}
        ]
      }}
  ]
}}
```
Return between 5 and 15 metrics, ordered by importance. Focus on metrics that are specific and actionable for THIS particular project, not generic software metrics. Avoid vague metrics like "code quality" -- be specific."""

    try:
        raw = await _call_llm(prompt)
        result, trace = _parse_json_with_trace(raw)
        metrics = []
        if isinstance(result, dict):
            metrics = result.get("metrics", []) or []
            result.pop("trace", None)
        if metrics:
            return metrics, trace
    except Exception as e:
        logger.warning(f"[DiscoverMetrics] LLM failed, using heuristic fallback: {type(e).__name__}: {str(e)[:200]}")
        paths = [f.get("path", "") for f in files if isinstance(f, dict) and f.get("path")]
        return _heuristic_metric_fallback(project_summary=project_summary, file_paths=paths)

    # If LLM returned no metrics, fall back deterministically.
    paths = [f.get("path", "") for f in files if isinstance(f, dict) and f.get("path")]
    return _heuristic_metric_fallback(project_summary=project_summary, file_paths=paths)


async def consolidate_metrics(project_summary: dict, batch_results: list[list[dict]]) -> tuple[list[dict], dict]:
    """Pass 3: Consolidate metrics from multiple batches (only if batching was needed)."""
    summary_str = json.dumps(project_summary, indent=2)

    all_metrics = []
    for i, batch in enumerate(batch_results):
        all_metrics.append(f"Batch {i + 1}:")
        all_metrics.append(json.dumps(batch, indent=2))
    metrics_str = "\n".join(all_metrics)

    prompt = f"""You previously analyzed a software project in multiple batches and discovered the following metrics:

PROJECT CONTEXT:
{summary_str}

BATCH RESULTS:
{metrics_str}

Please consolidate these into a single, deduplicated, ranked list of the most important and actionable metrics for this project. Remove duplicates, merge overlapping metrics, and ensure the final list is between 8 and 25 metrics.

Respond in the following JSON format exactly:
{{
  "trace": {{
    "dedup_rules": ["3-8 rules you used to merge / dedup"],
    "merged": [{{"from": ["old metric names"], "to": "new metric name", "reason": "why merged"}}],
    "dropped": [{{"name": "dropped metric name", "reason": "why dropped"}}]
  }},
  "metrics": [
    {{
      "name": "string",
      "description": "string",
      "category": "business|engagement|content|performance|growth",
      "data_type": "number|percentage|boolean|string",
      "suggested_source": "string describing where to measure this",
      "source_table": "string - the specific database table, API endpoint, or data collection",
      "source_platform": "string - the infrastructure platform (e.g., GCP, AWS, Oracle, PostgreSQL, MongoDB)",
      "estimated_value": "string or number"
    }}
  ]
}}"""

    def fallback_consolidate() -> tuple[list[dict], dict]:
        def norm(s: str) -> str:
            return "".join(ch.lower() for ch in (s or "").strip() if ch.isalnum())

        flat: list[dict] = []
        for b in batch_results or []:
            if isinstance(b, list):
                for m in b:
                    if isinstance(m, dict) and m.get("name"):
                        flat.append(m)
        dedup: dict[str, dict] = {}
        merged: list[dict] = []
        for m in flat:
            k = norm(str(m.get("name") or ""))
            if not k:
                continue
            if k in dedup:
                merged.append({"from": [dedup[k].get("name"), m.get("name")], "to": dedup[k].get("name"), "reason": "Normalized name duplicate"})
                continue
            dedup[k] = m
        metrics_out = list(dedup.values())[:25]
        trace_out = {
            "fallback": True,
            "dedup_rules": [
                "Normalize names (alnum lower) and merge duplicates",
                "Keep first-seen metric when duplicates occur",
            ],
            "merged": merged[:10],
            "dropped": [],
        }
        return metrics_out, trace_out

    try:
        raw = await _call_llm(prompt)
        result, trace = _parse_json_with_trace(raw)
        metrics = []
        if isinstance(result, dict):
            metrics = result.get("metrics", []) or []
            result.pop("trace", None)
        if metrics:
            return metrics, trace
        return fallback_consolidate()
    except Exception as e:
        logger.warning(f"[Consolidate] LLM failed, using fallback: {type(e).__name__}: {str(e)[:200]}")
        return fallback_consolidate()


async def discover_metrics_from_paths(project_summary: dict, file_paths: list[str]) -> tuple[list[dict], dict]:
    """Fallback for Pass 2: discover metrics using file paths only (no source contents)."""
    summary_str = json.dumps(project_summary, indent=2)
    paths_str = "\n".join(file_paths[:400])

    prompt = f"""You are an expert software analyst specializing in identifying trackable business and technical metrics for software projects.

PROJECT CONTEXT:
{summary_str}

FILE PATHS (no source code provided):
{paths_str}

Infer the most likely meaningful metrics from the project context and file-path signals. Only propose metrics you can justify from the paths and detected tech stack.

Respond in the following format:
```json
{{
  "trace": {{
    "batch_observations": ["3-10 path-based signals you used (reference specific paths)"],
    "shortlist_criteria": ["3-8 criteria you used to keep vs drop metrics"],
    "files_referenced": ["up to 20 file paths you relied on most"]
  }},
  "metrics": [
      {{
        "name": "string",
        "description": "string",
        "category": "business|engagement|content|performance|growth",
        "data_type": "number|percentage|boolean|string",
        "suggested_source": "string describing where to measure this (paths/endpoints/tables)",
        "source_table": "string - inferred table/endpoint/log source",
        "source_platform": "string - inferred platform (PostgreSQL/MongoDB/REST API/etc)",
        "estimated_value": "string or number"
      }}
  ]
}}
```
Return between 5 and 12 metrics, ordered by importance."""

    try:
        raw = await _call_llm(prompt)
        result, trace = _parse_json_with_trace(raw)
        metrics = []
        if isinstance(result, dict):
            metrics = result.get("metrics", []) or []
            result.pop("trace", None)
        if metrics:
            return metrics, trace
    except Exception as e:
        logger.warning(f"[DiscoverPaths] LLM failed, using heuristic fallback: {type(e).__name__}: {str(e)[:200]}")
        return _heuristic_metric_fallback(project_summary=project_summary, file_paths=file_paths)

    return _heuristic_metric_fallback(project_summary=project_summary, file_paths=file_paths)


async def generate_dashboard_code(project_summary: dict, metrics: list[dict], workspace_id: str, model: str | None = None) -> str:
    """Pass 4: Generate a React component for the dashboard."""
    summary_str = json.dumps(project_summary, indent=2)
    metrics_str = json.dumps(metrics, indent=2)

    safe_id = workspace_id.replace("-", "")

    prompt = f"""You are an expert React developer specializing in data visualization with Recharts and Tailwind CSS.

    Your task is to generate a COMPLETE, self-contained React functional component that serves as a dashboard for a specific software project.

    PROJECT CONTEXT:
    {summary_str}

    DETECTED METRICS (with estimated values):
    {metrics_str}

    REQUIREMENTS:
    1. **Component Name**: The component MUST be named `WorkspaceDashboard` and exported as `default`.
    2. **Props**: The component will receive a single prop `metrics` which is an array of objects: `{{ metric: string; value: number; display_value: string; category: string }}`.
       - You MUST use this `metrics` prop to populate your charts.
       - Do NOT hardcode data. Filter the `metrics` array by `metric` name to find the data you need for each chart.
    3. **Libraries**:
       - Use `recharts` for all charts (BarChart, PieChart, LineChart, AreaChart).
       - Use Tailwind CSS classes for styling (the project has a WHITE background).
       - Create beautiful, modern cards with `bg-white border border-gray-200 shadow-sm rounded-xl`.
       - Text should be `text-gray-800` or `text-gray-500`.
       - Accent color is red (`#ef4444` / `text-red-500` / `bg-red-500`).
    4. **Layout**:
       - Create a masonry-like or grid layout to display the metrics logically.
       - Group related metrics (e.g., "Performance", "Growth", "Content").
       - At the top, show Key Performance Indicators (KPIs) as big cards.
    5. **Creativity**:
       - Choose the best visualization for each metric (e.g., Pie for distribution, Bar for comparison).
       - If a metric implies a trend or progress, and you only have a single value, maybe use a Progress bar or a radial bar if possible, or just a nice card.

    IMPORTS AVAILABLE:
    - `import React, {{ useMemo }} from 'react';`
    - `import {{ BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line }} from 'recharts';`
    - `import {{ Users, Code, Activity, Server, GitBranch, AlertCircle, CheckCircle }} from 'lucide-react';` (You can assume lucide-react is installed).

    IMPORTANT: Return ONLY the raw code string. Do not wrap in markdown blocks. Do not explain your code. Just the React code.

    """

    raw = await _call_llm(prompt, model=model)

    # Clean up markdown code blocks if present
    code = raw.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        code = "\n".join(lines)

    return code


async def generate_mock_data(metrics: list[dict], workspace_name: str, model: str | None = None) -> tuple[list[dict], dict]:
    """Generate realistic mock data entries for each metric using the LLM."""
    metrics_str = json.dumps(metrics, indent=2)

    prompt = f"""You are an expert data analyst. Generate realistic mock data for the following metrics
belonging to workspace "{workspace_name}".

METRICS:
{metrics_str}

For each metric, generate realistic time-series data spanning the last 30 days.
Each metric MUST have its own characteristic pattern based on its name/category (do NOT use the same monotonic trend for every metric).
Examples of characteristic patterns:
- Error/failure rates: mostly low with occasional spikes
- Latency/response time: noisy with occasional outliers
- Throughput/requests: weekly seasonality
- Cache hit rate: high baseline with occasional dips
- Adoption/MAU/DAU: gradual changes with noise, not perfectly linear

REQUIREMENTS:
- Generate 24-32 entries per metric (ideally ~1 per day for the last 30 days).
- Percentages MUST be between 0 and 100.
- Booleans should reflect metric intent (e.g., availability mostly true).
- Ensure there is visible variability across days so charts look realistic.

Respond in the following format:
```json
{{
  "trace": {{
    "patterns": ["2-6 short notes on trends/ranges you used"],
    "assumptions": ["0-5 assumptions you made (optional)"]
  }},
  "mock_data": [
    {{
      "metric_id": "string - MUST match the metric id from the METRICS input (if provided)",
      "metric_name": "string - MUST match the metric name from the METRICS input",
      "entries": [{{"value": "...", "recorded_at": "ISO timestamp", "notes": "optional"}}]
    }}
  ]
}}
```

IMPORTANT: For each metric, generate 24-32 data entries spanning the last 30 days.
THE JSON MUST BE THE ONLY CONTENT OUTSIDE THE THINKING TAG. DO NOT ADD PREAMBLE OR CLOSING REMARKS.
"""

    def fallback_mock_data() -> tuple[list[dict], dict]:
        rng = random.Random(f"{workspace_name}:{len(metrics)}:v2")
        now = datetime.now(timezone.utc)

        def clamp(x: float, lo: float, hi: float) -> float:
            return max(lo, min(hi, x))

        def infer_kind(metric_name: str) -> str:
            n = (metric_name or "").lower()
            if any(k in n for k in ["error", "failure", "fail", "exception", "crash", "timeout"]):
                return "error_rate"
            if any(k in n for k in ["latency", "response time", "duration", "time to", "ttfb"]):
                return "latency"
            if any(k in n for k in ["throughput", "requests", "qps", "rps", "traffic", "hits"]):
                return "throughput"
            if "cache" in n and ("hit" in n or "miss" in n or "hit rate" in n):
                return "cache_hit_rate"
            if any(k in n for k in ["availability", "uptime"]):
                return "availability"
            if any(k in n for k in ["conversion", "ctr", "retention", "churn", "bounce"]):
                return "funnel_rate"
            if any(k in n for k in ["users", "mau", "dau", "wau", "sessions", "active"]):
                return "usage"
            return "generic"

        def series_random_walk(*, baseline: float, volatility: float, mean_revert: float = 0.15) -> list[float]:
            vals: list[float] = []
            x = baseline
            for i in range(30):
                seasonal = 1.0 + 0.08 * (1 if (i % 7) in (1, 2, 3, 4, 5) else -1)
                drift = (baseline - x) * mean_revert
                x = (x + drift + rng.gauss(0.0, volatility)) * seasonal
                vals.append(x)
            return vals

        out: list[dict] = []
        for m in metrics:
            metric_id = (m.get("id") or "").strip() if isinstance(m, dict) else ""
            name = (m.get("name") or "").strip() or "metric"
            dt = (m.get("data_type") or "number").strip().lower()
            kind = infer_kind(name)

            entries: list[dict] = []
            days = list(reversed(range(30)))  # oldest -> newest

            if dt == "boolean":
                p_true = 0.97 if kind in ("availability",) else 0.7
                for d in days:
                    ts = (now - timedelta(days=d)).replace(hour=12, minute=0, second=0, microsecond=0)
                    entries.append({"value": (rng.random() < p_true), "recorded_at": ts.isoformat()})
            elif dt == "string":
                if any(s in name.lower() for s in ["status", "state", "result"]):
                    choices = [("success", 0.8), ("failure", 0.12), ("pending", 0.08)]
                else:
                    choices = [("low", 0.25), ("medium", 0.55), ("high", 0.2)]
                labels, weights = zip(*choices)
                for d in days:
                    ts = (now - timedelta(days=d)).replace(hour=12, minute=0, second=0, microsecond=0)
                    entries.append({"value": rng.choices(list(labels), weights=list(weights), k=1)[0], "recorded_at": ts.isoformat()})
            else:
                if kind == "error_rate":
                    baseline = rng.uniform(0.1, 3.0)  # percent
                    vals = series_random_walk(baseline=baseline, volatility=baseline * 0.25, mean_revert=0.25)
                    for s in rng.sample(range(30), k=rng.randint(1, 3)):
                        vals[s] += rng.uniform(4.0, 18.0)
                    if dt != "percentage":
                        vals = [clamp(v / 100.0, 0.0, 1.0) for v in vals]
                    else:
                        vals = [clamp(v, 0.0, 100.0) for v in vals]
                elif kind == "cache_hit_rate":
                    baseline = rng.uniform(78.0, 97.0)
                    vals = series_random_walk(baseline=baseline, volatility=1.8, mean_revert=0.3)
                    for s in rng.sample(range(30), k=rng.randint(1, 2)):
                        vals[s] -= rng.uniform(6.0, 15.0)
                    vals = [clamp(v, 0.0, 100.0) for v in vals]
                    if dt != "percentage":
                        vals = [round(v / 100.0, 4) for v in vals]
                elif kind == "latency":
                    baseline = rng.uniform(120.0, 900.0)
                    vals = series_random_walk(baseline=baseline, volatility=baseline * 0.08, mean_revert=0.2)
                    for s in rng.sample(range(30), k=rng.randint(1, 2)):
                        vals[s] *= rng.uniform(1.6, 2.8)
                    vals = [max(0.0, v) for v in vals]
                elif kind in ("throughput", "usage"):
                    baseline = rng.uniform(500.0, 15000.0) if kind == "throughput" else rng.uniform(50.0, 6000.0)
                    vals = series_random_walk(baseline=baseline, volatility=baseline * 0.10, mean_revert=0.15)
                    vals = [max(0.0, v) for v in vals]
                elif kind == "funnel_rate":
                    baseline = rng.uniform(0.8, 9.0)
                    vals = series_random_walk(baseline=baseline, volatility=baseline * 0.18, mean_revert=0.25)
                    vals = [clamp(v, 0.0, 100.0) for v in vals]
                    if dt != "percentage":
                        vals = [round(v / 100.0, 4) for v in vals]
                else:
                    baseline = rng.uniform(10.0, 800.0)
                    vals = series_random_walk(baseline=baseline, volatility=baseline * 0.12, mean_revert=0.12)
                    vals = [max(0.0, v) for v in vals]

                for idx, d in enumerate(days):
                    ts = (now - timedelta(days=d)).replace(hour=12, minute=0, second=0, microsecond=0)
                    v = float(vals[idx]) if idx < len(vals) else 0.0
                    if dt == "percentage":
                        value = round(clamp(v, 0.0, 100.0), 2)
                    else:
                        value = round(v, 2)
                    entries.append({"value": value, "recorded_at": ts.isoformat()})

            out.append({"metric_id": metric_id, "metric_name": name, "entries": entries})

        return out, {
            "fallback": True,
            "patterns": [
                "Generated ~30 daily points per metric (last 30 days)",
                "Used metric-name heuristics (error spikes, cache dips, weekly seasonality, noisy latency)",
                "Applied mean-reverting random walk + anomalies for realism",
            ],
            "assumptions": ["Used deterministic RNG seeded by workspace name for reproducibility"],
        }

    try:
        raw = await _call_llm(prompt, model=model)
        result, trace = _parse_json_with_trace(raw)
        mock = []
        if isinstance(result, dict):
            mock = result.get("mock_data", []) or []
            result.pop("trace", None)
        if not mock:
            return fallback_mock_data()
        return mock, trace
    except Exception as e:
        logger.warning(f"[MockData] LLM generation failed, using fallback: {type(e).__name__}: {str(e)[:200]}")
        return fallback_mock_data()


async def generate_dashboard_plan(metrics: list[dict], workspace_name: str, workspace_id: str, model: str | None = None) -> tuple[dict, dict]:
    """Ask the LLM to plan a Metabase dashboard: decide chart types and write SQL queries."""
    metrics_str = json.dumps(metrics, indent=2)

    prompt = f"""You are an expert data analyst and dashboard designer. You need to plan a Metabase dashboard for the workspace "{workspace_name}".

The data is stored in a SQLite database with these tables:

TABLE: metrics
  - id (TEXT, primary key)
  - workspace_id (TEXT)
  - name (TEXT)
  - description (TEXT)
  - category (TEXT) -- one of: business, engagement, content, performance, growth
  - data_type (TEXT) -- one of: number, percentage, boolean, string
  - suggested_source (TEXT)
  - source_table (TEXT)
  - source_platform (TEXT)
  - display_order (INTEGER)
  - created_at (TEXT)

TABLE: metric_entries
  - id (TEXT, primary key)
  - metric_id (TEXT, foreign key to metrics.id)
  - value (TEXT) -- the value as a string
  - recorded_at (TEXT) -- ISO timestamp
  - notes (TEXT)

The workspace_id for this workspace is: "{workspace_id}"

METRICS FOR THIS WORKSPACE:
{metrics_str}

Design a dashboard with 5-10 charts. For each chart, decide:
1. The best visualization type based on what the metric represents
2. A SQL query that extracts the right data from the tables above
3. A descriptive title

Available chart types: bar, line, pie, scalar, area, row, table

Respond in the following format:
```json
{{
  "trace": {{
    "design_choices": ["3-8 short, concrete design choices tied to specific metrics"],
    "sql_notes": ["0-5 important SQL assumptions (optional)"]
  }},
  "dashboard_name": "string - a descriptive name for the dashboard",
  "description": "string - brief description",
  "cards": [
    {{
      "title": "string - chart title",
      "chart_type": "bar|line|pie|scalar|area|row|table",
      "sql": "string - the SQL query (use SQLite syntax). Always filter by workspace_id = '{workspace_id}' when joining metrics table.",
      "size_x": 12,
      "size_y": 6,
      "description": "brief description of what this chart shows"
    }}
  ]
}}

IMPORTANT SQL NOTES:
- Always JOIN metric_entries with metrics ON metric_entries.metric_id = metrics.id
- Always filter with metrics.workspace_id = '{workspace_id}'
- For scalar charts (single number), use aggregations like COUNT, AVG, SUM
- For time series (line/area), group by date using substr(metric_entries.recorded_at, 1, 10)
- For category distribution (pie), group by metrics.category
- Cast value to numeric when needed: CAST(metric_entries.value AS REAL)
- Use descriptive column aliases

Design the dashboard to be insightful and specific to these metrics. Group related charts together."""

    def fallback_plan() -> tuple[dict, dict]:
        plan = {
            "dashboard_name": f"{workspace_name} - Metrics",
            "description": "Auto-generated fallback dashboard (LLM plan unavailable).",
            "cards": [
                {
                    "title": "Total Entries (Last 30d)",
                    "chart_type": "scalar",
                    "sql": (
                        "SELECT COUNT(*) AS total_entries "
                        "FROM metric_entries me "
                        "JOIN metrics m ON me.metric_id = m.id "
                        f"WHERE m.workspace_id = '{workspace_id}' "
                        "AND substr(me.recorded_at, 1, 10) >= substr(date('now','-30 day'), 1, 10)"
                    ),
                    "size_x": 6,
                    "size_y": 4,
                    "description": "Count of all synthetic (or real) metric entries in the last 30 days.",
                },
                {
                    "title": "Entries Over Time (Last 30d)",
                    "chart_type": "line",
                    "sql": (
                        "SELECT substr(me.recorded_at, 1, 10) AS day, COUNT(*) AS entries "
                        "FROM metric_entries me "
                        "JOIN metrics m ON me.metric_id = m.id "
                        f"WHERE m.workspace_id = '{workspace_id}' "
                        "AND substr(me.recorded_at, 1, 10) >= substr(date('now','-30 day'), 1, 10) "
                        "GROUP BY day ORDER BY day"
                    ),
                    "size_x": 12,
                    "size_y": 6,
                    "description": "Volume of recorded entries per day.",
                },
                {
                    "title": "Top Metrics by Entry Count",
                    "chart_type": "bar",
                    "sql": (
                        "SELECT m.name AS metric, COUNT(*) AS entries "
                        "FROM metric_entries me "
                        "JOIN metrics m ON me.metric_id = m.id "
                        f"WHERE m.workspace_id = '{workspace_id}' "
                        "GROUP BY metric ORDER BY entries DESC LIMIT 10"
                    ),
                    "size_x": 12,
                    "size_y": 6,
                    "description": "Which metrics have the most recorded points.",
                },
                {
                    "title": "Latest Values",
                    "chart_type": "table",
                    "sql": (
                        "SELECT m.name AS metric, me.value, me.recorded_at "
                        "FROM metric_entries me "
                        "JOIN metrics m ON me.metric_id = m.id "
                        f"WHERE m.workspace_id = '{workspace_id}' "
                        "ORDER BY me.recorded_at DESC LIMIT 50"
                    ),
                    "size_x": 12,
                    "size_y": 6,
                    "description": "Most recent values across metrics.",
                },
            ],
        }
        trace = {
            "fallback": True,
            "design_choices": [
                "Use workspace-wide charts so the dashboard works even without per-metric SQL.",
                "Favor simple joins and date grouping compatible with SQLite.",
            ],
        }
        return plan, trace

    try:
        raw = await _call_llm(prompt, model=model)
        result, trace = _parse_json_with_trace(raw)
        if isinstance(result, dict) and isinstance(result.get("trace"), dict):
            result.pop("trace", None)
        if not isinstance(result, dict) or not result.get("cards"):
            return fallback_plan()
        return result, trace
    except Exception as e:
        logger.warning(f"[MetabasePlan] LLM plan failed, using fallback: {type(e).__name__}: {str(e)[:200]}")
        return fallback_plan()


async def get_first_impressions(file_tree: list[str]) -> tuple[str, dict]:
    """Get a quick analysis of the repository structure for logging."""
    tree_str = "\n".join(file_tree[:150])  # Cap for speed

    prompt = f"""You are an expert software analyst. Look at this file tree and return a very specific, user-visible note about what you immediately notice.

FILE TREE:
{tree_str}

Respond as JSON:
```json
{{
  "impression": "1 punchy sentence: I see a ... because ... (reference specific dirs/files)",
  "trace": {{
    "top_level_signals": ["2-6 specific path-based signals you used"]
  }}
}}
```"""

    try:
        raw = await _call_llm(prompt)
        result, trace = _parse_json_with_trace(raw)
        if isinstance(result, dict):
            impression = result.get("impression")
            if isinstance(impression, str) and impression.strip():
                return impression.strip(), trace
        return "I see a repository with a mixed layout; key signals were not confidently identified from the tree sample.", trace
    except Exception as e:
        logger.warning(f"[FirstImpressions] LLM failed, using fallback: {type(e).__name__}: {str(e)[:200]}")
        trace = {"fallback": True, "top_level_signals": [p for p in (file_tree or [])[:25] if isinstance(p, str)]}
        return "I see a repository tree sample, but the LLM impression call failed; continuing without it.", trace
