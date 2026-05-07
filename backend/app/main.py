from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.api import auth, workflows, integrations
from app.scheduler.setup import init_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init scheduler. Shutdown: stop scheduler."""
    scheduler = init_scheduler()
    scheduler.start()
    print("StackBridge API starting up — scheduler running")
    yield
    scheduler.shutdown()
    print("StackBridge API shutting down")


app = FastAPI(
    title="StackBridge API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workflows.router)
app.include_router(integrations.router)


@app.get("/health")
async def health_check():
    """Returns API and database status."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {"status": "ok", "db": db_status}