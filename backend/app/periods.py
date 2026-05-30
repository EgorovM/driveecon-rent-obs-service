import calendar
import secrets
from datetime import date

from sqlalchemy.orm import Session

from app.models import Lease, PeriodStatus, RentPeriod

# На сколько месяцев вперёд заранее создаём начисления (чтобы напоминание за 3 дня успело сработать).
LOOKAHEAD_MONTHS = 1


def due_date_for(year: int, month: int, payment_day: int) -> date:
    """День платежа в конкретном месяце; если в месяце нет такого числа — последний день."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(payment_day, last_day))


def _add_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def recompute_status(period: RentPeriod) -> None:
    """Пересчитывает статус начисления по факту оплаты."""
    if period.amount_paid >= period.amount_due:
        period.status = PeriodStatus.paid.value
        return
    if period.status == PeriodStatus.paid.value:
        # Откатили оплату — больше не оплачено.
        period.status = PeriodStatus.pending.value


def ensure_periods_for_lease(db: Session, lease: Lease, today: date | None = None) -> int:
    """Создаёт недостающие месячные начисления по аренде от rent_start до today+LOOKAHEAD.

    Идемпотентна: существующие периоды не трогает. Возвращает число созданных.
    Для расторгнутых договоров новые периоды после terminated_at не создаются.
    """
    today = today or date.today()
    existing = {(p.year, p.month) for p in lease.periods}

    # Граница «вперёд»: текущий месяц + LOOKAHEAD_MONTHS.
    boundary_y, boundary_m = today.year, today.month
    for _ in range(LOOKAHEAD_MONTHS):
        boundary_y, boundary_m = _add_month(boundary_y, boundary_m)

    # Последний месяц действия договора (окончание или досрочное расторжение).
    cutoff_end = lease.terminated_at or lease.rent_end
    end_y, end_m = cutoff_end.year, cutoff_end.month

    # Создаём начисления вплоть до min(граница вперёд, конец договора).
    last_y, last_m = min((boundary_y, boundary_m), (end_y, end_m))

    y, m = lease.rent_start.year, lease.rent_start.month
    created = 0
    while (y, m) <= (last_y, last_m):
        if (y, m) not in existing:
            db.add(
                RentPeriod(
                    lease_id=lease.id,
                    year=y,
                    month=m,
                    due_date=due_date_for(y, m, lease.payment_day),
                    amount_due=lease.rent_amount,
                    amount_paid=0,
                    status=PeriodStatus.pending.value,
                    confirmation_token=secrets.token_urlsafe(32),
                )
            )
            created += 1
        y, m = _add_month(y, m)
    return created
