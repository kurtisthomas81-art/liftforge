import json
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from models import PersonalRecord, WorkoutSet, WorkoutSession, Exercise

router = APIRouter(prefix="/api/prs", tags=["prs"])

USER_ID = 1


def _epley_1rm(weight: float, reps: int) -> float:
    if reps == 1:
        return weight
    return weight * (1 + reps / 30.0)


def _serialize_pr(pr: PersonalRecord, exercise_name: str = "") -> dict:
    return {
        "id": pr.id,
        "exercise_id": pr.exercise_id,
        "exercise_name": exercise_name,
        "pr_type": pr.pr_type,
        "value": pr.value,
        "achieved_at": pr.achieved_at.isoformat() if pr.achieved_at else None,
        "session_id": pr.session_id,
    }


@router.get("")
def get_all_prs(session: Session = Depends(get_session)):
    """All PRs grouped by exercise."""
    stmt = (
        select(PersonalRecord)
        .where(PersonalRecord.user_id == USER_ID)
        .order_by(PersonalRecord.achieved_at.desc())
    )
    prs = session.exec(stmt).all()

    grouped: dict[int, dict] = {}
    for pr in prs:
        ex = session.get(Exercise, pr.exercise_id)
        ex_name = ex.name if ex else "Unknown"
        if pr.exercise_id not in grouped:
            grouped[pr.exercise_id] = {
                "exercise_id": pr.exercise_id,
                "exercise_name": ex_name,
                "prs": [],
            }
        grouped[pr.exercise_id]["prs"].append(_serialize_pr(pr, ex_name))

    return list(grouped.values())


@router.get("/exercise/{exercise_id}")
def get_prs_for_exercise(exercise_id: int, session: Session = Depends(get_session)):
    """PR history for one exercise."""
    ex = session.get(Exercise, exercise_id)
    stmt = (
        select(PersonalRecord)
        .where(PersonalRecord.user_id == USER_ID)
        .where(PersonalRecord.exercise_id == exercise_id)
        .order_by(PersonalRecord.achieved_at.desc())
    )
    prs = session.exec(stmt).all()
    ex_name = ex.name if ex else "Unknown"
    return [_serialize_pr(pr, ex_name) for pr in prs]


@router.post("/check/{session_id}")
def check_session_prs(session_id: int, session: Session = Depends(get_session)):
    """
    Check a session for new PRs. Compare each set's e1RM and max weight to
    stored records. Persist and return any new PRs found.
    """
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        return {"new_prs": []}

    sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == session_id)
    sets = session.exec(sets_stmt).all()

    # Group by exercise
    by_exercise: dict[int, list] = {}
    for ws in sets:
        if ws.set_type == "warmup":
            continue
        by_exercise.setdefault(ws.exercise_id, []).append(ws)

    new_prs = []

    for exercise_id, ex_sets in by_exercise.items():
        ex = session.get(Exercise, exercise_id)
        ex_name = ex.name if ex else "Unknown"

        # Get current stored PRs for this exercise
        pr_stmt = select(PersonalRecord).where(
            PersonalRecord.user_id == USER_ID,
            PersonalRecord.exercise_id == exercise_id,
        )
        existing_prs = session.exec(pr_stmt).all()
        current_best: dict[str, float] = {}
        for pr in existing_prs:
            if pr.pr_type not in current_best or pr.value > current_best[pr.pr_type]:
                current_best[pr.pr_type] = pr.value

        # Find best values in this session
        session_best_e1rm = 0.0
        session_best_weight = 0.0
        session_best_reps = 0

        for ws in ex_sets:
            w = ws.weight or 0
            r = ws.reps or 0
            if w and r:
                e1rm = _epley_1rm(w, r)
                if e1rm > session_best_e1rm:
                    session_best_e1rm = e1rm
            if w > session_best_weight:
                session_best_weight = w
            if r > session_best_reps:
                session_best_reps = r

        # Check e1RM PR
        if session_best_e1rm > 0:
            if session_best_e1rm > current_best.get("e1rm", 0):
                pr = PersonalRecord(
                    user_id=USER_ID,
                    exercise_id=exercise_id,
                    pr_type="e1rm",
                    value=round(session_best_e1rm, 2),
                    achieved_at=wk.completed_at or datetime.utcnow(),
                    session_id=session_id,
                )
                session.add(pr)
                session.commit()
                session.refresh(pr)
                new_prs.append(_serialize_pr(pr, ex_name))

        # Check weight PR
        if session_best_weight > 0:
            if session_best_weight > current_best.get("weight", 0):
                pr = PersonalRecord(
                    user_id=USER_ID,
                    exercise_id=exercise_id,
                    pr_type="weight",
                    value=session_best_weight,
                    achieved_at=wk.completed_at or datetime.utcnow(),
                    session_id=session_id,
                )
                session.add(pr)
                session.commit()
                session.refresh(pr)
                new_prs.append(_serialize_pr(pr, ex_name))

        # Check reps PR (bodyweight sets)
        if session_best_reps > 0:
            if session_best_reps > current_best.get("reps", 0):
                pr = PersonalRecord(
                    user_id=USER_ID,
                    exercise_id=exercise_id,
                    pr_type="reps",
                    value=session_best_reps,
                    achieved_at=wk.completed_at or datetime.utcnow(),
                    session_id=session_id,
                )
                session.add(pr)
                session.commit()
                session.refresh(pr)
                new_prs.append(_serialize_pr(pr, ex_name))

    return {"session_id": session_id, "new_prs": new_prs}
