#!/usr/bin/env sh
set -eu

if [ "${RUN_DB_BOOTSTRAP:-false}" = "true" ]; then
  python - <<'PY'
import os
import time
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
last_error = None
for attempt in range(60):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database is ready.")
        break
    except Exception as exc:
        last_error = exc
        time.sleep(2)
else:
    raise SystemExit(f"Database did not become ready: {last_error}")
PY

  alembic upgrade head
  python - <<'PY'
from app.database import init_db
init_db()
print("Database schema bootstrap completed.")
PY

  if [ "${SEED_DEVELOPMENT:-false}" = "true" ]; then
    python scripts/seed_development.py
  fi
fi

exec "$@"
