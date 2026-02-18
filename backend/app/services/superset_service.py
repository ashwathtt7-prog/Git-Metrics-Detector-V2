from __future__ import annotations

import logging
import httpx
from typing import Optional
from pathlib import Path
from ..config import settings

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "metrics.db"


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
                params={"q": '{"filters":[{"col":"table_name","opr":"eq","value":"metrics"}]}'},
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

    async def create_chart(
        self, dataset_id: int, workspace_id: str, workspace_name: str
    ) -> Optional[int]:
        headers = await self._headers()

        chart_config = {
            "datasource": f"{dataset_id}__table",
            "viz_type": "echarts_timeseries_pie",
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

        import json
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/chart/",
                headers=headers,
                json={
                    "datasource_id": dataset_id,
                    "datasource_type": "table",
                    "slice_name": f"{workspace_name} - Metrics by Category",
                    "viz_type": "echarts_timeseries_pie",
                    "params": json.dumps(chart_config),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("id")

    async def create_dashboard(
        self, workspace_id: str, workspace_name: str, chart_ids: list[int]
    ) -> Optional[str]:
        headers = await self._headers()

        children = []
        for i, chart_id in enumerate(chart_ids):
            children.append(
                {
                    "type": "CHART",
                    "id": i + 1,
                    "children": [],
                    "meta": {"chartId": chart_id, "width": 12, "height": 50},
                }
            )

        position_json = {
            "DASHBOARD_VERSION_KEY": "v2",
            "ROOT_ID": {"children": list(range(1, len(chart_ids) + 1)), "id": "ROOT_ID", "type": "ROOT"},
            **{
                str(i + 1): child
                for i, child in enumerate(children)
            },
        }

        import json
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
        self, workspace_id: str, workspace_name: str
    ) -> Optional[str]:
        try:
            database_id = await self.ensure_database()
            dataset_id = await self.ensure_dataset(database_id)
            chart_id = await self.create_chart(dataset_id, workspace_id, workspace_name)
            
            if chart_id:
                dashboard_id = await self.create_dashboard(
                    workspace_id, workspace_name, [chart_id]
                )
                if dashboard_id:
                    dashboard_url = f"{self.base_url}/superset/dashboard/workspace-{workspace_id[:8]}/"
                    logger.info(f"[Superset] Created dashboard: {dashboard_url}")
                    return dashboard_url
            return None
        except Exception as e:
            logger.error(f"[Superset] Failed to create dashboard: {e}")
            return None


superset_client = SupersetClient()


async def create_superset_dashboard(workspace_id: str, workspace_name: str) -> Optional[str]:
    return await superset_client.setup_workspace_dashboard(workspace_id, workspace_name)
