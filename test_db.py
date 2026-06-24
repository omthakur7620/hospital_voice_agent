import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:8477@localhost:5433/hospital_db"

engine = create_async_engine(DATABASE_URL)

async def test():
    async with engine.begin() as conn:
        print("Database Connected Successfully")

asyncio.run(test())