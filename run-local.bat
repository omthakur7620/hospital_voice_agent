@echo off
REM Local development startup script for Windows

echo ========================================
echo Hospital Voice Agent - Local Development
echo ========================================
echo.

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install requirements
echo Installing dependencies...
pip install -q -r requirements.txt
echo.

REM Initialize database
echo Initializing database...
python -c "
import asyncio
from app.database import Base, engine

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✓ Database tables created/verified')

asyncio.run(init_db())
"
echo.

REM Seed database
echo Seeding database...
python -m scripts.seed
echo.

REM Start application
echo Starting application...
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
