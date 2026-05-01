from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import UserProfile, UserEquipment
from typing import Optional

router = APIRouter(prefix="/api/profile", tags=["profile"])

USER_ID = 1


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    unit_preference: Optional[str] = None
    sex: Optional[str] = None
    experience_level: Optional[str] = None
    default_rest_seconds: Optional[int] = None
    preferred_session_minutes: Optional[int] = None


class EquipmentUpdate(BaseModel):
    equipment: list[str]


def _get_or_create_profile(session: Session) -> UserProfile:
    stmt = select(UserProfile).where(UserProfile.user_id == USER_ID)
    profile = session.exec(stmt).first()
    if not profile:
        profile = UserProfile(user_id=USER_ID)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def _serialize_profile(p: UserProfile) -> dict:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "display_name": p.display_name,
        "unit_preference": p.unit_preference,
        "sex": p.sex,
        "experience_level": p.experience_level,
        "default_rest_seconds": p.default_rest_seconds,
        "preferred_session_minutes": p.preferred_session_minutes,
    }


@router.get("")
def get_profile(session: Session = Depends(get_session)):
    profile = _get_or_create_profile(session)
    eq_stmt = select(UserEquipment).where(
        UserEquipment.user_id == USER_ID, UserEquipment.available == True
    )
    equipment = session.exec(eq_stmt).all()
    data = _serialize_profile(profile)
    data["equipment"] = [e.equipment for e in equipment]
    return data


@router.put("")
def update_profile(payload: ProfileUpdate, session: Session = Depends(get_session)):
    profile = _get_or_create_profile(session)
    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.unit_preference is not None:
        profile.unit_preference = payload.unit_preference
    if payload.sex is not None:
        profile.sex = payload.sex
    if payload.experience_level is not None:
        profile.experience_level = payload.experience_level
    if payload.default_rest_seconds is not None:
        profile.default_rest_seconds = payload.default_rest_seconds
    if payload.preferred_session_minutes is not None:
        profile.preferred_session_minutes = payload.preferred_session_minutes
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return _serialize_profile(profile)


@router.put("/equipment")
def update_equipment(payload: EquipmentUpdate, session: Session = Depends(get_session)):
    # Delete all existing equipment for user and replace
    old_stmt = select(UserEquipment).where(UserEquipment.user_id == USER_ID)
    old_equipment = session.exec(old_stmt).all()
    for e in old_equipment:
        session.delete(e)
    session.commit()

    for eq in payload.equipment:
        ue = UserEquipment(user_id=USER_ID, equipment=eq, available=True)
        session.add(ue)
    session.commit()

    return {"equipment": payload.equipment}
