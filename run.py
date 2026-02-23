#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_WORKFLOW_DIR = REPO_ROOT / "frontend" / "workflow"
FRONTEND_DASHBOARD_DIR = REPO_ROOT / "frontend" / "dashboard"
EVIDENCE_DIR = REPO_ROOT / "evidence"
LOGS_DIR = REPO_ROOT / "logs"


def _print(msg: str) -> None:
    sys.stdout.write(msg.rstrip() + "\n")
    sys.stdout.flush()


def _venv_python() -> Path:
    if os.name == "nt":
        return BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    return BACKEND_DIR / "venv" / "bin" / "python"


def _find_java_exe() -> str:
    # Prefer portable JDK under backend/jdk-*
    for d in sorted(BACKEND_DIR.glob("jdk-*")):
        if not d.is_dir():
            continue
        p = d / ("bin/java.exe" if os.name == "nt" else "bin/java")
        if p.exists():
            return str(p)
    return shutil.which("java.exe" if os.name == "nt" else "java") or ""


def _java_major(java_exe: str) -> int | None:
    try:
        out = subprocess.check_output([java_exe, "-version"], stderr=subprocess.STDOUT, text=True)
    except Exception:
        return None
    m = re.search(r'version\s+"(\d+)(?:\.\d+)?', out)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _ensure_cmd(name: str) -> str:
    # On Windows, prefer the .cmd shim for npm/npx (CreateProcess won't run .cmd reliably via bare name).
    if os.name == "nt" and name.lower() in ("npm", "npx"):
        p_cmd = shutil.which(name + ".cmd")
        if p_cmd:
            return p_cmd

    p = shutil.which(name)
    if p:
        # If PATH resolves to an extensionless file but a .cmd exists next to it, use the .cmd.
        if os.name == "nt" and Path(p).suffix == "" and (Path(p).with_suffix(".cmd")).exists():
            return str(Path(p).with_suffix(".cmd"))
        return p

    if os.name == "nt":
        for ext in (".cmd", ".exe", ".bat"):
            p2 = shutil.which(name + ext)
            if p2:
                return p2
    raise RuntimeError(f"Required command not found on PATH: {name}")


def _http_json(method: str, url: str, payload: dict | None = None, *, timeout: float = 10.0) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8") or "{}")


def _url_reachable(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            return 200 <= resp.status < 500
    except urllib.error.HTTPError as e:
        # 4xx/5xx still means the server is responding.
        return 200 <= int(getattr(e, "code", 0) or 0) < 600
    except Exception:
        return False


def _url_responding(url: str) -> bool:
    """Return True if the host responds over HTTP (any status code)."""
    try:
        with urllib.request.urlopen(url, timeout=2.0):
            return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def _port_is_free(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def _parse_metabase_url(backend_env: dict[str, str]) -> tuple[str, int]:
    raw = (backend_env.get("METABASE_URL") or os.getenv("METABASE_URL") or "http://localhost:3003").strip()
    parsed = urlparse(raw if "://" in raw else "http://" + raw)
    host = parsed.hostname or "localhost"
    port = parsed.port or 3003
    base = f"{parsed.scheme or 'http'}://{host}:{port}"
    return base.rstrip("/"), port


def _read_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            env[k] = v
    except Exception:
        pass
    return env


def _prompt(text: str) -> str:
    if not (sys.stdin and sys.stdin.isatty()):
        return ""
    try:
        return input(text).strip()
    except EOFError:
        return ""


def _prompt_yes_no(text: str, *, default: bool = True) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        ans = _prompt(text + suffix).lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        _print("Please answer y or n.")


def _wait_url_ok(url: str, *, timeout_s: float, interval_s: float = 0.5) -> None:
    start = time.time()
    last_err = ""
    last_print = 0.0
    while time.time() - start < timeout_s:
        try:
            with urllib.request.urlopen(url, timeout=3.0) as resp:
                if 200 <= resp.status < 500:
                    return
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        now = time.time()
        if now - last_print > 3.0:
            elapsed = int(now - start)
            _print(f"  ...waiting ({elapsed}s) for {url}")
            last_print = now
        time.sleep(interval_s)
    raise RuntimeError(f"Timed out waiting for {url}. Last error: {last_err}")


def _wait_url_responding(url: str, *, timeout_s: float, interval_s: float = 0.5) -> None:
    start = time.time()
    last_print = 0.0
    while time.time() - start < timeout_s:
        if _url_responding(url):
            return
        now = time.time()
        if now - last_print > 3.0:
            elapsed = int(now - start)
            _print(f"  ...waiting ({elapsed}s) for {url}")
            last_print = now
        time.sleep(interval_s)
    raise RuntimeError(f"Timed out waiting for {url} to respond.")


def _start_proc(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.Popen:
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    return subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env or os.environ.copy(),
        creationflags=creationflags,
    )


def _terminate(proc: subprocess.Popen) -> None:
    try:
        if proc.poll() is not None:
            return
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            time.sleep(1.0)
        proc.terminate()
        try:
            proc.wait(timeout=8.0)
        except subprocess.TimeoutExpired:
            proc.kill()
    except Exception:
        pass


def _run_e2e(*, repo_url: str, timeout_s: float, github_token: str = "") -> None:
    _print(f"Running E2E test: analyze -> mock data -> metabase ({repo_url})")

    backend_env = _read_env_file(BACKEND_DIR / ".env")
    token = (github_token or "").strip() or (backend_env.get("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        token = _prompt("GitHub token for E2E test (recommended; press Enter to try without): ").strip()
    if not token:
        _print("WARNING: No GitHub token provided. GitHub API rate limits may cause the test to fail.")

    payload: dict = {"repo_url": repo_url, "force": True}
    if token:
        payload["github_token"] = token

    job = _http_json(
        "POST",
        "http://localhost:8001/api/workflow/analyze",
        payload,
        timeout=30.0,
    )
    job_id = job.get("id")
    if not job_id:
        raise RuntimeError(f"Analyze did not return job id: {job}")

    ws_id = None
    start = time.time()
    last_print = 0.0
    while time.time() - start < timeout_s:
        j = _http_json("GET", f"http://localhost:8001/api/workflow/jobs/{job_id}", None, timeout=10.0)
        status = j.get("status")
        ws_id = j.get("workspace_id") or ws_id
        if status == "completed":
            break
        if status == "failed":
            err = j.get("error_message") or "Analysis failed"
            if "rate limit" in str(err).lower():
                raise RuntimeError(
                    f"Analysis failed due to GitHub rate limit.\n"
                    f"Fix: set GITHUB_TOKEN in backend/.env (or pass --github-token) and retry.\n"
                    f"Details: {err}"
                )
            raise RuntimeError(f"Analysis failed: {err}")
        now = time.time()
        if now - last_print > 5.0:
            stage = j.get("current_stage")
            msg = j.get("progress_message") or ""
            _print(f"  status={status} stage={stage} {msg}")
            last_print = now
        time.sleep(1.0)
    else:
        raise RuntimeError("Timed out waiting for analysis to complete.")

    if not ws_id:
        raise RuntimeError("Analysis completed but no workspace_id was returned.")

    md = _http_json(
        "POST",
        f"http://localhost:8001/api/workflow/workspaces/{ws_id}/mock-data",
        {},
        timeout=120.0,
    )
    if (md.get("status") != "success") or md.get("metabase_error"):
        raise RuntimeError(f"Mock data / Metabase failed: {md.get('metabase_error') or md}")

    mb_url = md.get("metabase_url")
    if not mb_url:
        raise RuntimeError(f"No metabase_url returned: {md}")

    _print(f"E2E OK. Metabase URL: {mb_url}")


def main() -> int:
    ap = argparse.ArgumentParser(description="One-command runner for Git Metrics Detector")
    ap.add_argument("--startup-timeout", type=float, default=60.0, help="Startup timeout seconds")
    ap.add_argument("--e2e-timeout", type=float, default=240.0, help="End-to-end analysis timeout seconds")
    ap.add_argument("--timeout", type=float, default=None, help="(deprecated) Sets both --startup-timeout and --e2e-timeout")
    ap.add_argument("--no-metabase", action="store_true", help="Do not start Metabase")
    ap.add_argument("--smoke", action="store_true", help="Start services, verify URLs, then exit")
    ap.add_argument("--test", action="store_true", help="Run end-to-end test then exit")
    ap.add_argument("--repo", default="https://github.com/octocat/Hello-World", help="Repo URL for --test")
    ap.add_argument("--github-token", default="", help="GitHub token for --test (overrides backend/.env)")
    args = ap.parse_args()

    if args.timeout is not None:
        args.startup_timeout = float(args.timeout)
        args.e2e_timeout = float(args.timeout)

    _ensure_cmd("node")
    npm_cmd = _ensure_cmd("npm")

    vpy = _venv_python()
    if not vpy.exists():
        raise RuntimeError("backend/venv is missing. Run: python install.py")

    if not (FRONTEND_WORKFLOW_DIR / "node_modules").exists():
        raise RuntimeError("frontend/workflow/node_modules missing. Run: python install.py")
    if not (FRONTEND_DASHBOARD_DIR / "node_modules").exists():
        raise RuntimeError("frontend/dashboard/node_modules missing. Run: python install.py")

    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        raise RuntimeError("backend/.env missing. Run: python install.py")

    backend_env = _read_env_file(env_path)
    llm_provider = (backend_env.get("LLM_PROVIDER") or "").strip().lower()
    if llm_provider == "gemini":
        sa = (backend_env.get("GEMINI_SERVICE_ACCOUNT_FILE") or "").strip()
        api_key = (backend_env.get("GEMINI_API_KEY") or "").strip()
        if not sa and not api_key:
            _print("WARNING: LLM_PROVIDER=gemini but GEMINI_SERVICE_ACCOUNT_FILE / GEMINI_API_KEY is not set.")
            _print("Fix: run `python install.py` again or edit backend/.env.")

    if not (backend_env.get("METABASE_USERNAME") or "").strip() or not (backend_env.get("METABASE_PASSWORD") or "").strip():
        _print("WARNING: METABASE_USERNAME/METABASE_PASSWORD not set in backend/.env.")
        _print("Generate mock data will fail until you set them (or re-run `python install.py`).")

    procs: list[subprocess.Popen] = []
    try:
        _print("== Git Metrics Detector: run ==")

        backend_running = _url_reachable("http://localhost:8001/api/health")
        metabase_base, metabase_port = _parse_metabase_url(backend_env)
        effective_metabase_base = metabase_base
        effective_metabase_port = metabase_port

        if not args.no_metabase and not backend_running:
            configured_props = f"{metabase_base}/api/session/properties"
            if (not _url_reachable(configured_props)) and (not _port_is_free(metabase_port)):
                for cand in range(3004, 3016):
                    if _port_is_free(cand):
                        effective_metabase_port = cand
                        effective_metabase_base = f"http://localhost:{cand}"
                        _print(f"NOTE: Port {metabase_port} is busy; using Metabase on {effective_metabase_base}")
                        break

        _print("[1/4] Backend (8001)...")
        if backend_running:
            _print("  already running")
        else:
            env_backend = os.environ.copy()
            if not args.no_metabase:
                env_backend["METABASE_URL"] = effective_metabase_base
            procs.append(
                _start_proc(
                    [str(vpy), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
                    cwd=BACKEND_DIR,
                    env=env_backend,
                )
            )
            _wait_url_ok("http://localhost:8001/api/health", timeout_s=args.startup_timeout)

        _print("[2/4] Workflow UI (3001)...")
        if _url_reachable("http://localhost:3001"):
            _print("  already running")
        else:
            procs.append(_start_proc([npm_cmd, "run", "dev", "--", "--host", "--port", "3001"], cwd=FRONTEND_WORKFLOW_DIR))
            _wait_url_ok("http://localhost:3001", timeout_s=args.startup_timeout)

        _print("[3/4] Workspaces UI (3000)...")
        if _url_reachable("http://localhost:3000"):
            _print("  already running")
        else:
            procs.append(_start_proc([npm_cmd, "run", "dev", "--", "--host", "--port", "3000"], cwd=FRONTEND_DASHBOARD_DIR))
            _wait_url_ok("http://localhost:3000", timeout_s=args.startup_timeout)

        if not args.no_metabase:
            jar = BACKEND_DIR / "metabase.jar"
            if not jar.exists():
                raise RuntimeError("backend/metabase.jar is missing. Run: python install.py")

            _print("[4/4] Metabase (3003)...")
            effective_props = f"{effective_metabase_base}/api/session/properties"
            if _url_responding(effective_props):
                _print("  already running")
            else:
                if backend_running and (not _port_is_free(metabase_port)):
                    raise RuntimeError(
                        f"Metabase port {metabase_port} is busy and Metabase is not reachable at {metabase_base}. "
                        "Stop the process using that port, or stop the existing backend and re-run `python run.py`."
                    )
                java_exe = _find_java_exe()
                if not java_exe:
                    if args.test:
                        raise RuntimeError("java not found. Install Java 21+ (required for Metabase) and retry.")
                    _print("  NOTE: java not found; skipping Metabase. Install Java 21+ to enable it.")

                if java_exe:
                    major = _java_major(java_exe) or 0
                    if major < 21:
                        if args.test:
                            raise RuntimeError(f"Java 21+ required for Metabase. Detected Java {major}.")
                        _print(f"  NOTE: Java 21+ required for Metabase. Detected Java {major}; skipping Metabase.")
                        java_exe = ""

                if java_exe:
                    env = os.environ.copy()
                    env["MB_JETTY_PORT"] = str(effective_metabase_port)
                    creationflags = 0
                    if os.name == "nt":
                        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
                    LOGS_DIR.mkdir(exist_ok=True)
                    mb_log_path = LOGS_DIR / "metabase.log"
                    mb_log = open(mb_log_path, "ab", buffering=0)
                    mb_proc = subprocess.Popen(
                        [java_exe, "-jar", str(jar)],
                        cwd=str(BACKEND_DIR),
                        env=env,
                        creationflags=creationflags,
                        stdout=mb_log,
                        stderr=mb_log,
                    )
                    procs.append(mb_proc)
                    time.sleep(1.5)
                    if mb_proc.poll() is not None:
                        raise RuntimeError(
                            "Metabase exited immediately. Common causes: port already in use or Java < 21. "
                            f"Try freeing port {effective_metabase_port} or install Java 21+. "
                            f"See logs: {mb_log_path}"
                        )

                    # Metabase often returns 503 while initializing; that's still "up enough" for dev startup.
                    wait_s = args.startup_timeout if args.test else min(args.startup_timeout, 8.0)
                    try:
                        _wait_url_responding(effective_props, timeout_s=wait_s)
                    except RuntimeError:
                        if args.test:
                            raise
                        _print(f"  NOTE: Metabase is still starting; open {effective_metabase_base} and wait ~30-60s.")

        _print("")
        _print("Ready:")
        _print("  Workflow:   http://localhost:3001")
        _print("  Workspaces: http://localhost:3000")
        _print("  Backend:    http://localhost:8001/docs")
        if not args.no_metabase:
            _print(f"  Metabase:   {effective_metabase_base}")

        if args.smoke:
            _print("")
            _print("Smoke OK.")
            return 0

        if args.test:
            _run_e2e(repo_url=args.repo, timeout_s=args.e2e_timeout, github_token=str(args.github_token or ""))
            return 0

        _print("")
        _print("Press Ctrl+C to stop.")
        while True:
            time.sleep(0.5)
    finally:
        for p in reversed(procs):
            _terminate(p)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        _print("\nStopping...")
        raise
    except urllib.error.HTTPError as e:
        _print(f"\nERROR: HTTP {e.code} {e.reason}")
        raise SystemExit(1)
    except Exception as e:
        _print(f"\nERROR: {e}")
        raise SystemExit(1)
