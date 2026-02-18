from __future__ import annotations

import asyncio
import base64
from typing import Callable, Optional

import httpx
from urllib.parse import urlparse
from ..utils.file_filters import should_exclude_path, sort_files_by_priority, MAX_FILE_SIZE


GITHUB_API = "https://api.github.com"
SEMAPHORE_LIMIT = 15


def parse_repo_url(url: str) -> tuple:
    """Extract owner and repo name from a GitHub URL."""
    parsed = urlparse(url.strip().rstrip("/"))
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub repo URL: {url}")
    owner = parts[0]
    repo = parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _headers(token: Optional[str]) -> dict:
    h = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Git-Metrics-Detector/1.0",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def fetch_repo_tree(owner: str, repo: str, token: Optional[str] = None) -> list:
    """Fetch the full file tree of a repo using the Git Trees API."""
    async with httpx.AsyncClient(timeout=30) as client:
        # Get the default branch SHA
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}",
            headers=_headers(token),
        )
        resp.raise_for_status()
        default_branch = resp.json()["default_branch"]

        # Get the tree recursively
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
            headers=_headers(token),
        )
        resp.raise_for_status()
        tree = resp.json()

        file_paths = []
        for item in tree.get("tree", []):
            if item["type"] == "blob" and not should_exclude_path(item["path"]):
                size = item.get("size", 0)
                if size <= MAX_FILE_SIZE:
                    file_paths.append(item["path"])

        return sort_files_by_priority(file_paths)


async def fetch_file_content(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    path: str,
    token: Optional[str],
    semaphore: asyncio.Semaphore,
) -> Optional[dict]:
    """Fetch a single file's content from GitHub."""
    async with semaphore:
        try:
            resp = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
                headers=_headers(token),
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            if data.get("encoding") == "base64" and data.get("content"):
                try:
                    content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                    return {"path": path, "content": content}
                except Exception:
                    return None
            return None
        except Exception:
            return None


async def fetch_files_batch(
    owner: str,
    repo: str,
    paths: list,
    token: Optional[str] = None,
    on_progress: Optional[Callable] = None,
) -> list:
    """Fetch multiple files concurrently with a semaphore."""
    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
    results = []

    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [
            fetch_file_content(client, owner, repo, path, token, semaphore)
            for path in paths
        ]

        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1
            if result:
                results.append(result)
            if on_progress:
                await on_progress(completed)

    return results
