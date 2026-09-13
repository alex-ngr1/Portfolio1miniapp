from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import SessionLocal, engine
from app.models import Base
from app.routers import auth, goals, tasks, uploads
from app.seed import seed_demo


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    if not settings.skip_seed:
        db = SessionLocal()
        try:
            seed_demo(db)
        finally:
            db.close()
    yield


app = FastAPI(title="Цільник", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(goals.router)
app.include_router(tasks.router)
app.include_router(uploads.router)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}
