from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_auth, router as auth_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.jobs import generate_due_periods, run_overdue_job, run_reminder_3d_job
from app.routers import confirm, email_test, leases, properties
from app.seed import seed_demo_objects
from app.seed_history import seed_history


def _run_scheduled_jobs() -> None:
    db = SessionLocal()
    try:
        generate_due_periods(db)
        run_reminder_3d_job(db)
        run_overdue_job(db)
    except Exception as exc:
        print(f"[scheduler] error: {exc}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_start:
        db = SessionLocal()
        try:
            if settings.seed_history:
                seed_history(db)
            else:
                seed_demo_objects(db)
        except Exception as exc:
            print(f"[seed] error: {exc}")
        finally:
            db.close()
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

# Публичные: вход и подтверждение оплаты арендатором по ссылке из письма.
app.include_router(auth_router)
app.include_router(confirm.router)
# Защищённые авторизацией (админка владельца).
app.include_router(properties.router, dependencies=[Depends(require_auth)])
app.include_router(leases.router, dependencies=[Depends(require_auth)])
app.include_router(email_test.router, dependencies=[Depends(require_auth)])


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/jobs/run-now", dependencies=[Depends(require_auth)])
def run_jobs_now():
    """Ручной запуск проверок (генерация начислений, напоминание за 3 дня, просрочка)."""
    db = SessionLocal()
    try:
        created = generate_due_periods(db)
        r1 = run_reminder_3d_job(db)
        r2 = run_overdue_job(db)
        return {"periods_created": created, "reminders_sent": r1, "overdue_notices_sent": r2}
    finally:
        db.close()
