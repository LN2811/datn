from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.main import api_router
from app.core.config import settings
from app.database import engine

uploads_dir = Path(__file__).resolve().parent / "storage"
uploads_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI()

if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")



@app.on_event("startup")
async def test_db():
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    print("PostgreSQL connected")
