#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   PGHOST=127.0.0.1 PGPORT=5432 PGUSER=postgres PGPASSWORD=xxx \
#   ./backend/scripts/init_postgres.sh

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
INIT_SQL="$ROOT_DIR/init-scripts/00-init-postgres.sql"

PGHOST="${PGHOST:-127.0.0.1}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-postgres}"

echo "[1/3] Apply init SQL (role/db/extension)"
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -f "$INIT_SQL"

echo "[2/3] Apply schema/default data via Flask app bootstrap"
DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://arco_user:arco_password@127.0.0.1:5432/arco_db}" \
ROOT_DIR="$ROOT_DIR" \
python3 - <<'PY'
import os
import sys
ROOT = os.environ["ROOT_DIR"]
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app import create_app  # noqa: E402

create_app("development")
print("Flask bootstrap completed.")
PY

echo "[3/3] Done."
