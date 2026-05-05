import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from database import get_session
from models import Exercise, WorkoutSet, WorkoutSession
from datetime import datetime

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


def _serialize(ex: Exercise) -> dict:
    return {
        "id": ex.id,
        "name": ex.name,
        "aliases": json.loads(ex.aliases),
        "movement_pattern": ex.movement_pattern,
        "sub_pattern": getattr(ex, "sub_pattern", "") or "",
        "primary_muscles": json.loads(ex.primary_muscles),
        "secondary_muscles": json.loads(ex.secondary_muscles),
        "equipment_required": json.loads(ex.equipment_required),
        "mechanics": ex.mechanics,
        "force": ex.force,
        "is_bilateral": ex.is_bilateral,
        "notes": ex.notes,
        "substitution_ids": json.loads(ex.substitution_ids),
        "is_custom": ex.is_custom,
    }


@router.get("")
def list_exercises(
    equipment: Optional[str] = Query(None),
    muscle: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sub_pattern: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    stmt = select(Exercise)
    exercises = session.exec(stmt).all()

    result = []
    for ex in exercises:
        primary = json.loads(ex.primary_muscles)
        secondary = json.loads(ex.secondary_muscles)
        equipment_req = json.loads(ex.equipment_required)
        aliases = json.loads(ex.aliases)

        if equipment and equipment not in equipment_req:
            continue
        if muscle and muscle not in primary and muscle not in secondary:
            continue
        if search:
            q = search.lower()
            name_match = q in ex.name.lower()
            alias_match = any(q in a.lower() for a in aliases)
            if not (name_match or alias_match):
                continue
        if sub_pattern and (getattr(ex, "sub_pattern", "") or "") != sub_pattern:
            continue

        result.append(_serialize(ex))

    return result


@router.get("/{exercise_id}")
def get_exercise(exercise_id: int, session: Session = Depends(get_session)):
    ex = session.get(Exercise, exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")

    data = _serialize(ex)
    # Resolve substitutions
    sub_ids = data["substitution_ids"]
    subs = []
    for sid in sub_ids:
        sub = session.get(Exercise, sid)
        if sub:
            subs.append({"id": sub.id, "name": sub.name})
    data["substitutions"] = subs
    return data


@router.post("")
def create_exercise(payload: dict, session: Session = Depends(get_session)):
    ex = Exercise(
        name=payload["name"],
        aliases=json.dumps(payload.get("aliases", [])),
        movement_pattern=payload.get("movement_pattern", ""),
        primary_muscles=json.dumps(payload.get("primary_muscles", [])),
        secondary_muscles=json.dumps(payload.get("secondary_muscles", [])),
        equipment_required=json.dumps(payload.get("equipment_required", [])),
        mechanics=payload.get("mechanics", "compound"),
        force=payload.get("force", "push"),
        is_bilateral=payload.get("is_bilateral", True),
        notes=payload.get("notes", ""),
        substitution_ids=json.dumps(payload.get("substitution_ids", [])),
        is_custom=True,
    )
    session.add(ex)
    session.commit()
    session.refresh(ex)
    return _serialize(ex)


@router.get("/{exercise_id}/history")
def exercise_session_history(exercise_id: int, session: Session = Depends(get_session)):
    """Return the last 10 sessions this exercise was logged in."""
    ex = session.get(Exercise, exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Get all sets for this exercise, ordered by id desc
    sets_stmt = (
        select(WorkoutSet)
        .where(WorkoutSet.exercise_id == exercise_id)
        .order_by(WorkoutSet.id.desc())
    )
    all_sets = session.exec(sets_stmt).all()

    # Group by session_id, keep up to 10 unique sessions
    seen_sessions = {}
    for ws in all_sets:
        if ws.session_id not in seen_sessions:
            seen_sessions[ws.session_id] = []
        seen_sessions[ws.session_id].append(ws)
        if len(seen_sessions) >= 10:
            break

    result = []
    for sess_id, sets in seen_sessions.items():
        wk = session.get(WorkoutSession, sess_id)
        if not wk:
            continue
        result.append(
            {
                "session_id": sess_id,
                "session_name": wk.name,
                "started_at": wk.started_at.isoformat() if wk.started_at else None,
                "sets": [
                    {
                        "set_number": s.set_number,
                        "weight": s.weight,
                        "reps": s.reps,
                        "rir": s.rir,
                    }
                    for s in sorted(sets, key=lambda x: x.set_number)
                ],
            }
        )

    return result
