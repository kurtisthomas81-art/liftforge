import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import UserProfile, UserEquipment, Exercise, PersonalRecord, BodyMeasurement
from typing import Optional

router = APIRouter(prefix="/api/profile", tags=["profile"])

USER_ID = 1

# ── Strength grader ────────────────────────────────────────────────────────────

_THRESHOLDS = {
    "squat":    {"male":   [(0, 1.25), (1.25, 1.75), (1.75, 2.25), (2.25, 999)],
                 "female": [(0, 0.75), (0.75, 1.2),  (1.2,  1.6),  (1.6,  999)]},
    "bench":    {"male":   [(0, 1.0),  (1.0,  1.35), (1.35, 1.75), (1.75, 999)],
                 "female": [(0, 0.6),  (0.6,  0.9),  (0.9,  1.2),  (1.2,  999)]},
    "deadlift": {"male":   [(0, 1.5),  (1.5,  2.0),  (2.0,  2.5),  (2.5,  999)],
                 "female": [(0, 0.9),  (0.9,  1.4),  (1.4,  1.9),  (1.9,  999)]},
    "ohp":      {"male":   [(0, 0.65), (0.65, 0.85), (0.85, 1.1),  (1.1,  999)],
                 "female": [(0, 0.35), (0.35, 0.55), (0.55, 0.75), (0.75, 999)]},
}
_LEVEL_NAMES = ["beginner", "intermediate", "advanced", "elite"]
_LEVEL_ORDER = {n: i for i, n in enumerate(_LEVEL_NAMES)}
_BIG4 = [
    ("squat",    "Barbell Back Squat"),
    ("bench",    "Barbell Bench Press"),
    ("deadlift", "Conventional Deadlift"),
    ("ohp",      "Barbell Overhead Press"),
]


def _classify(lift_key: str, ratio: float, sex: str):
    s = "female" if sex == "female" else "male"
    bands = _THRESHOLDS[lift_key][s]
    for i, (lo, hi) in enumerate(bands):
        if ratio < hi or i == len(bands) - 1:
            return _LEVEL_NAMES[i], lo, hi
    return "elite", bands[-1][0], 999.0


def grade_strength_level(session: Session) -> dict:
    """Compute strength level and update experience_level on UserProfile."""
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == USER_ID)).first()
    sex = (profile.sex or "male").lower() if profile else "male"

    bm = session.exec(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == USER_ID, BodyMeasurement.body_weight != None)
        .order_by(BodyMeasurement.date.desc())
    ).first()
    body_weight = bm.body_weight if bm else None

    lifts = []
    for lift_key, canonical_name in _BIG4:
        ex = session.exec(select(Exercise).where(Exercise.name == canonical_name)).first()
        e1rm = None
        if ex:
            best = session.exec(
                select(PersonalRecord)
                .where(PersonalRecord.user_id == USER_ID,
                       PersonalRecord.exercise_id == ex.id,
                       PersonalRecord.pr_type == "e1rm")
                .order_by(PersonalRecord.value.desc())
            ).first()
            e1rm = best.value if best else None

        ratio = level = next_threshold = None
        pct_to_next = 0

        if e1rm is not None and body_weight and body_weight > 0:
            ratio = round(e1rm / body_weight, 3)
            lv, lo, hi = _classify(lift_key, ratio, sex)
            level = lv
            if lv != "elite":
                next_threshold = hi
                pct_to_next = min(100, round((ratio - lo) / (hi - lo) * 100))
            else:
                pct_to_next = 100

        lifts.append({
            "lift_key": lift_key,
            "exercise_name": canonical_name,
            "e1rm": round(e1rm, 1) if e1rm is not None else None,
            "ratio": ratio,
            "level": level,
            "next_threshold": next_threshold,
            "pct_to_next": pct_to_next,
        })

    leveled = [l for l in lifts if l["level"] is not None]
    overall_level = None
    if leveled:
        overall_level = min(leveled, key=lambda l: _LEVEL_ORDER[l["level"]])["level"]
        if profile and profile.experience_level != overall_level:
            profile.experience_level = overall_level
            session.add(profile)
            session.commit()

    return {
        "overall_level": overall_level,
        "has_body_weight": body_weight is not None,
        "body_weight": body_weight,
        "lifts": lifts,
    }


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    unit_preference: Optional[str] = None
    sex: Optional[str] = None
    experience_level: Optional[str] = None
    default_rest_seconds: Optional[int] = None
    preferred_session_minutes: Optional[int] = None
    plate_inventory: Optional[dict] = None


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
        "plate_inventory": json.loads(p.plate_inventory or "{}"),
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
    if payload.plate_inventory is not None:
        profile.plate_inventory = json.dumps(payload.plate_inventory)
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


@router.get("/strength-level")
def get_strength_level(session: Session = Depends(get_session)):
    return grade_strength_level(session)
