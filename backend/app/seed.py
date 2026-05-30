"""Демо-данные: портфель объектов заказчика из листа «2026» формы контроля аренды.

Запуск вручную:  python -m app.seed
Авто-запуск при пустой БД управляется настройкой SEED_ON_START (см. config).
Арендаторы и их email не заполняются (их нет в исходной таблице) — заводятся в UI.
"""

from app.config import settings
from app.database import SessionLocal
from app.models import Property, PropertyStatus

# (название с площадью, адрес, статус)
DEMO_PROPERTIES: list[tuple[str, str, str]] = [
    ("Кирова, 1 этаж — 256,3 кв.м", "г. Якутск, ул. Кирова", PropertyStatus.occupied.value),
    ("Кирова, 2 этаж — 271 кв.м", "г. Якутск, ул. Кирова", PropertyStatus.occupied.value),
    ("Кирова, 3 этаж — 280 кв.м", "г. Якутск, ул. Кирова", PropertyStatus.occupied.value),
    ("Пояркова 6п — 229,2 кв.м", "г. Якутск, ул. Пояркова, д.20/1, 6 подъезд", PropertyStatus.occupied.value),
    ("Пояркова 7п — 17 кв.м", "г. Якутск, ул. Пояркова, д.20/1, 7 подъезд", PropertyStatus.free.value),
    ("Б.М., 1 этаж", "г. Якутск", PropertyStatus.occupied.value),
    ("Б.М., 2 этаж", "г. Якутск", PropertyStatus.occupied.value),
    ("Б.М., между этажами", "г. Якутск", PropertyStatus.occupied.value),
    ("Б.М., 1 этаж — 167,3 кв.м", "г. Якутск", PropertyStatus.occupied.value),
    ("Грозовая, 1 — 771,8 кв.м", "г. Якутск, ул. Грозовая, д.1", PropertyStatus.occupied.value),
    ("Орджоникидзе, 44", "г. Якутск, ул. Орджоникидзе, д.44", PropertyStatus.occupied.value),
]


def seed_demo_objects(db) -> int:
    """Создаёт демо-объекты, если в БД ещё нет ни одного объекта. Возвращает число созданных."""
    if db.query(Property).first() is not None:
        return 0
    for name, address, status in DEMO_PROPERTIES:
        db.add(
            Property(
                name=name,
                address=address,
                status=status,
                owner_email=settings.owner_email,
            )
        )
    db.commit()
    return len(DEMO_PROPERTIES)


if __name__ == "__main__":
    db = SessionLocal()
    try:
        n = seed_demo_objects(db)
        print(f"Создано объектов: {n}" if n else "Объекты уже есть — пропуск.")
    finally:
        db.close()
