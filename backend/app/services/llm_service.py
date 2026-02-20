from __future__ import annotations

import json
import re
import logging

from .llm.provider_chain import LLMProviderChain
from .llm.gemini_provider import GeminiProvider
from .llm.groq_provider import GroqProvider
from .llm.openrouter_provider import OpenRouterProvider
from .llm.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

_chain: LLMProviderChain | None = None


def _get_chain() -> LLMProviderChain:
    global _chain
    if _chain is None:
        _chain = LLMProviderChain([
            GeminiProvider(),
            GroqProvider(),
            OpenRouterProvider(),
            OllamaProvider(),
        ])
    return _chain


def get_batch_token_limit() -> int:
    """Return the safe token limit for batching, based on available providers."""
    return _get_chain().get_max_context_tokens()


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

    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse LLM response as JSON: {raw[:300]}...")


async def _call_llm(prompt: str) -> str:
    chain = _get_chain()
    return await chain.generate(prompt)


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
- A source_table: the specific database table, API endpoint, or data collection where this metric can be found (e.g., 'users', 'orders', 'api_access_logs', '/api/v1/metrics'). Infer from the codebase.
- A source_platform: the platform or system where this data lives (e.g., 'PostgreSQL', 'GCP BigQuery', 'Oracle DB', 'MongoDB', 'REST API', 'Application Logs', 'GitHub API'). Infer from the detected tech stack.

Respond in the following JSON format exactly:
{{
  "metrics": [
      {{
        "name": "string",
        "description": "string",
        "category": "business|engagement|content|performance|growth",
        "data_type": "number|percentage|boolean|string",
        "suggested_source": "string describing where to measure this",
        "source_table": "string - the specific database table, API endpoint, or data collection",
        "source_platform": "string - the infrastructure platform (e.g., GCP, AWS, Oracle, PostgreSQL, MongoDB)",
        "estimated_value": "string or number (e.g., '150', '25%', 'Active', 'High') - based on the code analysis (e.g., count routes for API count, count components for component count)"
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
      "suggested_source": "string describing where to measure this",
      "source_table": "string - the specific database table, API endpoint, or data collection",
      "source_platform": "string - the infrastructure platform (e.g., GCP, AWS, Oracle, PostgreSQL, MongoDB)",
      "estimated_value": "string or number"
    }}
  ]
}}"""

    raw = await _call_llm(prompt)
    result = _parse_json_response(raw)
    return result.get("metrics", [])


async def generate_dashboard_code(project_summary: dict, metrics: list[dict], workspace_id: str) -> str:
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

    raw = await _call_llm(prompt)

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


async def generate_mock_data(metrics: list[dict], workspace_name: str) -> list[dict]:
    """Generate realistic mock data entries for each metric using the LLM."""
    metrics_str = json.dumps(metrics, indent=2)

    prompt = f"""You are an expert data analyst. Generate realistic mock data for the following metrics
belonging to workspace "{workspace_name}".

METRICS:
{metrics_str}

For each metric, generate between 10 and 30 data entries spanning the last 90 days.
The data should follow realistic patterns:
- Numbers should have realistic ranges and trends (gradual growth, seasonal patterns, etc.)
- Percentages should be between 0 and 100
- Boolean metrics should have a mix of true/false
- String metrics should have realistic categorical values

Respond in the following JSON format exactly:
{{
  "mock_data": [
    {{
      "metric_name": "string (must match a metric name exactly)",
      "entries": [
        {{
          "value": "string representation of the value",
          "recorded_at": "ISO 8601 date string (e.g., 2026-01-15T10:00:00Z)",
          "notes": "optional note about this data point"
        }}
      ]
    }}
  ]
}}

Make the data look realistic and varied. For growth metrics, show an upward trend.
For performance metrics, show occasional spikes. Include some data anomalies for realism."""

    raw = await _call_llm(prompt)
    result = _parse_json_response(raw)
    return result.get("mock_data", [])


async def generate_dashboard_plan(metrics: list[dict], workspace_name: str, workspace_id: str) -> dict:
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

Respond in the following JSON format exactly:
{{
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

    raw = await _call_llm(prompt)
    return _parse_json_response(raw)
