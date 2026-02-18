EXCLUDED_EXTENSIONS = {
    # Binary / compiled
    ".exe", ".dll", ".so", ".dylib", ".o", ".obj", ".a", ".lib",
    ".wasm", ".pyc", ".pyo", ".class", ".jar",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp", ".tiff",
    # Fonts
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    # Media
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac", ".ogg", ".webm",
    # Archives
    ".zip", ".tar", ".gz", ".rar", ".7z", ".bz2",
    # Data (large)
    ".sqlite", ".db", ".sqlite3",
    # PDF / docs
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Maps / sourcemaps
    ".map",
}

EXCLUDED_DIRECTORIES = {
    "node_modules", ".git", "__pycache__", ".next", ".nuxt",
    "dist", "build", "out", ".output", "target", "bin", "obj",
    ".idea", ".vscode", ".vs", ".eclipse",
    "vendor", "bower_components",
    ".tox", ".nox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "coverage", ".nyc_output", "htmlcov",
    ".terraform", ".serverless",
    "venv", ".venv", "env", ".env",
}

EXCLUDED_FILENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Pipfile.lock", "poetry.lock", "Cargo.lock", "composer.lock",
    "Gemfile.lock", "go.sum",
    ".DS_Store", "Thumbs.db", ".gitattributes",
}

PRIORITY_PATTERNS = [
    "README", "readme",
    "package.json", "requirements.txt", "pyproject.toml",
    "Cargo.toml", "go.mod", "build.gradle", "pom.xml",
    "Gemfile", "composer.json",
    "Dockerfile", "docker-compose",
    ".env.example", ".env.sample",
]

PRIORITY_PATH_KEYWORDS = [
    "model", "schema", "migration",
    "route", "router", "controller", "handler", "api",
    "config", "settings",
    "main", "app", "index", "server",
    "service", "middleware",
    "component", "page", "view",
]

MAX_FILE_SIZE = 100_000  # 100KB per file


def should_exclude_path(path: str) -> bool:
    parts = path.split("/")
    for part in parts[:-1]:
        if part in EXCLUDED_DIRECTORIES:
            return True

    filename = parts[-1] if parts else path
    if filename in EXCLUDED_FILENAMES:
        return True

    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext in EXCLUDED_EXTENSIONS:
        return True

    return False


def get_file_priority(path: str) -> int:
    filename = path.split("/")[-1] if "/" in path else path
    path_lower = path.lower()

    for pattern in PRIORITY_PATTERNS:
        if pattern.lower() in filename.lower():
            return 0

    for keyword in PRIORITY_PATH_KEYWORDS:
        if keyword in path_lower:
            return 1

    return 2


def sort_files_by_priority(file_paths: list[str]) -> list[str]:
    return sorted(file_paths, key=get_file_priority)
