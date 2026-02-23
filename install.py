#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_WORKFLOW_DIR = REPO_ROOT / "frontend" / "workflow"
FRONTEND_DASHBOARD_DIR = REPO_ROOT / "frontend" / "dashboard"
EVIDENCE_DIR = REPO_ROOT / "evidence"

METABASE_JAR_URL = "https://downloads.metabase.com/latest/metabase.jar"


def _print(msg: str) -> None:
    sys.stdout.write(msg.rstrip() + "\n")
    sys.stdout.flush()

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


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)


def _which(exe: str) -> str | None:
    p = shutil.which(exe)
    return str(p) if p else None


def _npm_cmd() -> str:
    # On Windows, prefer npm.cmd (batch script). Using "npm" can fail under CreateProcess.
    if os.name == "nt":
        return _which("npm.cmd") or _which("npm") or "npm.cmd"
    return _which("npm") or "npm"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    if dest.exists() and dest.stat().st_size > 0:
        return
    _print(f"Downloading {url} -> {dest}")
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f)
    tmp.replace(dest)

def _looks_like_service_account_json(path: Path) -> bool:
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        return isinstance(data, dict) and data.get("type") == "service_account" and bool(data.get("client_email"))
    except Exception:
        return False


def _detect_java_exe() -> Path | None:
    candidates: list[Path] = []
    for d in sorted(BACKEND_DIR.glob("jdk-*")):
        if d.is_dir():
            candidates.append(d / ("bin/java.exe" if os.name == "nt" else "bin/java"))
    for c in candidates:
        if c.exists():
            return c
    sys_java = _which("java.exe" if os.name == "nt" else "java")
    return Path(sys_java) if sys_java else None


def _java_major(java_exe: Path) -> int | None:
    try:
        out = subprocess.check_output([str(java_exe), "-version"], stderr=subprocess.STDOUT, text=True)
    except Exception:
        return None
    # Example: 'java version "21.0.2" ...' or 'openjdk version "21.0.2" ...'
    m = re.search(r'version\s+"(\d+)(?:\.\d+)?', out)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"Unsafe zip entry: {member.filename}")
        zf.extractall(dest_dir)


def _safe_extract_tar(tar_path: Path, dest_dir: Path) -> None:
    with tarfile.open(tar_path, "r:*") as tf:
        for member in tf.getmembers():
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"Unsafe tar entry: {member.name}")
        tf.extractall(dest_dir)


def _adoptium_platform() -> tuple[str, str, str]:
    sys_name = platform.system().lower()
    mach = platform.machine().lower()

    if sys_name.startswith("win"):
        os_name = "windows"
        archive = "zip"
    elif sys_name.startswith("darwin") or sys_name.startswith("mac"):
        os_name = "mac"
        archive = "tar.gz"
    elif sys_name.startswith("linux"):
        os_name = "linux"
        archive = "tar.gz"
    else:
        raise RuntimeError(f"Unsupported OS for auto-JDK download: {platform.system()}")

    if mach in ("x86_64", "amd64"):
        arch = "x64"
    elif mach in ("aarch64", "arm64"):
        arch = "aarch64"
    else:
        raise RuntimeError(f"Unsupported CPU arch for auto-JDK download: {platform.machine()}")

    return os_name, arch, archive


def _ensure_java21(*, yes: bool) -> Path | None:
    java_exe = _detect_java_exe()
    if java_exe:
        major = _java_major(java_exe)
        if major and major >= 21:
            return java_exe

    # Downloading a JDK is often blocked in corporate environments; do not do it by default.
    if not yes:
        want = _prompt_yes_no("Java 21+ not detected. Download a portable JDK 21 into backend/ (optional)?", default=False)
        if not want:
            return None

    try:
        os_name, arch, archive = _adoptium_platform()
    except Exception:
        return None

    url = f"https://api.adoptium.net/v3/binary/latest/21/ga/{os_name}/{arch}/jdk/hotspot/normal/eclipse?project=jdk"
    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        archive_path = tmp_dir / f"jdk21.{archive.replace('.', '') if archive != 'zip' else 'zip'}"
        _download(url, archive_path)

        _print(f"Extracting {archive_path} -> {BACKEND_DIR}")
        if archive == "zip":
            _safe_extract_zip(archive_path, BACKEND_DIR)
        else:
            _safe_extract_tar(archive_path, BACKEND_DIR)

    java_exe = _detect_java_exe()
    if java_exe and (_java_major(java_exe) or 0) >= 21:
        return java_exe
    return None


def _venv_python() -> Path:
    if os.name == "nt":
        return BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    return BACKEND_DIR / "venv" / "bin" / "python"


def _ensure_backend_venv() -> Path:
    vpy = _venv_python()
    if vpy.exists():
        return vpy
    _print("Creating backend virtualenv (backend/venv)...")
    _run([sys.executable, "-m", "venv", str(BACKEND_DIR / "venv")], cwd=BACKEND_DIR)
    if not vpy.exists():
        raise RuntimeError("Failed to create backend virtualenv.")
    return vpy


def _ensure_backend_deps(vpy: Path) -> None:
    sentinel = BACKEND_DIR / "venv" / ".deps_installed"
    if sentinel.exists():
        return
    _print("Installing backend dependencies...")
    _run([str(vpy), "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.txt"], cwd=BACKEND_DIR)
    sentinel.write_text("ok\n", encoding="utf-8")


def _ensure_node() -> None:
    if not _which("node"):
        raise RuntimeError("Node.js is required but was not found on PATH.")
    if os.name == "nt":
        if not (_which("npm.cmd") or _which("npm")):
            raise RuntimeError("npm is required but was not found on PATH.")
    else:
        if not _which("npm"):
            raise RuntimeError("npm is required but was not found on PATH.")


def _ensure_frontend_deps(app_dir: Path) -> None:
    if not app_dir.exists():
        return
    node_modules = app_dir / "node_modules"
    if node_modules.exists():
        return
    _print(f"Installing frontend dependencies: {app_dir.relative_to(REPO_ROOT)}")
    _run([_npm_cmd(), "install"], cwd=app_dir)

def _ensure_service_account(*, yes: bool) -> bool:
    """Ensure backend/service-account.json exists if the user wants Gemini service account auth."""
    sa_dest = BACKEND_DIR / "service-account.json"
    if sa_dest.exists():
        return True

    if yes:
        _print("NOTE: backend/service-account.json not found. If you want Gemini Vertex, add it later.")
        return False

    want = _prompt_yes_no("Do you want to use a Gemini Vertex service account JSON?", default=True)
    if not want:
        return False

    while True:
        p = _prompt("Path to your service-account.json (it will be copied into backend/): ")
        if not p:
            _print("Please enter a path (or Ctrl+C to cancel).")
            continue
        src = Path(p).expanduser()
        if not src.is_file():
            _print("File not found. Try again.")
            continue
        if not _looks_like_service_account_json(src):
            ok = _prompt_yes_no("That file does not look like a Google service account JSON. Copy anyway?", default=False)
            if not ok:
                continue
        sa_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, sa_dest)
        _print("Copied to backend/service-account.json (gitignored).")
        return True


def _env_get(env_text: str, key: str) -> str | None:
    m = re.search(rf"(?m)^[ \t]*{re.escape(key)}=(.*)$", env_text)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")


def _env_set(env_text: str, key: str, value: str) -> str:
    line = f"{key}={value}"
    if re.search(rf"(?m)^[ \t]*{re.escape(key)}=", env_text):
        return re.sub(rf"(?m)^[ \t]*{re.escape(key)}=.*$", line, env_text)
    if not env_text.endswith("\n"):
        env_text += "\n"
    return env_text + line + "\n"


def _ensure_env(*, yes: bool) -> tuple[str, str]:
    env_path = BACKEND_DIR / ".env"
    example_path = BACKEND_DIR / ".env.example"
    if not env_path.exists():
        _print("Creating backend/.env from backend/.env.example ...")
        shutil.copyfile(example_path, env_path)

    env_text = _read_text(env_path)

    # LLM setup (prompt-friendly). Prefer Gemini Vertex when service account exists.
    sa_path = BACKEND_DIR / "service-account.json"
    if sa_path.exists():
        env_text = _env_set(env_text, "LLM_PROVIDER", "gemini")
        env_text = _env_set(env_text, "GEMINI_SERVICE_ACCOUNT_FILE", "service-account.json")
    else:
        # If no service account, allow the user to choose Ollama or Gemini API key.
        if not yes:
            use_gemini_key = _prompt_yes_no("No service account found. Use Gemini API key instead of Ollama?", default=False)
            if use_gemini_key:
                key = _prompt("Enter GEMINI_API_KEY (input hidden not supported; paste carefully): ").strip()
                if key:
                    env_text = _env_set(env_text, "LLM_PROVIDER", "gemini")
                    env_text = _env_set(env_text, "GEMINI_API_KEY", key)
                else:
                    _print("No key entered; leaving LLM_PROVIDER unchanged.")

    # GitHub token (recommended) to avoid rate limits.
    gh = _env_get(env_text, "GITHUB_TOKEN") or ""
    if not gh and not yes:
        tok = _prompt("GitHub token (recommended; press Enter to skip): ").strip()
        if tok:
            env_text = _env_set(env_text, "GITHUB_TOKEN", tok)

    # Metabase creds: auto-generate if missing (so user isn't blocked).
    mb_user = _env_get(env_text, "METABASE_USERNAME") or ""
    mb_pass = _env_get(env_text, "METABASE_PASSWORD") or ""
    if not mb_user:
        if yes:
            mb_user = "admin@example.com"
        else:
            mb_user = input("Metabase admin email (METABASE_USERNAME) [admin@example.com]: ").strip() or "admin@example.com"
        env_text = _env_set(env_text, "METABASE_USERNAME", mb_user)

    generated_pass = ""
    if not mb_pass:
        if yes:
            generated_pass = secrets.token_urlsafe(24)
            mb_pass = generated_pass
        else:
            mb_pass = input("Metabase admin password (METABASE_PASSWORD) [auto-generate]: ").strip()
            if not mb_pass:
                generated_pass = secrets.token_urlsafe(24)
                mb_pass = generated_pass
        env_text = _env_set(env_text, "METABASE_PASSWORD", mb_pass)

    if not (_env_get(env_text, "METABASE_URL") or "").strip():
        env_text = _env_set(env_text, "METABASE_URL", "http://localhost:3003")

    _write_text(env_path, env_text)
    return mb_user, generated_pass


def main() -> int:
    ap = argparse.ArgumentParser(description="One-command installer for Git Metrics Detector")
    ap.add_argument("--yes", action="store_true", help="Non-interactive; auto-fill missing settings")
    ap.add_argument("--download-jdk", action="store_true", help="Allow downloading a portable Java 21 into backend/jdk-*")
    args = ap.parse_args()

    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10+ is required.")

    _print("== Git Metrics Detector: install ==")

    _ensure_node()

    # Optional but recommended: set up service account locally (prompts).
    _ensure_service_account(yes=args.yes)

    vpy = _ensure_backend_venv()
    _ensure_backend_deps(vpy)

    _ensure_frontend_deps(FRONTEND_WORKFLOW_DIR)
    _ensure_frontend_deps(FRONTEND_DASHBOARD_DIR)
    if EVIDENCE_DIR.exists():
        _ensure_frontend_deps(EVIDENCE_DIR)

    jar_path = BACKEND_DIR / "metabase.jar"
    if not jar_path.exists():
        _download(METABASE_JAR_URL, jar_path)

    mb_user, generated_pass = _ensure_env(yes=args.yes)

    java_exe = None
    if args.download_jdk:
        java_exe = _ensure_java21(yes=args.yes)
    else:
        java_exe = _detect_java_exe()
        if java_exe:
            major = _java_major(java_exe)
            if not major or major < 21:
                java_exe = None

    if not java_exe:
        _print("NOTE: Java 21+ was not detected. Metabase will NOT start until Java 21+ is available.")
        _print("Fix options (manual):")
        _print("  - Install Java 21+ system-wide, OR")
        _print("  - Download a JDK 21 zip/tar.gz yourself and unpack to backend/jdk-* (so backend/jdk-*/bin/java exists).")
        _print("  - If allowed, re-run: python install.py --download-jdk")

    _print("")
    _print("Install complete.")
    _print("Next: run the stack with:  python run.py")
    _print("")
    _print("Metabase admin credentials (saved in backend/.env):")
    _print(f"  METABASE_USERNAME={mb_user}")
    if generated_pass:
        _print(f"  METABASE_PASSWORD={generated_pass}")
        _print("  (Password was auto-generated; keep it safe.)")
    else:
        _print("  METABASE_PASSWORD=(as set in backend/.env)")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        _print("\nCancelled.")
        raise
    except Exception as e:
        _print(f"\nERROR: {e}")
        raise SystemExit(1)
