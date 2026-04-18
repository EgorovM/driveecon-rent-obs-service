from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.jobs import run_overdue_job, run_reminder_3d_job
from app.routers import confirm, email_test, leases, properties


def _run_scheduled_jobs() -> None:
    db = SessionLocal()
    try:
        run_reminder_3d_job(db)
        run_overdue_job(db)
    except Exception as exc:
        print(f"[scheduler] error: {exc}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler = BackgroundScheduler(timezone=ZoneInfo("Europe/Moscow"))
    scheduler.add_job(_run_scheduled_jobs, "cron", hour=9, minute=0)
    scheduler.add_job(_run_scheduled_jobs, "interval", hours=6, id="interval_fallback")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Drivee — мониторинг аренды", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url.rstrip("/"),
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:80",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(properties.router)
app.include_router(leases.router)
app.include_router(confirm.router)
app.include_router(email_test.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/jobs/run-now")
def run_jobs_now():
    """Ручной запуск проверок (напоминание за 3 дня и просрочка)."""
    db = SessionLocal()
    try:
        r1 = run_reminder_3d_job(db)
        r2 = run_overdue_job(db)
        return {"reminders_sent": r1, "overdue_notices_sent": r2}
    finally:
        db.close()
