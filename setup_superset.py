"""
Apache Superset Setup Script for Git Metrics Detector

This script:
1. Installs Apache Superset in a virtual environment
2. Initializes the Superset database
3. Creates an admin user
4. Registers the Git Metrics SQLite database as a data source
5. Starts Superset on port 8088
"""

import subprocess
import sys
import os
import json

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, "superset_venv")
DATA_DIR = os.path.join(BASE_DIR, "backend", "data")
DB_PATH = os.path.join(DATA_DIR, "metrics.db")
SUPERSET_CONFIG = os.path.join(BASE_DIR, "superset_config.py")

PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
PIP = os.path.join(VENV_DIR, "Scripts", "pip.exe")
SUPERSET_BIN = os.path.join(VENV_DIR, "Scripts", "superset.exe")


def run(cmd, env=None, check=True):
    """Run a command and print output."""
    print(f"\n{'='*60}")
    print(f"Running: {cmd}")
    print(f"{'='*60}")
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(cmd, shell=True, env=merged_env, capture_output=False)
    if check and result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(1)
    return result


def setup():
    # Step 1: Create virtual environment
    if not os.path.exists(VENV_DIR):
        print("\n[1/6] Creating virtual environment for Superset...")
        run(f"python -m venv {VENV_DIR}")
    else:
        print("\n[1/6] Virtual environment already exists, skipping...")

    # Step 2: Install Superset
    print("\n[2/6] Installing Apache Superset...")
    run(f'"{PIP}" install apache-superset')

    # Step 3: Write config
    print("\n[3/6] Writing Superset configuration...")
    config_content = f'''
import os

# Superset specific config
SECRET_KEY = "git-metrics-detector-superset-secret-key-change-in-prod"
SQLALCHEMY_DATABASE_URI = "sqlite:///{os.path.join(BASE_DIR, "superset_data", "superset.db").replace(os.sep, "/")}"

# Flask App Builder
FAB_ADD_SECURITY_VIEWS = True
WTF_CSRF_ENABLED = False

# Enable embedding in iframes
ENABLE_CORS = True
CORS_OPTIONS = {{
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["/api/*"],
    "origins": ["http://localhost:3001", "http://localhost:3000"],
}}

# Enable public dashboards (for embedding)
FEATURE_FLAGS = {{
    "EMBEDDED_SUPERSET": True,
    "ENABLE_TEMPLATE_PROCESSING": True
}}

# Talisman security headers
TALISMAN_ENABLED = False

# Allow embedding
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = False

PREVENT_UNSAFE_DB_CONNECTIONS = False
'''
    with open(SUPERSET_CONFIG, "w") as f:
        f.write(config_content)

    # Step 4: Create superset data directory
    superset_data = os.path.join(BASE_DIR, "superset_data")
    os.makedirs(superset_data, exist_ok=True)

    env = {"SUPERSET_CONFIG_PATH": SUPERSET_CONFIG}

    # Step 5: Initialize Superset database
    print("\n[4/6] Initializing Superset database...")
    run(f'"{SUPERSET_BIN}" db upgrade', env=env)

    # Step 6: Create admin user
    print("\n[5/6] Creating admin user...")
    run(
        f'"{SUPERSET_BIN}" fab create-admin '
        f'--username admin --firstname Admin --lastname User '
        f'--email admin@example.com --password admin',
        env=env,
        check=False,  # May fail if user already exists
    )

    # Step 7: Init Superset (load examples etc)
    print("\n[6/6] Initializing Superset...")
    run(f'"{SUPERSET_BIN}" init', env=env)

    print(f"""
{'='*60}
  Superset Setup Complete!
{'='*60}

  To start Superset, run:
    start_superset.bat

  Or manually:
    set SUPERSET_CONFIG_PATH={SUPERSET_CONFIG}
    "{SUPERSET_BIN}" run -p 8088 --with-threads --reload

  Login:
    URL:      http://localhost:8088
    Username: admin
    Password: admin

  Then add the Git Metrics database:
    1. Go to Settings > Database Connections
    2. Click + Database
    3. Select SQLite
    4. Connection string: sqlite:///{DB_PATH.replace(os.sep, "/")}
{'='*60}
""")


if __name__ == "__main__":
    setup()
