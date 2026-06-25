#!/bin/bash
# Local development startup script for macOS/Linux

echo "========================================"
echo "Hospital Voice Agent - Local Development"
echo "========================================"
echo ""

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo ""
fi

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate
echo ""

# Install requirements
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo ""

# Initialize database
echo "Initializing database..."
python -c "
import asyncio
from app.database import Base, engine

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✓ Database tables created/verified')

asyncio.run(init_db())
"
echo ""

# Seed database
echo "Seeding database..."
python -m scripts.seed
echo ""

# Start application
echo "Starting application..."
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
