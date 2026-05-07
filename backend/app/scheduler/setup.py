from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from app.core.config import settings

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Return the global scheduler instance. Must call init_scheduler first."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized")
    return _scheduler


def init_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance with SQLite job store."""
    global _scheduler

    jobstores = {
        "default": SQLAlchemyJobStore(url=settings.scheduler_jobstore_url)
    }

    _scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        job_defaults={
            "coalesce": True,       # Run once if multiple executions were missed
            "max_instances": 1,     # Never run the same job twice simultaneously
            "misfire_grace_time": 60,
        },
    )
    return _scheduler