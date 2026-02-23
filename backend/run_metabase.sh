#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "metabase.jar" ]; then
  echo "ERROR: backend/metabase.jar not found."
  echo "Download it first:"
  echo "  curl -L \"https://downloads.metabase.com/latest/metabase.jar\" -o backend/metabase.jar"
  exit 1
fi

JAVA_BIN="java"
for d in "$SCRIPT_DIR"/jdk-*; do
  if [ -x "$d/bin/java" ]; then
    JAVA_BIN="$d/bin/java"
    break
  fi
done

if ! command -v "$JAVA_BIN" >/dev/null 2>&1; then
  echo "ERROR: java not found."
  echo "Install Java 21+ or unpack a portable JDK under backend/jdk-* (so backend/jdk-*/bin/java exists)."
  exit 1
fi

java_version="$("$JAVA_BIN" -version 2>&1 | head -n 1)"
major=""
if [[ "$java_version" =~ \"([0-9]+)\. ]]; then
  major="${BASH_REMATCH[1]}"
elif [[ "$java_version" =~ \"([0-9]+) ]]; then
  major="${BASH_REMATCH[1]}"
fi

if [ -z "$major" ] || [ "$major" -lt 21 ]; then
  echo "ERROR: Metabase requires Java 21+."
  echo "Detected: $java_version"
  echo "Fix:"
  echo "  - Install Java 21+, OR"
  echo "  - Unpack a portable JDK under backend/jdk-* (backend/jdk-*/bin/java)."
  exit 1
fi

export MB_JETTY_PORT="${MB_JETTY_PORT:-3003}"
echo "Starting Metabase on http://localhost:${MB_JETTY_PORT} using: $JAVA_BIN"
exec "$JAVA_BIN" -jar metabase.jar

