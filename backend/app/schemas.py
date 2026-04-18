import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, model_validator


class PropertyStatus(str, Enum):
    free = "free"
    listed_ykt = "listed_ykt"
    occupied = "occupied"


class PaymentStatus(str, Enum):
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


class LeaseCreate(LeaseBase):
    pass


class LeaseUpdate(BaseModel):
    tenant_name: str | None = Field(None, min_length=1)
    tenant_email: EmailStr | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.tenant_name is None and self.tenant_email is None:
            raise ValueError("Укажите tenant_name и/или tenant_email")
        return self


class LeaseOut(LeaseBase):
    id: uuid.UUID
    property_id: uuid.UUID
    payment_status: PaymentStatus
    reminder_3d_sent_at: datetime | None
    overdue_notice_sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfirmOut(BaseModel):
    lease_id: uuid.UUID
    property_name: str
    address: str
    tenant_name: str
    rent_end: date


class ConfirmBody(BaseModel):
    confirmation_text: str = Field(..., min_length=3, description="Краткий текст подтверждения оплаты")


class EmailTestBody(BaseModel):
    """Если указан lease_id, to_email можно не передавать — подставится email из аренды / владельца."""

    to_email: EmailStr | None = None
    lease_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def require_to_when_no_lease(self):
        if self.lease_id is None and self.to_email is None:
            raise ValueError("Укажите to_email или lease_id")
        return self


class MessageOut(BaseModel):
    ok: bool = True
    detail: str = ""
