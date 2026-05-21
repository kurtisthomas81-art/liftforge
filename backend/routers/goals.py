from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import Goal, Exercise, WorkoutSet
from utils import epley_1rm

router = APIRouter(prefix="/api/goals", tags=["goals"])

USER_ID = 1


def _serialize_goal(goal: Goal, exercise_name: str, current_value: float | None) -> dict:
    pct = 0
    if current_value is not None and goal.target_value:
        pct = min(100, round(current_value / goal.target_value * 100))
    return {
        "id": goal.id,
        "exercise_id": goal.exercise_id,
        "exercise_name": exercise_name,
        "goal_type": goal.goal_type,
        "target_value": goal.target_value,
        "deadline": goal.deadline,
        "status": goal.status,
        "achieved_at": goal.achieved_at.isoformat() if goal.achieved_at else None,
        "achieved_session_id": goal.achieved_session_id,
        "created_at": goal.created_at.isoformat() if goal.created_at else None,
        "current_value": round(current_value, 1) if current_value is not None else None,
        "pct": pct,
    }


def _best_pr_value(exercise_id: int, goal_type: str, db: Session) -> float | None:
    """Return the best PersonalRecord value for this exercise+type, or compute from sets."""
    from models import PersonalRecord
    pr = db.exec(
        select(PersonalRecord)
        .where(PersonalRecord.exercise_id == exercise_id, PersonalRecord.pr_type == goal_type)
        .order_by(PersonalRecord.value.desc())
    ).first()
    return pr.value if pr else None


def check_goals_for_session(session_id: int, db: Session) -> list[dict]:
    """Check active goals against sets from this session. Mark achieved ones. Returns list of hit goals."""
    sets = db.exec(
        select(WorkoutSet).where(
            WorkoutSet.session_id == session_id,
            WorkoutSet.set_type != "warmup",
        )
    ).all()

    if not sets:
        return []

    # Compute best values per exercise from this session's sets
    by_exercise: dict[int, dict] = {}
    for s in sets:
        if s.exercise_id not in by_exercise:
            by_exercise[s.exercise_id] = {"e1rm": 0.0, "weight": 0.0, "reps": 0}
        vals = by_exercise[s.exercise_id]
        if s.weight and s.reps:
            vals["e1rm"] = max(vals["e1rm"], epley_1rm(s.weight, s.reps))
            vals["weight"] = max(vals["weight"], s.weight)
        if s.reps:
            vals["reps"] = max(vals["reps"], s.reps)

    exercise_ids = list(by_exercise.keys())
    active_goals = db.exec(
        select(Goal).where(
            Goal.user_id == USER_ID,
            Goal.status == "active",
            Goal.exercise_id.in_(exercise_ids),
        )
    ).all()

    achieved = []
    now = datetime.utcnow()
    for goal in active_goals:
        session_val = by_exercise.get(goal.exercise_id, {}).get(goal.goal_type, 0)
        if session_val >= goal.target_value:
            goal.status = "achieved"
            goal.achieved_at = now
            goal.achieved_session_id = session_id
            db.add(goal)
            ex = db.get(Exercise, goal.exercise_id)
            achieved.append({
                "exercise_name": ex.name if ex else "Unknown",
                "goal_type": goal.goal_type,
                "target_value": goal.target_value,
                "achieved_value": round(session_val, 1),
            })

    if achieved:
        db.commit()

    return achieved


# ── Endpoints ──────────────────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    exercise_id: int
    goal_type: str
    target_value: float
    deadline: Optional[str] = None


@router.get("")
def list_goals(db: Session = Depends(get_session)):
    goals = db.exec(
        select(Goal)
        .where(Goal.user_id == USER_ID)
        .order_by(Goal.status, Goal.created_at.desc())
    ).all()

    result = []
    for goal in goals:
        ex = db.get(Exercise, goal.exercise_id)
        current = _best_pr_value(goal.exercise_id, goal.goal_type, db)
        result.append(_serialize_goal(goal, ex.name if ex else "Unknown", current))
    return result


@router.post("")
def create_goal(body: GoalCreate, db: Session = Depends(get_session)):
    if body.goal_type not in ("e1rm", "weight", "reps"):
        raise HTTPException(status_code=400, detail="goal_type must be e1rm, weight, or reps")
    ex = db.get(Exercise, body.exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")

    goal = Goal(
        user_id=USER_ID,
        exercise_id=body.exercise_id,
        goal_type=body.goal_type,
        target_value=body.target_value,
        deadline=body.deadline,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    current = _best_pr_value(goal.exercise_id, goal.goal_type, db)
    return _serialize_goal(goal, ex.name, current)


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_session)):
    goal = db.get(Goal, goal_id)
    if not goal or goal.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()
