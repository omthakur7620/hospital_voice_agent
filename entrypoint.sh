#!/bin/bash
set -e

echo "[STARTUP] Starting Hospital Voice Agent..."

# Force install asyncpg first
echo "[STARTUP] Ensuring asyncpg is installed..."
pip install asyncpg==0.31.0 --force-reinstall --no-deps

# Then install the rest
echo "[STARTUP] Installing dependencies..."
pip install -r requirements.txt

# Wait for PostgreSQL
echo "[STARTUP] Waiting for PostgreSQL connection..."
max_attempts=10
attempt=1
db_ready=false

while [ $attempt -le $max_attempts ]; do
    if python -c "
import asyncio
from app.database import check_db_connection
try:
    result = asyncio.run(check_db_connection())
    exit(0 if result else 1)
except Exception as e:
    print(f'DB check error: {e}')
    exit(1)
" 2>&1; then
        db_ready=true
        echo "[STARTUP] Database connection verified"
        break
    fi
    
    sleep 1
    attempt=$((attempt + 1))
done

if [ "$db_ready" = false ]; then
    echo "[STARTUP] Warning: Database not ready yet. App will retry on startup."
fi

echo "[STARTUP] Ready to start application"
exec "$@"