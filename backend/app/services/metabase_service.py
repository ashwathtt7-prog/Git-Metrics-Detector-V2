import httpx
import json
import logging
from typing import Optional, List, Dict
from ..config import settings

logger = logging.getLogger(__name__)

class MetabaseService:
    def __init__(self):
        self.base_url = settings.metabase_url.rstrip("/")
        self.username = settings.metabase_username
        self.password = settings.metabase_password
        self.session_token = None

    async def _authenticate(self):
        """Authenticate with Metabase and get a session token."""
        if not self.username or not self.password:
            logger.warning("[Metabase] No credentials provided. Skipping authentication.")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/session",
                    json={"username": self.username, "password": self.password},
                    timeout=10.0
                )
                if resp.status_code == 200:
                    self.session_token = resp.json().get("id")
                    return True
                else:
                    logger.error(f"[Metabase] Auth failed: {resp.status_code} {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"[Metabase] Connection error: {str(e)}")
            return False

    async def _get_headers(self):
        if not self.session_token:
            await self._authenticate()
        return {"X-Metabase-Session": self.session_token} if self.session_token else {}

    async def setup_database(self, db_path: str) -> Optional[int]:
        """Ensure the SQLite database is registered in Metabase."""
        headers = await self._get_headers()
        if not headers: return None

        async with httpx.AsyncClient() as client:
            # 1. Check if already exists
            dbs_resp = await client.get(f"{self.base_url}/api/database", headers=headers)
            if dbs_resp.status_code == 200:
                for db in dbs_resp.json().get("data", []):
                    if db.get("details", {}).get("db") == db_path:
                        return db["id"]

            # 2. Add it
            payload = {
                "name": "Git Metrics Detector DB",
                "engine": "sqlite",
                "details": {"db": db_path},
                "auto_run_queries": True,
                "is_full_sync": True
            }
            add_resp = await client.post(f"{self.base_url}/api/database", headers=headers, json=payload)
            if add_resp.status_code == 200:
                return add_resp.json()["id"]
            else:
                logger.error(f"[Metabase] Failed to add DB: {add_resp.text}")
                return None

    async def create_dashboard(self, workspace_name: str, db_id: int, plan: Dict) -> Optional[str]:
        """Create a dashboard and cards based on the LLM plan."""
        headers = await self._get_headers()
        if not headers: return None

        async with httpx.AsyncClient() as client:
            # 1. Create Dashboard
            dash_payload = {
                "name": f"{workspace_name} - Metrics Discovery",
                "description": plan.get("description", "AI-Generated Dashboard")
            }
            dash_resp = await client.post(f"{self.base_url}/api/dashboard", headers=headers, json=dash_payload)
            if dash_resp.status_code != 200:
                logger.error(f"[Metabase] Dash creation failed: {dash_resp.text}")
                return None
            
            dash_id = dash_resp.json()["id"]

            # 2. Create Cards and add to Dashboard
            for i, card_plan in enumerate(plan.get("cards", [])):
                # Create Card (Question)
                card_payload = {
                    "name": card_plan["title"],
                    "dataset_query": {
                        "database": db_id,
                        "type": "native",
                        "native": {"query": card_plan["sql"]}
                    },
                    "display": self._map_chart_type(card_plan["chart_type"]),
                    "visualization_settings": {}
                }
                card_resp = await client.post(f"{self.base_url}/api/card", headers=headers, json=card_payload)
                if card_resp.status_code == 200:
                    card_id = card_resp.json()["id"]
                    
                    # Add to dashboard
                    add_to_dash_payload = {
                        "cardId": card_id,
                        "row": (i // 2) * 6,
                        "col": (i % 2) * 6,
                        "sizeX": card_plan.get("size_x", 12 if card_plan["chart_type"] == "line" else 6),
                        "sizeY": card_plan.get("size_y", 6)
                    }
                    await client.post(f"{self.base_url}/api/dashboard/{dash_id}/cards", headers=headers, json=add_to_dash_payload)

            return f"{self.base_url}/dashboard/{dash_id}"

    def _map_chart_type(self, ct: str) -> str:
        mapping = {
            "bar": "bar",
            "line": "line",
            "area": "area",
            "pie": "pie",
            "scalar": "scalar",
            "table": "table",
            "row": "row"
        }
        return mapping.get(ct, "bar")

metabase_service = MetabaseService()
