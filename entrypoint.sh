#!/bin/bash
set -e

echo "🚀 Starting Hospital Voice Agent..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if python -c "
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check_db():
    engine = create_async_engine('${DATABASE_URL}', echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        return True
    except:
        return False

if asyncio.run(check_db()):
    sys.exit(0)
else:
    sys.exit(1)
" 2>/dev/null; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ PostgreSQL did not become ready in time"
        exit 1
    fi
    
    echo "   Attempt $attempt/$max_attempts..."
    sleep 1
    attempt=$((attempt + 1))
done

# Create database tables
echo "📦 Initializing database..."
python -c "
import asyncio
from app.database import Base, engine

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✅ Database tables created/verified')

asyncio.run(init_db())
"

# Seed the database with hospital data
echo "🌱 Seeding database with hospital data..."
python -m scripts.seed

echo "✨ Setup complete! Starting application..."
exec "$@"
