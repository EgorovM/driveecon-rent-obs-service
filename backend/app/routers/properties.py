import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Property
from app.schemas import PropertyCreate, PropertyOut, PropertyUpdate

router = APIRouter(prefix="/api/properties", tags=["properties"])


@router.get("", response_model=list[PropertyOut])
def list_properties(db: Session = Depends(get_db)):
    return db.query(Property).order_by(Property.created_at.desc()).all()


@router.post("", response_model=PropertyOut)
def create_property(data: PropertyCreate, db: Session = Depends(get_db)):
    p = Property(
        name=data.name,
        address=data.address,
        status=data.status.value,
        owner_email=str(data.owner_email),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(property_id: uuid.UUID, db: Session = Depends(get_db)):
    p = db.query(Property).filter(Property.id == property_id).first()
    if not p:
        raise HTTPException(404, "Объект не найден")
    return p


@router.patch("/{property_id}", response_model=PropertyOut)
def update_property(property_id: uuid.UUID, data: PropertyUpdate, db: Session = Depends(get_db)):
    p = db.query(Property).filter(Property.id == property_id).first()
    if not p:
        raise HTTPException(404, "Объект не найден")
    if data.name is not None:
        p.name = data.name
    if data.address is not None:
        p.address = data.address
    if data.status is not None:
        p.status = data.status.value
    if data.owner_email is not None:
        p.owner_email = str(data.owner_email)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{property_id}")
def delete_property(property_id: uuid.UUID, db: Session = Depends(get_db)):
    p = db.query(Property).filter(Property.id == property_id).first()
    if not p:
        raise HTTPException(404, "Объект не найден")
    db.delete(p)
    db.commit()
    return {"ok": True}
