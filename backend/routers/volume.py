import json
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from database import get_session
from models import WorkoutSet, WorkoutSession, Exercise, MuscleVolumeLandmark, MesocycleWeek, PlannedSession

router = APIRouter(prefix="/api/volume", tags=["volume"])

USER_ID = 1


def _get_landmarks(session: Session) -> dict:
    stmt = select(MuscleVolumeLandmark).where(MuscleVolumeLandmark.user_id == USER_ID)
    landmarks = session.exec(stmt).all()
    return {lm.muscle: {"mev": lm.mev, "mav_low": lm.mav_low, "mav_high": lm.mav_high, "mrv": lm.mrv}
            for lm in landmarks}


def _parse_muscles(raw: str) -> list[str]:
    try:
        return json.loads(raw)
    except Exception:
        return []


def _volume_status(sets: int, lm: dict | None) -> str:
    if not lm:
        return "unknown"
    if sets < lm["mev"]:
        return "below_mev"
    if sets <= lm["mav_high"]:
        return "in_mav"
    if sets < lm["mrv"]:
        return "above_mav"
    return "at_mrv"


def _aggregate_sets_by_muscle(sets: list, exercises: dict, exclude_warmup: bool = True) -> dict[str, int]:
    """Count working sets per primary muscle, excluding warm-up sets."""
    muscle_sets: dict[str, int] = {}
    for ws in sets:
        if exclude_warmup and ws.set_type == "warmup":
            continue
        ex = exercises.get(ws.exercise_id)
        if not ex:
            continue
        muscles = _parse_muscles(ex.primary_muscles)
        for muscle in muscles:
            muscle_sets[muscle] = muscle_sets.get(muscle, 0) + 1
    return muscle_sets


def _aggregate_volume_load(sets: list, exercises: dict, exclude_warmup: bool = True) -> dict[str, float]:
    """Sum (weight * reps) per primary muscle."""
    muscle_vol: dict[str, float] = {}
    for ws in sets:
        if exclude_warmup and ws.set_type == "warmup":
            continue
        ex = exercises.get(ws.exercise_id)
        if not ex:
            continue
        muscles = _parse_muscles(ex.primary_muscles)
        vol = (ws.weight or 0) * ws.reps
        for muscle in muscles:
            muscle_vol[muscle] = muscle_vol.get(muscle, 0) + vol
    return muscle_vol


@router.get("/session/{session_id}")
def volume_for_session(session_id: int, session: Session = Depends(get_session)):
    """Sets + volume_load per muscle for a session."""
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        return {"error": "Session not found"}

    sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == session_id)
    sets = session.exec(sets_stmt).all()

    exercise_ids = {ws.exercise_id for ws in sets}
    exercises = {eid: session.get(Exercise, eid) for eid in exercise_ids}

    sets_by_muscle = _aggregate_sets_by_muscle(sets, exercises)
    volume_by_muscle = _aggregate_volume_load(sets, exercises)
    landmarks = _get_landmarks(session)

    result = []
    for muscle in sorted(set(sets_by_muscle) | set(volume_by_muscle)):
        lm = landmarks.get(muscle)
        result.append({
            "muscle": muscle,
            "sets": sets_by_muscle.get(muscle, 0),
            "volume_load": round(volume_by_muscle.get(muscle, 0), 1),
            "status": _volume_status(sets_by_muscle.get(muscle, 0), lm),
            "landmarks": lm,
        })

    return {"session_id": session_id, "muscles": result}


@router.get("/week")
def volume_for_week(
    date: Optional[str] = Query(default=None, description="Any date in the desired Mon-Sun week (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
):
    """Sets per muscle for the Mon-Sun week containing the given date."""
    if date:
        target = __import__("datetime").date.fromisoformat(date)
    else:
        target = __import__("datetime").date.today()

    monday = target - timedelta(days=target.weekday())
    sunday = monday + timedelta(days=6)

    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.started_at >= monday.isoformat())
        .where(WorkoutSession.started_at <= (sunday.isoformat() + "T23:59:59"))
    )
    sessions = session.exec(stmt).all()

    all_sets = []
    exercise_cache: dict[int, Exercise] = {}

    for wk in sessions:
        sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == wk.id)
        s = session.exec(sets_stmt).all()
        all_sets.extend(s)
        for ws in s:
            if ws.exercise_id not in exercise_cache:
                ex = session.get(Exercise, ws.exercise_id)
                if ex:
                    exercise_cache[ws.exercise_id] = ex

    sets_by_muscle = _aggregate_sets_by_muscle(all_sets, exercise_cache)
    landmarks = _get_landmarks(session)

    result = []
    all_muscles = set(sets_by_muscle) | set(landmarks)
    for muscle in sorted(all_muscles):
        lm = landmarks.get(muscle)
        s_count = sets_by_muscle.get(muscle, 0)
        result.append({
            "muscle": muscle,
            "sets": s_count,
            "status": _volume_status(s_count, lm),
            "landmarks": lm,
        })

    return {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "muscles": result,
    }


@router.get("/mesocycle/{id}")
def volume_for_mesocycle(id: int, session: Session = Depends(get_session)):
    """Sets per muscle per week for a whole mesocycle."""
    from models import Mesocycle
    meso = session.get(Mesocycle, id)
    if not meso or meso.user_id != USER_ID:
        return {"error": "Mesocycle not found"}

    weeks_stmt = select(MesocycleWeek).where(
        MesocycleWeek.mesocycle_id == id
    ).order_by(MesocycleWeek.week_number)
    weeks = session.exec(weeks_stmt).all()

    landmarks = _get_landmarks(session)
    all_muscles: set[str] = set(landmarks.keys())
    result_by_week = []

    for week in weeks:
        ps_stmt = select(PlannedSession).where(PlannedSession.mesocycle_week_id == week.id)
        planned_sessions = session.exec(ps_stmt).all()

        all_sets = []
        exercise_cache: dict[int, Exercise] = {}

        for ps in planned_sessions:
            if ps.session_id:
                sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == ps.session_id)
                s = session.exec(sets_stmt).all()
                all_sets.extend(s)
                for ws in s:
                    if ws.exercise_id not in exercise_cache:
                        ex = session.get(Exercise, ws.exercise_id)
                        if ex:
                            exercise_cache[ws.exercise_id] = ex

        sets_by_muscle = _aggregate_sets_by_muscle(all_sets, exercise_cache)
        all_muscles.update(sets_by_muscle.keys())

        result_by_week.append({
            "week_number": week.week_number,
            "is_deload": week.is_deload,
            "muscles": sets_by_muscle,
        })

    return {
        "mesocycle_id": id,
        "mesocycle_name": meso.name,
        "all_muscles": sorted(all_muscles),
        "landmarks": landmarks,
        "weeks": result_by_week,
    }


@router.get("/alltime")
def volume_alltime(
    weeks: int = Query(default=52, description="Number of weeks to look back"),
    session: Session = Depends(get_session),
):
    """Weekly sets per muscle for the last N weeks."""
    today = __import__("datetime").date.today()
    monday = today - timedelta(days=today.weekday())
    start = monday - timedelta(weeks=weeks - 1)

    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.started_at >= start.isoformat())
    )
    sessions = session.exec(stmt).all()

    # Group sessions by ISO week
    week_data: dict[str, dict] = {}
    for wk in sessions:
        if not wk.started_at:
            continue
        session_date = wk.started_at.date()
        week_monday = session_date - timedelta(days=session_date.weekday())
        wk_key = week_monday.isoformat()

        if wk_key not in week_data:
            week_data[wk_key] = {"sessions": [], "sets": [], "exercises": {}}

        sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == wk.id)
        s = session.exec(sets_stmt).all()
        week_data[wk_key]["sets"].extend(s)

        for ws in s:
            if ws.exercise_id not in week_data[wk_key]["exercises"]:
                ex = session.get(Exercise, ws.exercise_id)
                if ex:
                    week_data[wk_key]["exercises"][ws.exercise_id] = ex

    result = []
    for wk_start in sorted(week_data.keys()):
        wd = week_data[wk_start]
        sets_by_muscle = _aggregate_sets_by_muscle(wd["sets"], wd["exercises"])
        result.append({
            "week_start": wk_start,
            "muscles": sets_by_muscle,
        })

    landmarks = _get_landmarks(session)
    return {"weeks": result, "landmarks": landmarks}
