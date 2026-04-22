import json
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from models import WorkoutSession, WorkoutSet, Exercise

router = APIRouter(prefix="/api/history", tags=["history"])

USER_ID = 1


def _epley_1rm(weight: float, reps: int) -> float:
    if reps == 1:
        return weight
    return weight * (1 + reps / 30.0)


@router.get("")
def recent_history(session: Session = Depends(get_session)):
    """Last 30 completed sessions with summary info."""
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at != None)
        .order_by(WorkoutSession.started_at.desc())
        .limit(30)
    )
    sessions = session.exec(stmt).all()

    result = []
    for wk in sessions:
        sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == wk.id)
        sets = session.exec(sets_stmt).all()

        # Collect muscles hit
        muscle_set: set[str] = set()
        for ws in sets:
            ex = session.get(Exercise, ws.exercise_id)
            if ex:
                for m in json.loads(ex.primary_muscles):
                    muscle_set.add(m)

        result.append(
            {
                "id": wk.id,
                "name": wk.name,
                "started_at": wk.started_at.isoformat() if wk.started_at else None,
                "completed_at": wk.completed_at.isoformat() if wk.completed_at else None,
                "set_count": len(sets),
                "muscles": sorted(muscle_set),
            }
        )

    return result


@router.get("/exercise/{exercise_id}")
def exercise_progression(exercise_id: int, session: Session = Depends(get_session)):
    """Progression data: date, max_weight, total_volume, estimated_1rm per session."""
    ex = session.get(Exercise, exercise_id)
    if not ex:
        return []

    sets_stmt = (
        select(WorkoutSet)
        .where(WorkoutSet.exercise_id == exercise_id)
        .order_by(WorkoutSet.id)
    )
    all_sets = session.exec(sets_stmt).all()

    # Group by session
    session_groups: dict[int, list] = {}
    for ws in all_sets:
        session_groups.setdefault(ws.session_id, []).append(ws)

    result = []
    for sess_id, sets in session_groups.items():
        wk = session.get(WorkoutSession, sess_id)
        if not wk or not wk.completed_at:
            continue

        max_weight = max((s.weight or 0) for s in sets)
        total_volume = sum((s.weight or 0) * s.reps for s in sets)
        best_1rm = max(
            _epley_1rm(s.weight, s.reps)
            for s in sets
            if s.weight and s.reps
        ) if any(s.weight and s.reps for s in sets) else 0

        result.append(
            {
                "session_id": sess_id,
                "date": wk.started_at.isoformat() if wk.started_at else None,
                "max_weight": max_weight,
                "total_volume": round(total_volume, 2),
                "estimated_1rm": round(best_1rm, 2),
            }
        )

    # Sort chronologically
    result.sort(key=lambda x: x["date"] or "")
    return result


@router.get("/exercise/{exercise_id}/last-session")
def last_session_for_exercise(exercise_id: int, session: Session = Depends(get_session)):
    """Most recent sets for this exercise (reference during logging)."""
    sets_stmt = (
        select(WorkoutSet)
        .where(WorkoutSet.exercise_id == exercise_id)
        .order_by(WorkoutSet.id.desc())
    )
    all_sets = session.exec(sets_stmt).all()

    if not all_sets:
        return None

    # Find the most recent session that has sets for this exercise
    last_session_id = None
    for ws in all_sets:
        wk = session.get(WorkoutSession, ws.session_id)
        if wk:
            last_session_id = ws.session_id
            break

    if not last_session_id:
        return None

    wk = session.get(WorkoutSession, last_session_id)
    session_sets = [ws for ws in all_sets if ws.session_id == last_session_id]
    session_sets.sort(key=lambda x: x.set_number)

    return {
        "session_id": last_session_id,
        "session_name": wk.name if wk else None,
        "date": wk.started_at.isoformat() if wk and wk.started_at else None,
        "sets": [
            {
                "set_number": ws.set_number,
                "weight": ws.weight,
                "reps": ws.reps,
                "rir": ws.rir,
                "set_type": ws.set_type,
            }
            for ws in session_sets
            if ws.set_type != "warmup"  # exclude warm-up sets from reference
        ],
    }
