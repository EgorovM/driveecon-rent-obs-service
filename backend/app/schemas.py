import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, model_validator


class PropertyStatus(str, Enum):
    free = "free"
    listed_ykt = "listed_ykt"
    occupied = "occupied"


class PeriodStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"


class PropertyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    status: PropertyStatus = PropertyStatus.free
    owner_email: EmailStr


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    status: PropertyStatus | None = None
    owner_email: EmailStr | None = None


class PropertyOut(PropertyBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaseBase(BaseModel):
    tenant_name: str = Field(..., min_length=1)
    tenant_email: EmailStr
    rent_start: date
    rent_end: date
    rent_amount: int = Field(..., gt=0, description="Сумма аренды в месяц, рубли")
    payment_day: int = Field(..., ge=1, le=31, description="Расчётный день месяца (до какого числа платить)")
    contract_number: str | None = None
    contract_date: date | None = None


class LeaseCreate(LeaseBase):
    @model_validator(mode="after")
    def end_after_start(self):
        if self.rent_end < self.rent_start:
            raise ValueError("Дата окончания раньше даты начала")
        return self


class LeaseUpdate(BaseModel):
    tenant_name: str | None = Field(None, min_length=1)
    tenant_email: EmailStr | None = None
    rent_amount: int | None = Field(None, gt=0)
    payment_day: int | None = Field(None, ge=1, le=31)
    terminated_at: date | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if all(
            getattr(self, f) is None
            for f in ("tenant_name", "tenant_email", "rent_amount", "payment_day", "terminated_at")
        ):
            raise ValueError("Укажите хотя бы одно поле для изменения")
        return self


class RentPeriodOut(BaseModel):
    id: uuid.UUID
    lease_id: uuid.UUID
    year: int
    month: int
    due_date: date
    amount_due: int
    amount_paid: int
    status: PeriodStatus
    reminder_3d_sent_at: datetime | None
    overdue_notice_sent_at: datetime | None
    paid_at: datetime | None

    model_config = {"from_attributes": True}


class LeaseOut(LeaseBase):
    id: uuid.UUID
    property_id: uuid.UUID
    terminated_at: date | None
    created_at: datetime
    periods: list[RentPeriodOut] = []

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Сумма поступления, рубли")
    paid_on: date | None = None
    note: str | None = None


class ConfirmOut(BaseModel):
    period_id: uuid.UUID
    property_name: str
    address: str
    tenant_name: str
    year: int
    month: int
    due_date: date
    amount_due: int
    amount_paid: int
    status: PeriodStatus


class ConfirmBody(BaseModel):
    confirmation_text: str = Field(..., min_length=3, description="Краткий текст подтверждения оплаты")


class EmailTestBody(BaseModel):
    """Если указан period_id, to_email можно не передавать — подставится email из аренды / владельца."""

    to_email: EmailStr | None = None
    period_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def require_to_when_no_period(self):
        if self.period_id is None and self.to_email is None:
            raise ValueError("Укажите to_email или period_id")
        return self


class MessageOut(BaseModel):
    ok: bool = True
    detail: str = ""
