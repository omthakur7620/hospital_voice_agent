#!/bin/bash
# Production-optimized entrypoint script
# Works with Railway, Render, Railway, and other platforms
# Initializes database and starts the application without blocking health checks

set +e  # Don't exit on errors - let app handle gracefully

echo "[STARTUP] Starting Hospital Voice Agent..."

# Wait for PostgreSQL to be ready (non-blocking, short timeout)
echo "[STARTUP] Waiting for PostgreSQL connection..."
max_attempts=10
attempt=1
db_ready=false

while [ $attempt -le $max_attempts ]; do
    if python -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def check_db():
    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        await engine.dispose()
        return True
    except Exception as e:
        print(f'DB check error: {e}', flush=True)
        return False

try:
    if asyncio.run(check_db()):
        print('[STARTUP] PostgreSQL ready!', flush=True)
        exit(0)
    exit(1)
except Exception as e:
    print(f'Connection check failed: {e}', flush=True)
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

# Create database tables (non-blocking, errors don't stop startup)
echo "[STARTUP] Initializing database schema..."
python -c "
import asyncio
import sys
from app.database import Base, engine
from app.logger import get_logger

logger = get_logger(__name__)

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print('[STARTUP] Database tables initialized', flush=True)
        return True
    except Exception as e:
        print(f'[STARTUP] Warning: Database init error: {e}', flush=True)
        return False
    finally:
        try:
            await engine.dispose()
        except:
            pass

try:
    asyncio.run(init_db())
except Exception as e:
    print(f'[STARTUP] Error during init: {e}', flush=True)
" 2>&1 || echo "[STARTUP] Database initialization skipped/failed"

# Attempt data seed (completely optional, don't block on this)
echo "[STARTUP] Seeding hospital data (if needed)..."
timeout 30 python -m scripts.seed 2>&1 || echo "[STARTUP] Seed skipped or timed out"

echo "[STARTUP] Ready to start application"
exec "$@"