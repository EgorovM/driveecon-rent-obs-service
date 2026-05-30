import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PropertyStatus(str, enum.Enum):
    free = "free"
    listed_ykt = "listed_ykt"
    occupied = "occupied"


class PeriodStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=PropertyStatus.free.value)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    leases: Mapped[list["Lease"]] = relationship(
        "Lease", back_populates="property", cascade="all, delete-orphan"
    )


class Lease(Base):
    __tablename__ = "leases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_email: Mapped[str] = mapped_column(String(255), nullable=False)
    rent_start: Mapped[date] = mapped_column(Date, nullable=False)
    rent_end: Mapped[date] = mapped_column(Date, nullable=False)
    # Сумма аренды в месяц, рубли.
    rent_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    # Расчётный день месяца (1..31): до этого числа арендатор платит.
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contract_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Договор расторгнут / завершён — по таким арендам начисления больше не создаются.
    terminated_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    property: Mapped["Property"] = relationship("Property", back_populates="leases")
    periods: Mapped[list["RentPeriod"]] = relationship(
        "RentPeriod",
        back_populates="lease",
        cascade="all, delete-orphan",
        order_by="RentPeriod.due_date",
    )


class RentPeriod(Base):
    """Ежемесячное начисление аренды (период оплаты за конкретный месяц)."""

    __tablename__ = "rent_periods"
    __table_args__ = (UniqueConstraint("lease_id", "year", "month", name="uq_period_lease_month"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lease_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("leases.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_due: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_paid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=PeriodStatus.pending.value)
    confirmation_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    reminder_3d_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    overdue_notice_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lease: Mapped["Lease"] = relationship("Lease", back_populates="periods")
