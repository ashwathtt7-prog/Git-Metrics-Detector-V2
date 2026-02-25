from __future__ import annotations

import httpx
import json
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict
from ..config import settings

logger = logging.getLogger(__name__)

class MetabaseService:
    def __init__(self):
        self.base_url = settings.metabase_url.rstrip("/")
        self.username = settings.metabase_username
        self.password = settings.metabase_password
        self.session_token = None
        self._public_sharing_enabled = False
        self._last_auth_error: str | None = None

    async def _get_setup_state(self) -> tuple[bool, str | None] | None:
        """Return (has_user_setup, setup_token) or None if Metabase is unreachable."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/session/properties", timeout=10.0)
                if resp.status_code != 200:
                    return None
                data = resp.json() or {}
                has_user_setup = bool(data.get("has-user-setup"))
                setup_token = data.get("setup-token")
                return has_user_setup, setup_token if isinstance(setup_token, str) else None
        except Exception:
            return None

    async def _try_auto_setup(self) -> bool:
        """If Metabase isn't set up yet, attempt setup using configured credentials."""
        state = await self._get_setup_state()
        if not state:
            return False

        has_user_setup, setup_token = state
        if has_user_setup:
            return True

        if not self.username or not self.password:
            self._last_auth_error = (
                "Metabase is running but not set up yet. Either finish setup at http://localhost:3003 "
                "or set METABASE_USERNAME and METABASE_PASSWORD in backend/.env so the backend can bootstrap it."
            )
            return False

        if not setup_token:
            self._last_auth_error = (
                "Metabase is not set up, but no setup token was available from /api/session/properties."
            )
            return False

        payload = {
            "token": setup_token,
            "prefs": {
                "site_name": "Git Metrics Detector",
                "site_locale": "en",
            },
            "user": {
                "email": self.username,
                "password": self.password,
                "first_name": "Git Metrics",
                "last_name": "Detector",
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/setup",
                    json=payload,
                    timeout=30.0,
                )
                if resp.status_code in (200, 204):
                    logger.info(f"[Metabase] Auto-setup completed for admin '{self.username}'.")
                    self._last_auth_error = None
                    return True

                # Avoid logging secrets; response may include validation details.
                self._last_auth_error = f"Metabase auto-setup failed: {resp.status_code} {resp.text}"
                logger.error(f"[Metabase] {self._last_auth_error}")
                return False
        except Exception as e:
            self._last_auth_error = f"Metabase auto-setup error: {type(e).__name__}: {str(e)[:200]}"
            logger.error(f"[Metabase] {self._last_auth_error}")
            return False

    async def _authenticate(self):
        """Authenticate with Metabase and get a session token."""
        # Refresh credentials (in case settings/env were loaded after service init)
        self.base_url = (settings.metabase_url or self.base_url).rstrip("/")
        self.username = (settings.metabase_username or self.username or "").strip()
        self.password = (settings.metabase_password or self.password or "").strip()

        # Fallback: load from backend/.env if Settings didn't pick it up (common when cwd differs).
        if (not self.username or not self.password) and not os.getenv("METABASE_USERNAME") and not os.getenv("METABASE_PASSWORD"):
            try:
                env_path = Path(__file__).resolve().parents[2] / ".env"  # backend/.env
                if env_path.is_file():
                    for line in env_path.read_text(encoding="utf-8").splitlines():
                        if not line or line.strip().startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k == "METABASE_URL" and v:
                            self.base_url = v.rstrip("/")
                        elif k == "METABASE_USERNAME" and v:
                            self.username = v
                        elif k == "METABASE_PASSWORD" and v:
                            self.password = v
            except Exception:
                pass

        # Environment variables override everything else
        self.username = (os.getenv("METABASE_USERNAME") or self.username or "").strip()
        self.password = (os.getenv("METABASE_PASSWORD") or self.password or "").strip()
        self.base_url = (os.getenv("METABASE_URL") or self.base_url or "").rstrip("/")

        if not self.username or not self.password:
            state = await self._get_setup_state()
            if state and not state[0]:
                self._last_auth_error = (
                    "Metabase is running but not set up yet. Finish setup at http://localhost:3003 "
                    "or set METABASE_USERNAME and METABASE_PASSWORD in backend/.env."
                )
                logger.warning(f"[Metabase] {self._last_auth_error}")
            else:
                self._last_auth_error = "Metabase credentials are not configured (METABASE_USERNAME/METABASE_PASSWORD)."
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
                    self._last_auth_error = None
                    return True

                # If Metabase hasn't been set up yet, try to bootstrap it once, then retry auth.
                if await self._try_auto_setup():
                    resp2 = await client.post(
                        f"{self.base_url}/api/session",
                        json={"username": self.username, "password": self.password},
                        timeout=10.0,
                    )
                    if resp2.status_code == 200:
                        self.session_token = resp2.json().get("id")
                        self._last_auth_error = None
                        return True

                self._last_auth_error = f"Metabase auth failed: {resp.status_code} {resp.text}"
                logger.error(f"[Metabase] {self._last_auth_error}")
                return False
        except Exception as e:
            self._last_auth_error = f"Metabase connection error: {type(e).__name__}: {str(e)[:200]}"
            logger.error(f"[Metabase] {self._last_auth_error}")
            return False

    async def _get_headers(self):
        if not self.session_token:
            await self._authenticate()
        return {"X-Metabase-Session": self.session_token} if self.session_token else {}

    async def _ensure_public_sharing(self, client: httpx.AsyncClient, headers: dict):
        """Enable public sharing in Metabase settings (once per session)."""
        if self._public_sharing_enabled:
            return
        try:
            resp = await client.put(
                f"{self.base_url}/api/setting/enable-public-sharing",
                headers=headers,
                json={"value": True},
                timeout=10.0,
            )
            if resp.status_code == 204 or resp.status_code == 200:
                self._public_sharing_enabled = True
                logger.info("[Metabase] Public sharing enabled.")
            else:
                logger.warning(f"[Metabase] Could not enable public sharing: {resp.status_code}")
        except Exception as e:
            logger.warning(f"[Metabase] Public sharing toggle error: {e}")

    async def setup_database(self, db_path: str) -> Optional[int]:
        """Ensure the SQLite database is registered in Metabase."""
        headers = await self._get_headers()
        if not headers:
            extra = f" ({self._last_auth_error})" if self._last_auth_error else ""
            raise RuntimeError(
                "Metabase credentials not configured or authentication failed. "
                f"Finish Metabase setup at http://localhost:3003, then set "
                f"METABASE_USERNAME and METABASE_PASSWORD in backend/.env (matching the Metabase admin user){extra}."
            )

        def _norm_path(p: str) -> str:
            try:
                s = str(p or "")
                if s.startswith("file:"):
                    s = s[len("file:") :]
                return os.path.normcase(os.path.normpath(s))
            except Exception:
                return str(p or "")

        async with httpx.AsyncClient() as client:
            # 1. Check if already exists
            dbs_resp = await client.get(f"{self.base_url}/api/database", headers=headers, timeout=10.0)
            if dbs_resp.status_code != 200:
                raise RuntimeError(f"Metabase GET /api/database failed: {dbs_resp.status_code} {dbs_resp.text}")
            for db in dbs_resp.json().get("data", []):
                details_db = (db.get("details") or {}).get("db") or ""
                if _norm_path(details_db) == _norm_path(db_path):
                    return db.get("id")
                # Fallback match by name to avoid duplicate-name add failures when paths differ
                if (db.get("name") or "").strip() == "Git Metrics Detector DB":
                    return db.get("id")

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
                logger.error(f"[Metabase] Failed to add DB: {add_resp.status_code} {add_resp.text}")
                # If name already exists, fetch and return it
                try:
                    dbs_resp = await client.get(f"{self.base_url}/api/database", headers=headers, timeout=10.0)
                    if dbs_resp.status_code == 200:
                        for db in dbs_resp.json().get("data", []):
                            if (db.get("name") or "").strip() == "Git Metrics Detector DB":
                                return db.get("id")
                except Exception:
                    pass
                raise RuntimeError(f"Metabase POST /api/database failed: {add_resp.status_code} {add_resp.text}")

    async def create_dashboard(
        self,
        workspace_name: str,
        db_id: int,
        plan: Dict,
        *,
        workspace_id: str | None = None,
    ) -> Optional[str]:
        """Create a dashboard and cards based on the LLM plan, return a public URL.

        Notes:
        - LLM plans sometimes include placeholders like `{workspace_id}`; this method can
          patch them using the provided `workspace_id`.
        - If all planned cards fail to create, we fall back to a small set of known-good
          cards so the shared dashboard is not empty.
        """
        headers = await self._get_headers()
        if not headers: return None

        def _infer_workspace_id_from_sql(sql_text: str) -> str | None:
            try:
                import re
                m = re.search(r"workspace_id\\s*=\\s*['\\\"]([^'\\\"]+)['\\\"]", sql_text or "", re.IGNORECASE)
                if m:
                    return m.group(1)
            except Exception:
                pass
            return None

        def _fix_sql(sql_text: str, ws_id: str | None) -> str:
            s = str(sql_text or "")
            if ws_id:
                s = (
                    s.replace("{workspace_id}", ws_id)
                    .replace("{{workspace_id}}", ws_id)
                    .replace("${workspace_id}", ws_id)
                    .replace("$workspace_id", ws_id)
                )
            # Metabase native queries should not include trailing code fences, etc.
            return s.strip().strip("```").strip()

        # Try to infer workspace_id from the plan SQL if not provided.
        effective_ws_id = (workspace_id or "").strip() or None
        if not effective_ws_id:
            try:
                for cp in (plan.get("cards", []) or []):
                    if isinstance(cp, dict) and cp.get("sql"):
                        inferred = _infer_workspace_id_from_sql(str(cp.get("sql") or ""))
                        if inferred:
                            effective_ws_id = inferred
                            break
            except Exception:
                effective_ws_id = None

        def _fallback_cards(ws_id: str | None) -> list[dict]:
            if not ws_id:
                # Workspace unknown: still generate a non-empty, DB-scoped dashboard.
                return [
                    {
                        "title": "Entries Over Time (All Workspaces)",
                        "chart_type": "line",
                        "sql": (
                            "SELECT substr(me.recorded_at, 1, 10) AS day, COUNT(*) AS entries "
                            "FROM metric_entries me "
                            "JOIN metrics m ON me.metric_id = m.id "
                            "GROUP BY day ORDER BY day"
                        ),
                        "size_x": 12,
                        "size_y": 6,
                        "description": "Daily entry volume across all workspaces.",
                    }
                ]
            return [
                {
                    "title": "Entries Over Time (Last 30d)",
                    "chart_type": "line",
                    "sql": (
                        "SELECT substr(me.recorded_at, 1, 10) AS day, COUNT(*) AS entries "
                        "FROM metric_entries me "
                        "JOIN metrics m ON me.metric_id = m.id "
                        f"WHERE m.workspace_id = '{ws_id}' "
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
                        f"WHERE m.workspace_id = '{ws_id}' "
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
                        f"WHERE m.workspace_id = '{ws_id}' "
                        "ORDER BY me.recorded_at DESC LIMIT 50"
                    ),
                    "size_x": 12,
                    "size_y": 6,
                    "description": "Most recent values across metrics.",
                },
            ]

        async with httpx.AsyncClient() as client:
            # Enable public sharing first
            await self._ensure_public_sharing(client, headers)

            # 1. Create Dashboard
            dash_payload = {
                "name": f"Strategic Analytics: {workspace_name}",
                "description": "Executive Intelligence Suite - AI-Driven Metrics & Strategic Insights",
                "cache_ttl": 60
            }
            dash_resp = await client.post(f"{self.base_url}/api/dashboard", headers=headers, json=dash_payload)
            if dash_resp.status_code != 200:
                logger.error(f"[Metabase] Dash creation failed: {dash_resp.text}")
                return None

            dash_id = dash_resp.json()["id"]

            # 2. Create Cards
            created_cards: list[dict] = []
            card_plans = plan.get("cards", []) or []
            for i, card_plan in enumerate(card_plans):
                chart_type = self._map_chart_type(card_plan.get("chart_type", "bar"))
                sql_query = _fix_sql(card_plan.get("sql"), effective_ws_id)
                viz_settings = self._infer_visualization_settings(card_plan.get("chart_type", "bar"), sql_query, card_index=i)

                card_payload = {
                    "name": card_plan["title"],
                    "dataset_query": {
                        "database": db_id,
                        "type": "native",
                        "native": {"query": sql_query}
                    },
                    "display": chart_type,
                    "visualization_settings": viz_settings
                }
                card_resp = await client.post(f"{self.base_url}/api/card", headers=headers, json=card_payload)
                if card_resp.status_code != 200:
                    logger.error(f"[Metabase] Card creation failed ({card_plan.get('title','(untitled)')}): {card_resp.status_code} {card_resp.text}")
                    continue
                created_cards.append({"index": i, "card_id": card_resp.json().get("id"), "plan": card_plan})

            if not created_cards:
                logger.warning("[Metabase] No cards were created from plan; trying fallback cards.")
                fallback_plans = _fallback_cards(effective_ws_id)
                for j, card_plan in enumerate(fallback_plans):
                    chart_type = self._map_chart_type(card_plan.get("chart_type", "bar"))
                    sql_query = _fix_sql(card_plan.get("sql"), effective_ws_id)
                    viz_settings = self._infer_visualization_settings(card_plan.get("chart_type", "bar"), sql_query, card_index=j)

                    card_payload = {
                        "name": card_plan["title"],
                        "dataset_query": {
                            "database": db_id,
                            "type": "native",
                            "native": {"query": sql_query},
                        },
                        "display": chart_type,
                        "visualization_settings": viz_settings,
                    }
                    card_resp = await client.post(f"{self.base_url}/api/card", headers=headers, json=card_payload)
                    if card_resp.status_code != 200:
                        logger.error(
                            f"[Metabase] Fallback card creation failed ({card_plan.get('title','(untitled)')}): "
                            f"{card_resp.status_code} {card_resp.text}"
                        )
                        continue
                    created_cards.append({"index": j, "card_id": card_resp.json().get("id"), "plan": card_plan})

            if not created_cards:
                logger.error("[Metabase] Dashboard created but 0 cards could be created. Not returning an empty URL.")
                return None
            else:
                # 3. Add Cards to Dashboard
                #
                # Metabase v0.52.x does NOT support POST /api/dashboard/:id/cards.
                # The correct endpoint is PUT /api/dashboard/:id/cards with a payload of:
                #   { "cards": [{ "id": <dashcard-id placeholder>, "card_id": <card id>, ... }], "tabs": [...] }
                #
                # `id` is required and must be unique; placeholder values are OK for new cards.

                def _clamp_int(v: object, default: int, lo: int, hi: int) -> int:
                    try:
                        iv = int(v)  # type: ignore[arg-type]
                        return max(lo, min(hi, iv))
                    except Exception:
                        return default

                # Convert the plan's 12-col mental model to Metabase's 24-col grid.
                placements: list[dict] = []
                cursor_col = 0
                cursor_row = 0
                row_h = 0
                for j, item in enumerate(created_cards):
                    cp = item["plan"] or {}
                    size_x_12 = _clamp_int(cp.get("size_x"), 12, 1, 12)
                    size_y = _clamp_int(cp.get("size_y"), 6, 2, 18)
                    size_x = max(2, min(24, size_x_12 * 2))
                    if size_x >= 24:
                        if cursor_col != 0:
                            cursor_row += max(1, row_h)
                            cursor_col = 0
                            row_h = 0
                        placements.append({"col": 0, "row": cursor_row, "size_x": 24, "size_y": size_y})
                        cursor_row += size_y
                        continue
                    if cursor_col + size_x > 24:
                        cursor_row += max(1, row_h)
                        cursor_col = 0
                        row_h = 0
                    placements.append({"col": cursor_col, "row": cursor_row, "size_x": size_x, "size_y": size_y})
                    cursor_col += size_x
                    row_h = max(row_h, size_y)

                cards_payload: list[dict] = []
                for idx, item in enumerate(created_cards):
                    card_id = item.get("card_id")
                    if not card_id:
                        continue
                    place = placements[idx] if idx < len(placements) else {"col": 0, "row": idx * 6, "size_x": 24, "size_y": 6}
                    # Cyberpunk Dark Theme: Deep navy/black backgrounds with neon accents
                    card_viz_settings = {}
                    # Premium White & Red Theme
                    card_viz_settings = {}
                    # Using a subtle shadow and border to make cards "pop" on white background
                    card_viz_settings["card.background_color"] = "#ffffff" if idx % 2 == 0 else "#fff5f5"
                    card_viz_settings["card.border_style"] = "none" # Metabase doesn't support 1px solid easily via this key
                    card_viz_settings["graph.show_values"] = False
                    card_viz_settings["text.align"] = "center"

                    cards_payload.append(
                        {
                            "id": -(idx + 1),
                            "card_id": card_id,
                            "col": place["col"],
                            "row": place["row"],
                            "size_x": place["size_x"],
                            "size_y": place["size_y"],
                            "parameter_mappings": [],
                            "visualization_settings": card_viz_settings,
                            "series": [],
                        }
                    )

                put_payload = {"cards": cards_payload, "tabs": []}
                put_resp = await client.put(
                    f"{self.base_url}/api/dashboard/{dash_id}/cards",
                    headers=headers,
                    json=put_payload,
                    timeout=20.0,
                )
                if put_resp.status_code != 200:
                    logger.error(f"[Metabase] Failed to add cards to dashboard: {put_resp.status_code} {put_resp.text}")
                    return None

                # Verify dashboard has cards (helps debug empty public links)
                try:
                    dash_get = await client.get(f"{self.base_url}/api/dashboard/{dash_id}", headers=headers, timeout=10.0)
                    if dash_get.status_code == 200:
                        dash_json = dash_get.json()
                        dashcards = dash_json.get("dashcards") or []
                        if isinstance(dashcards, list) and len(dashcards) == 0:
                            logger.error("[Metabase] Dashboard created but still has 0 dashcards after PUT /cards.")
                            return None
                except Exception as e:
                    logger.warning(f"[Metabase] Dashboard verification failed: {e}")

            # 4. Create public link so no login is required
            public_uuid = None
            public_url = None
            for attempt in range(3):
                try:
                    pub_resp = await client.post(
                        f"{self.base_url}/api/dashboard/{dash_id}/public_link",
                        headers=headers,
                        timeout=10.0,
                    )
                    if pub_resp.status_code == 200:
                        public_uuid = pub_resp.json().get("uuid")
                        if public_uuid:
                            public_url = f"{self.base_url}/public/dashboard/{public_uuid}"
                            logger.info(f"[Metabase] Public dashboard generated on attempt {attempt+1}: {public_url}")
                            break
                    
                    if attempt < 2:
                        logger.warning(f"[Metabase] Public link creation attempt {attempt+1} failed ({pub_resp.status_code}). Retrying...")
                        await asyncio.sleep(1.5) # Wait for Metabase to settle
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(1.5)
                        continue
                    logger.error(f"[Metabase] Public link creation error: {str(e)}")
            # CRITICAL: We MUST have a public URL for the proxy to work.
            if not public_url:
                logger.error("[Metabase] All attempts to create public link failed.")
            
            return public_url

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

    # Premium Strategic Palette: Red & Slates
    _COLOR_PALETTE = [
        "#ef4444", # Strategic Red
        "#1e293b", # Deep Slate
        "#f87171", # Light Red
        "#64748b", # Medium Slate
        "#b91c1c", # Crimson
        "#94a3b8", # Blue Slate
        "#dc2626", # Vibrant Red
        "#475569", # Slate Gray
        "#fca5a5", # Rose Red
        "#334155", # Cool Slate
        "#991b1b", # Dark Red
        "#cbd5e1", # Light Slate
    ]

    def _get_card_color(self, card_index: int) -> str:
        """Return a color from the palette based on card index."""
        return self._COLOR_PALETTE[card_index % len(self._COLOR_PALETTE)]

    def _infer_visualization_settings(self, chart_type: str, sql: str, card_index: int = 0) -> dict:
        """Infer visualization settings from chart type and SQL query.

        For bar, line, area charts, Metabase needs to know which columns to use
        for x-axis (dimensions) and y-axis (metrics). Also applies custom colors.
        """
        import re

        settings: dict = {}
        color = self._get_card_color(card_index)

        def _extract_aliases(sql_text: str) -> list[str]:
            select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql_text, re.IGNORECASE | re.DOTALL)
            if not select_match:
                return []
            columns_part = select_match.group(1)
            aliases = re.findall(r'\bAS\s+(\w+)\b', columns_part, re.IGNORECASE)
            if aliases:
                return aliases
            parts = columns_part.split(",")
            result = []
            skip_words = {'count', 'sum', 'avg', 'min', 'max', 'date', 'substr', 'cast', 'real'}
            for part in parts:
                words = re.findall(r'\b(\w+)\b', part.strip())
                for w in reversed(words or []):
                    if w.lower() not in skip_words:
                        result.append(w)
                        break
            return result

        if chart_type in ("bar", "line", "area"):
            aliases = _extract_aliases(sql)
            if len(aliases) >= 2:
                settings["graph.dimensions"] = [aliases[0]]
                settings["graph.metrics"] = aliases[1:]
            elif len(aliases) == 1:
                settings["graph.metrics"] = [aliases[0]]

            if not settings.get("graph.dimensions"):
                settings["graph.dimensions"] = ["day"]
            if not settings.get("graph.metrics"):
                settings["graph.metrics"] = ["count"]

            # Apply color and style to series
            metric_cols = settings.get("graph.metrics", [])
            if metric_cols:
                series_colors = {}
                series_settings = {}
                for i, col in enumerate(metric_cols):
                    # Default color
                    main_color = self._COLOR_PALETTE[(card_index + i) % len(self._COLOR_PALETTE)]
                    series_settings[col] = {"color": main_color}
                    
                    # Special styling for "Target" or "Goal" columns
                    if col.lower() in ("target", "goal", "benchmark"):
                        series_settings[col]["line_style"] = "dash"
                        series_settings[col]["color"] = "#94a3b8" # Neutral slate for benchmark
                        series_settings[col]["display"] = "line" # Force line even if chart is area/bar

                settings["series_settings"] = series_settings
                
                # High-Contrast Axis Styling
                settings["graph.x_axis.colors"] = ["#1e293b"]
                settings["graph.y_axis.colors"] = ["#1e293b"]
                settings["graph.grid_color"] = "#f1f5f9"

            # Smooth lines and markers for line/area charts for a premium look
            if chart_type in ("line", "area"):
                settings["line.interpolate"] = "cardinal"
                settings["line.marker_enabled"] = True
                settings["line.marker_style"] = "circle"
                settings["graph.show_values"] = False
                
                # Area charts look amazing when stacked, UNLESS we have a target line
                has_target = any(c.lower() in ("target", "goal", "benchmark") for c in metric_cols)
                if chart_type == "area" and not has_target:
                    settings["stackable.stack_type"] = "stacked"
                else:
                    settings["stackable.stack_type"] = None

        elif chart_type == "pie":
            aliases = _extract_aliases(sql)
            if len(aliases) >= 2:
                settings["pie.dimension"] = aliases[0]
                settings["pie.metric"] = aliases[1]
            # Pie-specific: use vibrant slice colors
            settings["pie.colors"] = {
                str(i): self._COLOR_PALETTE[i % len(self._COLOR_PALETTE)]
                for i in range(12)
            }

        elif chart_type == "scalar":
            settings["scalar.field"] = "value"

        elif chart_type == "row":
            aliases = _extract_aliases(sql)
            if len(aliases) >= 2:
                settings["graph.dimensions"] = [aliases[0]]
                settings["graph.metrics"] = aliases[1:]
            metric_cols = settings.get("graph.metrics", [])
            if metric_cols:
                settings["series_settings"] = {
                    col: {"color": self._COLOR_PALETTE[(card_index + i) % len(self._COLOR_PALETTE)]}
                    for i, col in enumerate(metric_cols)
                }

        return settings

metabase_service = MetabaseService()
