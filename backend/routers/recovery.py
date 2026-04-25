from datetime import datetime, timezone, date, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session, select
from database import get_session
from models import WorkoutSet, WorkoutSession, Exercise, WeeklyCheckin
from routers.volume import _parse_muscles

router = APIRouter(prefix="/api", tags=["recovery"])

USER_ID = 1

ALL_MUSCLES = [
    "abs", "back", "biceps", "calves", "chest",
    "glutes", "hamstrings", "lats", "quads", "shoulders", "traps", "triceps",
]


@router.get("/recovery-map")
def recovery_map(session: Session = Depends(get_session)):
    stmt = (
        select(WorkoutSession.id, WorkoutSession.started_at)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at != None)
        .order_by(WorkoutSession.started_at.desc())
        .limit(10)
    )
    recent_sessions = session.exec(stmt).all()

    session_sets: dict[int, list] = {}
    exercise_cache: dict[int, Exercise] = {}
    for wk in recent_sessions:
        s_list = session.exec(select(WorkoutSet).where(WorkoutSet.session_id == wk.id)).all()
        session_sets[wk.id] = s_list
        for ws in s_list:
            if ws.exercise_id not in exercise_cache:
                ex = session.get(Exercise, ws.exercise_id)
                if ex:
                    exercise_cache[ws.exercise_id] = ex

    now = datetime.now(timezone.utc)
    result = []

    for muscle in ALL_MUSCLES:
        last_trained_dt = None
        days_since = None
        for wk in recent_sessions:
            if any(
                muscle in _parse_muscles(exercise_cache[ws.exercise_id].primary_muscles)
                for ws in session_sets.get(wk.id, [])
                if ws.exercise_id in exercise_cache
            ):
                dt = wk.started_at
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                last_trained_dt = dt
                days_since = (now - dt).total_seconds() / 86400
                break

        # Average RIR from last 3 sessions that trained this muscle
        rir_sessions = []
        for wk in recent_sessions:
            straight = [
                ws for ws in session_sets.get(wk.id, [])
                if ws.set_type == "straight"
                and ws.rir is not None
                and ws.exercise_id in exercise_cache
                and muscle in _parse_muscles(exercise_cache[ws.exercise_id].primary_muscles)
            ]
            if straight:
                rir_sessions.append(sum(ws.rir for ws in straight) / len(straight))
            if len(rir_sessions) == 3:
                break

        avg_rir = sum(rir_sessions) / len(rir_sessions) if rir_sessions else None

        if days_since is None:
            status = "gray"
            recovery_score = None
        else:
            rir_bonus = (avg_rir * 0.5) if avg_rir is not None else 1.0
            recovery_score = round(days_since + rir_bonus, 2)
            if recovery_score < 1.5:
                status = "red"
            elif recovery_score < 3.0:
                status = "amber"
            else:
                status = "green"

        result.append({
            "muscle": muscle,
            "days_since_trained": round(days_since, 1) if days_since is not None else None,
            "avg_rir": round(avg_rir, 1) if avg_rir is not None else None,
            "recovery_score": recovery_score,
            "status": status,
            "last_trained": last_trained_dt.isoformat() if last_trained_dt else None,
        })

    return {"muscles": result}


# ── Weekly check-in ────────────────────────────────────────────────────────────

class CheckinCreate(BaseModel):
    energy: int
    sleep_quality: int
    stress: int
    soreness: int
    notes: Optional[str] = ""


def _current_week_start() -> str:
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


@router.get("/recovery/checkin/status")
def checkin_status(db: Session = Depends(get_session)):
    week_start = _current_week_start()
    existing = db.exec(
        select(WeeklyCheckin).where(
            WeeklyCheckin.user_id == USER_ID,
            WeeklyCheckin.week_start == week_start,
        )
    ).first()
    is_monday = date.today().weekday() == 0
    return {
        "due": is_monday and existing is None,
        "week_start": week_start,
        "completed": existing is not None,
    }


@router.post("/recovery/checkin")
def submit_checkin(body: CheckinCreate, db: Session = Depends(get_session)):
    week_start = _current_week_start()
    existing = db.exec(
        select(WeeklyCheckin).where(
            WeeklyCheckin.user_id == USER_ID,
            WeeklyCheckin.week_start == week_start,
        )
    ).first()
    if existing:
        existing.energy = body.energy
        existing.sleep_quality = body.sleep_quality
        existing.stress = body.stress
        existing.soreness = body.soreness
        existing.notes = body.notes or ""
        db.add(existing)
    else:
        db.add(WeeklyCheckin(
            user_id=USER_ID,
            week_start=week_start,
            energy=body.energy,
            sleep_quality=body.sleep_quality,
            stress=body.stress,
            soreness=body.soreness,
            notes=body.notes or "",
        ))
    db.commit()
    return {"ok": True, "week_start": week_start}
