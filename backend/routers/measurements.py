from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import BodyMeasurement

router = APIRouter(prefix="/api/measurements", tags=["measurements"])

USER_ID = 1


class MeasurementCreate(BaseModel):
    date: str
    body_weight: Optional[float] = None
    body_fat_pct: Optional[float] = None
    waist_in: Optional[float] = None
    chest_in: Optional[float] = None
    hips_in: Optional[float] = None
    left_arm_in: Optional[float] = None
    right_arm_in: Optional[float] = None
    left_quad_in: Optional[float] = None
    right_quad_in: Optional[float] = None
    notes: str = ""


class MeasurementUpdate(BaseModel):
    date: Optional[str] = None
    body_weight: Optional[float] = None
    body_fat_pct: Optional[float] = None
    waist_in: Optional[float] = None
    chest_in: Optional[float] = None
    hips_in: Optional[float] = None
    left_arm_in: Optional[float] = None
    right_arm_in: Optional[float] = None
    left_quad_in: Optional[float] = None
    right_quad_in: Optional[float] = None
    notes: Optional[str] = None


def _serialize(m: BodyMeasurement) -> dict:
    return {
        "id": m.id,
        "date": m.date,
        "body_weight": m.body_weight,
        "body_fat_pct": m.body_fat_pct,
        "waist_in": m.waist_in,
        "chest_in": m.chest_in,
        "hips_in": m.hips_in,
        "left_arm_in": m.left_arm_in,
        "right_arm_in": m.right_arm_in,
        "left_quad_in": m.left_quad_in,
        "right_quad_in": m.right_quad_in,
        "notes": m.notes,
    }


@router.get("")
def list_measurements(session: Session = Depends(get_session)):
    stmt = (
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == USER_ID)
        .order_by(BodyMeasurement.date.desc())
    )
    return [_serialize(m) for m in session.exec(stmt).all()]


@router.get("/latest")
def latest_measurement(session: Session = Depends(get_session)):
    stmt = (
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == USER_ID)
        .order_by(BodyMeasurement.date.desc())
    )
    m = session.exec(stmt).first()
    return _serialize(m) if m else None


@router.post("")
def create_measurement(payload: MeasurementCreate, session: Session = Depends(get_session)):
    m = BodyMeasurement(
        user_id=USER_ID,
        date=payload.date,
        body_weight=payload.body_weight,
        body_fat_pct=payload.body_fat_pct,
        waist_in=payload.waist_in,
        chest_in=payload.chest_in,
        hips_in=payload.hips_in,
        left_arm_in=payload.left_arm_in,
        right_arm_in=payload.right_arm_in,
        left_quad_in=payload.left_quad_in,
        right_quad_in=payload.right_quad_in,
        notes=payload.notes,
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return _serialize(m)


@router.put("/{measurement_id}")
def update_measurement(
    measurement_id: int,
    payload: MeasurementUpdate,
    session: Session = Depends(get_session),
):
    m = session.get(BodyMeasurement, measurement_id)
    if not m or m.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Measurement not found")

    for field in ["date", "body_weight", "body_fat_pct", "waist_in", "chest_in",
                  "hips_in", "left_arm_in", "right_arm_in", "left_quad_in", "right_quad_in", "notes"]:
        val = getattr(payload, field)
        if val is not None:
            setattr(m, field, val)

    session.add(m)
    session.commit()
    session.refresh(m)
    return _serialize(m)


@router.delete("/{measurement_id}")
def delete_measurement(measurement_id: int, session: Session = Depends(get_session)):
    m = session.get(BodyMeasurement, measurement_id)
    if not m or m.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Measurement not found")
    session.delete(m)
    session.commit()
    return {"ok": True}
