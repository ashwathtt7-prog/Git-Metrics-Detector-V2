from __future__ import annotations

import json
import logging
import httpx
from typing import Optional
from pathlib import Path
from ..config import settings

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "metrics.db"

# Map LLM chart_type suggestions to Superset viz_type identifiers
CHART_TYPE_MAP = {
    "pie": "pie",
    "bar": "echarts_timeseries_bar",
    "table": "table",
    "big_number": "big_number",
    "big_number_total": "big_number_total",
    "line": "echarts_timeseries_line",
    "area": "echarts_area",
}


class SupersetClient:
    def __init__(self):
        self.base_url = settings.superset_url.rstrip("/")
        self.username = settings.superset_username
        self.password = settings.superset_password
        self._token: Optional[str] = None
        self._database_id: Optional[int] = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/security/login",
                json={
                    "username": self.username,
                    "password": self.password,
                    "provider": "db",
                    "refresh": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            return self._token

    async def _headers(self) -> dict:
        token = await self._get_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def ensure_database(self) -> int:
        if self._database_id:
            return self._database_id

        headers = await self._headers()
        db_uri = f"sqlite:///{DB_PATH.as_posix()}"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/database/",
                params={"q": '{"filters":[{"col":"database_name","opr":"eq","value":"Git Metrics"}]}'},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("result") and len(data["result"]) > 0:
                self._database_id = data["result"][0]["id"]
                return self._database_id

            resp = await client.post(
                f"{self.base_url}/api/v1/database/",
                headers=headers,
                json={
                    "database_name": "Git Metrics",
                    "sqlalchemy_uri": db_uri,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._database_id = data["id"]
            return self._database_id

    async def ensure_dataset(self, database_id: int, table_name: str = "metrics") -> int:
        headers = await self._headers()

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/dataset/",
                params={"q": json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": table_name}]})},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("result") and len(data["result"]) > 0:
                return data["result"][0]["id"]

            resp = await client.post(
                f"{self.base_url}/api/v1/dataset/",
                headers=headers,
                json={
                    "database": database_id,
                    "table_name": table_name,
                    "schema": "",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["id"]

    def _build_chart_config(
        self,
        chart_suggestion: dict,
        dataset_id: int,
        workspace_id: str,
    ) -> dict:
        """Build Superset chart params from an LLM chart suggestion."""
        chart_type = chart_suggestion.get("chart_type", "table")
        viz_type = CHART_TYPE_MAP.get(chart_type, "table")

        workspace_filter = {
            "expressionType": "SIMPLE",
            "clause": "WHERE",
            "comparator": workspace_id,
            "operator": "==",
            "subject": "workspace_id",
        }

        groupby = chart_suggestion.get("groupby", ["category"])
        metric_expr = chart_suggestion.get("metric_expression", "COUNT(*)")

        # Build the metric spec
        if "COUNT" in metric_expr.upper():
            metric = {
                "expressionType": "SIMPLE",
                "column": {"column_name": "id"},
                "aggregate": "COUNT",
            }
        else:
            metric = {
                "expressionType": "SQL",
                "sqlExpression": metric_expr,
                "label": metric_expr,
            }

        params = {
            "datasource": f"{dataset_id}__table",
            "viz_type": viz_type,
            "time_range": "No filter",
            "groupby": groupby,
            "metric": metric,
            "metrics": [metric],
            "adhoc_filters": [workspace_filter],
            "row_limit": 100,
            "color_scheme": "supersetColors",
        }

        # Type-specific config
        if chart_type == "pie":
            params.update({
                "show_legend": True,
                "show_labels": True,
                "labels_outside": True,
            })
        elif chart_type == "bar":
            params.update({
                "show_legend": True,
                "x_axis_label": groupby[0] if groupby else "category",
                "y_axis_label": "Count",
            })
        elif chart_type == "table":
            params.update({
                "all_columns": ["name", "description", "category", "data_type", "suggested_source"],
                "order_by_cols": ["name"],
                "page_length": 50,
            })
        elif chart_type in ("big_number", "big_number_total"):
            params.update({
                "header_font_size": 0.4,
                "subheader_font_size": 0.15,
            })

        return params

    async def create_chart(
        self,
        dataset_id: int,
        workspace_id: str,
        workspace_name: str,
        chart_suggestion: Optional[dict] = None,
    ) -> Optional[int]:
        """Create a single chart in Superset.

        If chart_suggestion is provided, uses the LLM-suggested config.
        Otherwise falls back to a default category pie chart.
        """
        headers = await self._headers()

        if chart_suggestion:
            chart_config = self._build_chart_config(chart_suggestion, dataset_id, workspace_id)
            chart_type = chart_suggestion.get("chart_type", "table")
            viz_type = CHART_TYPE_MAP.get(chart_type, "table")
            slice_name = chart_suggestion.get("title", f"{workspace_name} - Chart")
        else:
            # Default: category pie chart (backward-compatible)
            viz_type = "pie"
            slice_name = f"{workspace_name} - Metrics by Category"
            chart_config = {
                "datasource": f"{dataset_id}__table",
                "viz_type": "pie",
                "time_range": "No filter",
                "groupby": ["category"],
                "metric": {"expressionType": "SIMPLE", "column": {"column_name": "id"}, "aggregate": "COUNT"},
                "adhoc_filters": [
                    {
                        "expressionType": "SIMPLE",
                        "clause": "WHERE",
                        "comparator": workspace_id,
                        "operator": "==",
                        "subject": "workspace_id",
                    }
                ],
                "row_limit": 100,
                "color_scheme": "supersetColors",
                "show_legend": True,
                "show_labels": True,
                "labels_outside": True,
            }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/chart/",
                headers=headers,
                json={
                    "datasource_id": dataset_id,
                    "datasource_type": "table",
                    "slice_name": slice_name,
                    "viz_type": viz_type,
                    "params": json.dumps(chart_config),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("id")

    async def create_dashboard(
        self, workspace_id: str, workspace_name: str, chart_ids: list[int]
    ) -> Optional[str]:
        """Create a dashboard with auto-layout grid for all charts."""
        headers = await self._headers()

        # Build a responsive grid layout (Superset uses a 12-column grid)
        position_json = {"DASHBOARD_VERSION_KEY": "v2"}

        row_children = []
        for i, chart_id in enumerate(chart_ids):
            if len(chart_ids) <= 2:
                width = 12
            elif i == len(chart_ids) - 1 and len(chart_ids) % 2 == 1:
                width = 12
            else:
                width = 6

            component_id = f"CHART-{chart_id}"
            position_json[component_id] = {
                "type": "CHART",
                "id": component_id,
                "children": [],
                "meta": {
                    "chartId": chart_id,
                    "width": width,
                    "height": 50,
                },
            }
            row_children.append(component_id)

        # Create row containers (2 charts per row)
        rows = []
        for i in range(0, len(row_children), 2):
            row_id = f"ROW-{i // 2}"
            row_charts = row_children[i:i + 2]
            position_json[row_id] = {
                "type": "ROW",
                "id": row_id,
                "children": row_charts,
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
            }
            rows.append(row_id)

        # Header
        header_id = "HEADER_ID"
        position_json[header_id] = {
            "type": "HEADER",
            "id": header_id,
            "meta": {"text": f"{workspace_name} Metrics Dashboard"},
        }

        # Grid root
        position_json["GRID_ID"] = {
            "type": "GRID",
            "id": "GRID_ID",
            "children": rows,
        }

        position_json["ROOT_ID"] = {
            "type": "ROOT",
            "id": "ROOT_ID",
            "children": ["GRID_ID"],
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/dashboard/",
                headers=headers,
                json={
                    "dashboard_title": f"{workspace_name} Metrics",
                    "slug": f"workspace-{workspace_id[:8]}",
                    "position_json": json.dumps(position_json),
                    "published": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("id")

    async def setup_workspace_dashboard(
        self,
        workspace_id: str,
        workspace_name: str,
        chart_suggestions: Optional[list[dict]] = None,
    ) -> Optional[str]:
        """Full pipeline: ensure DB + dataset, create charts, assemble dashboard.

        Args:
            workspace_id: The workspace UUID.
            workspace_name: Human-readable workspace name.
            chart_suggestions: Optional list of LLM-suggested chart configs.
                If None, falls back to a single default pie chart.
        """
        try:
            database_id = await self.ensure_database()
            dataset_id = await self.ensure_dataset(database_id)

            chart_ids = []

            if chart_suggestions:
                for suggestion in chart_suggestions:
                    try:
                        chart_id = await self.create_chart(
                            dataset_id, workspace_id, workspace_name,
                            chart_suggestion=suggestion,
                        )
                        if chart_id:
                            chart_ids.append(chart_id)
                    except Exception as e:
                        logger.warning(f"[Superset] Failed to create chart '{suggestion.get('title', '?')}': {e}")
            else:
                chart_id = await self.create_chart(dataset_id, workspace_id, workspace_name)
                if chart_id:
                    chart_ids.append(chart_id)

            if chart_ids:
                dashboard_id = await self.create_dashboard(
                    workspace_id, workspace_name, chart_ids
                )
                if dashboard_id:
                    dashboard_url = f"{self.base_url}/superset/dashboard/workspace-{workspace_id[:8]}/"
                    logger.info(f"[Superset] Created dashboard with {len(chart_ids)} charts: {dashboard_url}")
                    return dashboard_url

            return None
        except Exception as e:
            logger.error(f"[Superset] Failed to create dashboard: {e}")
            return None


superset_client = SupersetClient()


async def create_superset_dashboard(
    workspace_id: str,
    workspace_name: str,
    chart_suggestions: Optional[list[dict]] = None,
) -> Optional[str]:
    return await superset_client.setup_workspace_dashboard(
        workspace_id, workspace_name, chart_suggestions
    )
