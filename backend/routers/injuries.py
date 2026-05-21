import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from database import get_session
from models import Injury, Exercise

router = APIRouter(prefix="/api/injuries", tags=["injuries"])
USER_ID = 1

# Body part → muscles that are stressed
BODY_PART_MUSCLES: dict[str, list[str]] = {
    "shoulder":   ["shoulders", "chest", "triceps", "lats"],
    "elbow":      ["biceps", "triceps"],
    "wrist":      ["biceps", "triceps", "chest", "forearms"],
    "lower_back": ["back", "glutes", "hamstrings"],
    "upper_back": ["back", "lats", "traps"],
    "hip":        ["glutes", "hamstrings", "quads"],
    "knee":       ["quads", "hamstrings", "calves", "glutes"],
    "ankle":      ["calves"],
    "neck":       ["traps"],
}


class InjuryCreate(BaseModel):
    body_part: str
    severity: str = "mild"
    notes: str = ""


@router.get("")
def list_injuries(session: Session = Depends(get_session)):
    stmt = select(Injury).where(Injury.user_id == USER_ID, Injury.is_active == True)
    return [
        {"id": i.id, "body_part": i.body_part, "severity": i.severity, "notes": i.notes}
        for i in session.exec(stmt).all()
    ]


@router.post("")
def create_injury(payload: InjuryCreate, session: Session = Depends(get_session)):
    if payload.body_part not in BODY_PART_MUSCLES:
        raise HTTPException(status_code=400, detail="Unknown body part")
    # Deactivate existing entry for this body part before creating new one
    existing = session.exec(
        select(Injury).where(
            Injury.user_id == USER_ID,
            Injury.body_part == payload.body_part,
            Injury.is_active == True,
        )
    ).all()
    for e in existing:
        e.is_active = False
        session.add(e)
    inj = Injury(user_id=USER_ID, body_part=payload.body_part, severity=payload.severity, notes=payload.notes)
    session.add(inj)
    session.commit()
    session.refresh(inj)
    return {"id": inj.id, "body_part": inj.body_part, "severity": inj.severity, "notes": inj.notes}


@router.delete("/{injury_id}")
def delete_injury(injury_id: int, session: Session = Depends(get_session)):
    inj = session.get(Injury, injury_id)
    if not inj or inj.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Not found")
    inj.is_active = False
    session.add(inj)
    session.commit()
    return {"ok": True}


@router.get("/affected-exercises")
def affected_exercises(session: Session = Depends(get_session)):
    """Return {exercise_id: [body_parts]} for all active injuries."""
    active = session.exec(
        select(Injury).where(Injury.user_id == USER_ID, Injury.is_active == True)
    ).all()
    if not active:
        return {}

    affected_muscles: set[str] = set()
    part_by_muscle: dict[str, list[str]] = {}
    for inj in active:
        for m in BODY_PART_MUSCLES.get(inj.body_part, []):
            affected_muscles.add(m)
            part_by_muscle.setdefault(m, []).append(inj.body_part)

    result: dict[int, list[str]] = {}
    all_exercises = session.exec(select(Exercise)).all()
    for ex in all_exercises:
        try:
            pm = json.loads(ex.primary_muscles)
        except (json.JSONDecodeError, TypeError):
            pm = []
        try:
            sm = json.loads(ex.secondary_muscles)
        except (json.JSONDecodeError, TypeError):
            sm = []
        hit_parts: list[str] = []
        for m in pm + sm:
            if m in affected_muscles:
                for part in part_by_muscle.get(m, []):
                    if part not in hit_parts:
                        hit_parts.append(part)
        if hit_parts:
            result[ex.id] = hit_parts

    return result
