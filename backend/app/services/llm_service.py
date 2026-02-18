from __future__ import annotations

import json
import re
import logging
from typing import List, Dict
from .providers import get_provider

logger = logging.getLogger(__name__)


def _format_files_for_prompt(files: list[dict]) -> str:
    parts = []
    for f in files:
        parts.append(f"--- {f['path']} ---\n{f['content']}\n")
    return "\n".join(parts)


def _parse_json_response(raw: str) -> dict:
    """Parse LLM JSON response with fallbacks."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse LLM response as JSON: {raw[:300]}...")


async def _call_llm(prompt: str) -> str:
    """Call the configured LLM provider with retry logic."""
    provider = get_provider()
    return await provider.generate_with_retry(prompt, json_mode=True)


async def analyze_project_overview(file_tree: list[str], key_files: list[dict]) -> dict:
    """Pass 1: Get a high-level understanding of the project."""
    tree_str = "\n".join(file_tree)
    files_str = _format_files_for_prompt(key_files)

    prompt = f"""You are an expert software analyst. You are given the contents of a software repository. Your job is to understand what this project does, its technology stack, its domain, and its architecture.

Here is the repository file tree:
{tree_str}

Here are the key files:
{files_str}

Respond in the following JSON format exactly:
{{
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

    raw = await _call_llm(prompt)
    return _parse_json_response(raw)


async def discover_metrics(project_summary: dict, files: list[dict]) -> list[dict]:
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

Respond in the following JSON format exactly:
{{
  "metrics": [
    {{
      "name": "string",
      "description": "string",
      "category": "business|engagement|content|performance|growth",
      "data_type": "number|percentage|boolean|string",
      "suggested_source": "string describing where to measure this"
    }}
  ]
}}

Return between 8 and 25 metrics, ordered by importance. Focus on metrics that are specific and actionable for THIS particular project, not generic software metrics. Avoid vague metrics like "code quality" -- be specific."""

    raw = await _call_llm(prompt)
    result = _parse_json_response(raw)
    return result.get("metrics", [])


async def consolidate_metrics(project_summary: dict, batch_results: list[list[dict]]) -> list[dict]:
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
  "metrics": [
    {{
      "name": "string",
      "description": "string",
      "category": "business|engagement|content|performance|growth",
      "data_type": "number|percentage|boolean|string",
      "suggested_source": "string describing where to measure this"
    }}
  ]
}}"""

    raw = await _call_llm(prompt)
    result = _parse_json_response(raw)
    return result.get("metrics", [])


async def suggest_dashboard_charts(project_summary: dict, metrics: list[dict]) -> list[dict]:
    """Pass 4: Ask LLM to suggest Superset chart types for the discovered metrics."""
    summary_str = json.dumps(project_summary, indent=2)
    metrics_str = json.dumps(metrics, indent=2)

    prompt = f"""You are a data visualization expert. Given a software project and its discovered metrics, suggest the best Apache Superset chart types for a dashboard.

PROJECT CONTEXT:
{summary_str}

DISCOVERED METRICS:
{metrics_str}

For this project's dashboard, suggest 3-6 charts that would give the best overview. For each chart, specify:
- chart_type: one of "pie", "bar", "table", "big_number", "big_number_total", "line", "area"
- title: a descriptive chart title
- description: what this chart shows
- metrics_used: which metric categories or specific metric names this chart covers
- groupby: what to group by (e.g., "category", "data_type", "name")
- metric_expression: what to aggregate (e.g., "COUNT(*)", "COUNT(id)")

Consider:
- A pie chart for category distribution
- A table showing all metrics with details
- Big number cards for key counts
- Bar charts comparing metrics across categories

Respond in JSON format exactly:
{{
  "charts": [
    {{
      "chart_type": "string",
      "title": "string",
      "description": "string",
      "metrics_used": ["string"],
      "groupby": ["string"],
      "metric_expression": "string"
    }}
  ]
}}"""

    raw = await _call_llm(prompt)
    result = _parse_json_response(raw)
    return result.get("charts", [])
