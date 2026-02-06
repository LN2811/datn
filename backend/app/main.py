from fastapi import FastAPI
from sqlalchemy import text

from app.database import engine

app = FastAPI()  # 👈 BẮT BUỘC

@app.on_event("startup")
async def test_db():
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    print("✅ PostgreSQL connected")
