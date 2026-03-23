# arco Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-14

## Active Technologies
- Python 3.11 + Flask 3.0.0, SQLAlchemy 2.0.36, Flask-SQLAlchemy 3.1.1, Flask-SocketIO (WebSocket) (003-notification-core)
- SQLite (dev), PostgreSQL/MySQL (prod) (003-notification-core)
- Python 3.11 + Flask 3.0.0, Flask-SQLAlchemy 3.1.1, Flask-SocketIO 5.x, SQLAlchemy 2.0.36 (004-notification-module)
- SQLite (development), PostgreSQL/MySQL (production) (004-notification-module)
- SQLite (开发), PostgreSQL/MySQL (生产) (005-ci-relation-trigger)
- Python 3.11 + Flask 3.0.0, SQLAlchemy 2.0.36, Flask-SQLAlchemy 3.1.1, APScheduler 3.10 (005-ci-relation-trigger)

- Python 3.11 + Flask 3.0.0, SQLAlchemy 2.0.36, Flask-SQLAlchemy 3.1.1 (001-cmdb-model-relations)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11: Follow standard conventions

## Recent Changes
- 005-ci-relation-trigger: Added Python 3.11 + Flask 3.0.0, SQLAlchemy 2.0.36, Flask-SQLAlchemy 3.1.1, APScheduler 3.10
- 005-ci-relation-trigger: Added Python 3.11 + Flask 3.0.0, SQLAlchemy 2.0.36, Flask-SQLAlchemy 3.1.1, APScheduler 3.10
- 005-ci-relation-trigger: Added Python 3.11 + Flask 3.0.0, SQLAlchemy 2.0.36, Flask-SQLAlchemy 3.1.1


<!-- MANUAL ADDITIONS START -->
## Current Runtime Baseline (2026-03-23)

- Project root: `/Users/peter/Documents/arco`
- Backend path: `backend/`
- Frontend path: `frontend/`
- Metadata DB baseline: PostgreSQL 16 (`arco-postgres`) for development and deployment
- Recommended `DATABASE_URL`:
  - `postgresql+psycopg2://arco_user:arco_password@127.0.0.1:5432/arco_db`

## DB Initialization / Migration

- PostgreSQL bootstrap SQL: `init-scripts/00-init-postgres.sql`
- SQLite -> PostgreSQL migration script: `backend/scripts/migrate_sqlite_to_postgres.py`
- One-time bootstrap helper: `backend/scripts/init_postgres.sh`
- Migration artifacts (backup/report): `backend/migration_artifacts/`

## Known Migration Caveat

- Alembic chain was normalized on 2026-03-23 and duplicate revision id was removed.
- Preferred flow is now:
  1) `./backend/scripts/init_postgres.sh`
  2) `python3 -m flask db upgrade` (or `flask db upgrade`) for schema evolution
  3) `python3 backend/scripts/migrate_sqlite_to_postgres.py --sqlite backend/instance/it_ops.db` when migrating legacy SQLite data
- Additional caveat (2026-03-23):
  - `manager-go` runtime persistence is still SQLite-based (`backend/instance/it_ops.db`) and has not fully switched to PostgreSQL.
  - Any migration plan touching metadata/licensing must explicitly include `manager-go` store migration and DSN switch steps.
<!-- MANUAL ADDITIONS END -->
