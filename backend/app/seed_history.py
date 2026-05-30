"""Историческое наполнение БД за 2024–2026 по форме контроля аренды заказчика.

Создаёт по каждому объекту арендаторов (договоры) с помесячными начислениями:
прошлые месяцы отмечаются оплаченными, отдельные — как долг/просрочка/частичная
оплата (по реальным пометкам в таблице: «съехал», «нет оплаты», «расторжение»).

ВАЖНО: на всех созданных начислениях проставляются reminder_3d_sent_at и
overdue_notice_sent_at = now, чтобы запущенный планировщик НЕ слал письма на
демонстрационные адреса (@example.com — реальных email в таблице нет).

Запуск вручную:  python -m app.seed_history
Авто-запуск при пустой БД управляется настройкой SEED_HISTORY (см. config).
Идемпотентна: к объекту, у которого уже есть договоры, ничего не добавляет.
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from app.config import settings
from app.database import SessionLocal
from app.models import Lease, PeriodStatus, Property, PropertyStatus, RentPeriod
from app.periods import ensure_periods_for_lease
from app.seed import seed_demo_objects

# Дата «сегодня» для разметки истории (демо-портфель привязан к маю 2026).
TODAY = date(2026, 5, 30)


@dataclass
class LeaseSpec:
    tenant_name: str
    tenant_email: str
    rent_start: date
    rent_end: date
    rent_amount: int
    payment_day: int
    contract_number: str | None = None
    contract_date: date | None = None
    terminated_at: date | None = None
    # (год, месяц) начислений, оставшихся неоплаченными (долг/просрочка).
    unpaid: set[tuple[int, int]] = field(default_factory=set)
    # (год, месяц) -> частично внесённая сумма.
    partial: dict[tuple[int, int], int] = field(default_factory=dict)


# Портфель: имя объекта (как в app.seed.DEMO_PROPERTIES) -> список договоров.
HISTORY: dict[str, list[LeaseSpec]] = {
    "Кирова, 1 этаж — 256,3 кв.м": [
        LeaseSpec(
            "ИП Ли Сергей", "li.sergey@example.com",
            date(2024, 1, 1), date(2025, 8, 6), 384450, 5,
            terminated_at=date(2025, 8, 6),
            unpaid={(2025, 7), (2025, 8)},  # съехал с долгом
        ),
        LeaseSpec(
            "ИП Филиппов Р.В.", "filippov@example.com",
            date(2025, 8, 7), date(2025, 9, 30), 385000, 6,
            contract_date=date(2025, 8, 6), terminated_at=date(2025, 9, 30),
        ),
        LeaseSpec(
            "ИП Ханхалеев", "hanhaleev@example.com",
            date(2025, 10, 1), date(2026, 12, 31), 385000, 6,
            contract_date=date(2025, 10, 1),
        ),
    ],
    "Кирова, 2 этаж — 271 кв.м": [
        LeaseSpec(
            "ИП Антонова Лина", "antonova@example.com",
            date(2024, 1, 1), date(2026, 12, 31), 379400, 29,
            contract_date=date(2023, 5, 29),
        ),
    ],
    "Кирова, 3 этаж — 280 кв.м": [
        LeaseSpec(
            "ИП Никулин А.", "nikulin@example.com",
            date(2024, 1, 1), date(2025, 4, 30), 250000, 5,
            terminated_at=date(2025, 4, 30),
        ),
        LeaseSpec(
            "ИП Огоюкин Ф.Ф.", "ogoyukin@example.com",
            date(2025, 5, 1), date(2026, 12, 31), 250000, 5,
            contract_date=date(2025, 5, 1),
        ),
    ],
    "Пояркова 6п — 229,2 кв.м": [
        LeaseSpec(
            "ИП Захарова Г.С. (Скиф)", "zaharova@example.com",
            date(2025, 8, 16), date(2026, 7, 31), 440220, 1,
            contract_number="Б/Н", contract_date=date(2025, 8, 16),
        ),
    ],
    "Пояркова 7п — 17 кв.м": [
        LeaseSpec(
            "Ольга", "olga@example.com",
            date(2024, 1, 1), date(2025, 9, 12), 30000, 4,
            terminated_at=date(2025, 9, 12),
        ),
        LeaseSpec(
            "ИП Степанец Ю.В.", "stepanets@example.com",
            date(2025, 9, 13), date(2026, 2, 12), 35000, 20,
            contract_date=date(2025, 9, 13), terminated_at=date(2026, 2, 12),
        ),
        LeaseSpec(
            "ИП Корнилов Д.И.", "kornilov@example.com",
            date(2026, 2, 17), date(2026, 3, 19), 35000, 17,
            contract_date=date(2026, 2, 17), terminated_at=date(2026, 3, 19),  # съехал
        ),
    ],
    "Б.М., 1 этаж": [
        LeaseSpec(
            "ИП Четвергова Т.Н.", "chetvergova@example.com",
            date(2024, 4, 21), date(2026, 3, 1), 75377, 20,
            contract_date=date(2024, 4, 21), terminated_at=date(2026, 3, 1),  # расторжение
        ),
        LeaseSpec(
            "ИП Мочкин А.Н.", "mochkin@example.com",
            date(2026, 3, 1), date(2026, 12, 31), 75377, 20,
            contract_date=date(2026, 3, 1),
        ),
    ],
    "Б.М., 2 этаж": [
        LeaseSpec(
            "ИП Синькинеев Е.М.", "sinkineev@example.com",
            date(2024, 4, 21), date(2026, 12, 31), 27597, 20,
            contract_date=date(2024, 4, 21),
        ),
    ],
    "Б.М., между этажами": [
        LeaseSpec(
            "ИП Кудинов И.А.", "kudinov@example.com",
            date(2024, 4, 21), date(2026, 12, 31), 17410, 20,
            contract_date=date(2024, 4, 21),
            unpaid={(2026, 5)},  # текущий долг
        ),
    ],
    "Б.М., 1 этаж — 167,3 кв.м": [
        LeaseSpec(
            "ООО Альбион", "albion@example.com",
            date(2024, 1, 1), date(2026, 12, 31), 167300, 20,
            contract_date=date(2022, 12, 21),
            partial={(2026, 5): 100000},  # частичная оплата мая
        ),
    ],
    "Грозовая, 1 — 771,8 кв.м": [
        LeaseSpec(
            "ИП Петров Н.Н.", "petrov@example.com",
            date(2025, 10, 1), date(2026, 12, 31), 350000, 10,
            contract_date=date(2025, 10, 1),
        ),
    ],
    "Орджоникидзе, 44": [
        LeaseSpec(
            "Юра (маникюр)", "yura@example.com",
            date(2024, 1, 1), date(2024, 12, 31), 21000, 6,
            terminated_at=date(2024, 12, 31),
        ),
        LeaseSpec(
            "ИП Андреева Н.", "andreeva@example.com",
            date(2025, 1, 10), date(2026, 12, 31), 23000, 10,
            contract_date=date(2025, 1, 10),
        ),
    ],
}


def _apply_history(periods: list[RentPeriod], spec: LeaseSpec) -> None:
    """Размечает начисления договора: прошлое — оплачено/долг, настоящее/будущее — ждёт.

    Письма-уведомления гасятся (sent_at = now), чтобы планировщик не слал их на @example.com.
    """
    now = datetime.now()
    for p in periods:
        p.reminder_3d_sent_at = now
        p.overdue_notice_sent_at = now
        key = (p.year, p.month)
        if key in spec.partial:
            p.amount_paid = spec.partial[key]
            p.status = PeriodStatus.pending.value
        elif key in spec.unpaid:
            p.amount_paid = 0
            p.status = PeriodStatus.overdue.value if p.due_date < TODAY else PeriodStatus.pending.value
        elif p.due_date < TODAY:
            p.amount_paid = p.amount_due
            p.status = PeriodStatus.paid.value
            p.paid_at = datetime.combine(p.due_date, datetime.min.time())
        else:
            p.amount_paid = 0
            p.status = PeriodStatus.pending.value


def seed_history(db) -> dict[str, int]:
    """Наполняет БД историей за 2024–2026. Возвращает счётчики созданного."""
    seed_demo_objects(db)  # гарантируем наличие объектов
    props = {p.name: p for p in db.query(Property).all()}

    leases_created = 0
    periods_created = 0
    for prop_name, specs in HISTORY.items():
        prop = props.get(prop_name)
        if prop is None:
            print(f"[seed_history] объект не найден, пропуск: {prop_name}")
            continue
        if prop.leases:  # к объекту уже привязаны договоры — не дублируем
            continue

        active = False
        for spec in specs:
            lease = Lease(
                property_id=prop.id,
                tenant_name=spec.tenant_name,
                tenant_email=spec.tenant_email,
                rent_start=spec.rent_start,
                rent_end=spec.rent_end,
                rent_amount=spec.rent_amount,
                payment_day=spec.payment_day,
                contract_number=spec.contract_number,
                contract_date=spec.contract_date,
                terminated_at=spec.terminated_at,
            )
            db.add(lease)
            db.flush()
            periods_created += ensure_periods_for_lease(db, lease, today=TODAY)
            db.flush()
            periods = db.query(RentPeriod).filter(RentPeriod.lease_id == lease.id).all()
            _apply_history(periods, spec)
            if spec.terminated_at is None and spec.rent_end >= TODAY:
                active = True
            leases_created += 1

        prop.status = PropertyStatus.occupied.value if active else PropertyStatus.free.value

    db.commit()
    return {"leases": leases_created, "periods": periods_created}


if __name__ == "__main__":
    db = SessionLocal()
    try:
        res = seed_history(db)
        print(f"Создано договоров: {res['leases']}, начислений: {res['periods']}")
    finally:
        db.close()
