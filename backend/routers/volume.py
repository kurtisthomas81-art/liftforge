import json
from datetime import date, timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from database import get_session
from models import WorkoutSet, WorkoutSession, Exercise, MuscleVolumeLandmark, MesocycleWeek, PlannedSession, WeeklyCheckin, Mesocycle

router = APIRouter(prefix="/api/volume", tags=["volume"])

USER_ID = 1


def _get_landmarks(session: Session, goal: str = "hypertrophy") -> dict:
    stmt = (
        select(MuscleVolumeLandmark)
        .where(MuscleVolumeLandmark.user_id == USER_ID)
        .where(MuscleVolumeLandmark.goal == goal)
    )
    landmarks = session.exec(stmt).all()
    if not landmarks:
        # fall back to hypertrophy if no rows exist for this goal yet
        stmt = (
            select(MuscleVolumeLandmark)
            .where(MuscleVolumeLandmark.user_id == USER_ID)
            .where(MuscleVolumeLandmark.goal == "hypertrophy")
        )
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


def _aggregate_sets_by_muscle(sets: list, exercises: dict, exclude_warmup: bool = True) -> dict[str, float]:
    """Count working sets per muscle. Primary muscles = 1.0 set, secondary = 0.5 set."""
    muscle_sets: dict[str, float] = {}
    for ws in sets:
        if exclude_warmup and ws.set_type == "warmup":
            continue
        ex = exercises.get(ws.exercise_id)
        if not ex:
            continue
        for muscle in _parse_muscles(ex.primary_muscles):
            muscle_sets[muscle] = muscle_sets.get(muscle, 0) + 1.0
        for muscle in _parse_muscles(ex.secondary_muscles or "[]"):
            muscle_sets[muscle] = muscle_sets.get(muscle, 0) + 0.5
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

    # Detect the active mesocycle's goal to use goal-calibrated landmarks
    active_meso = session.exec(
        select(Mesocycle)
        .where(Mesocycle.user_id == USER_ID)
        .where(Mesocycle.status == "active")
    ).first()
    goal = active_meso.goal if active_meso else "hypertrophy"

    sets_by_muscle = _aggregate_sets_by_muscle(all_sets, exercise_cache)
    landmarks = _get_landmarks(session, goal)

    result = []
    all_muscles = set(sets_by_muscle) | set(landmarks)
    for muscle in sorted(all_muscles):
        lm = landmarks.get(muscle)
        s_count = round(sets_by_muscle.get(muscle, 0), 1)
        result.append({
            "muscle": muscle,
            "sets": s_count,
            "status": _volume_status(s_count, lm),
            "landmarks": lm,
        })

    return {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "goal": goal,
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


@router.get("/fatigue-report")
def fatigue_report(session: Session = Depends(get_session)):
    """Compute fatigue score and deload recommendation from recent training data."""
    TRACKED_MUSCLES = ["chest", "back", "quads", "hamstrings", "shoulders", "biceps", "triceps", "calves", "forearms"]

    # Get last 10 completed sessions
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at != None)
        .order_by(WorkoutSession.started_at.desc())
        .limit(10)
    )
    recent_sessions = session.exec(stmt).all()

    if not recent_sessions:
        return {
            "overall_fatigue": "low",
            "fatigue_score": 0.0,
            "deload_recommended": False,
            "reasons": [],
            "muscles_at_risk": [],
            "last_deload_days_ago": None,
        }

    # Build session → sets → exercise cache
    session_sets: dict[int, list] = {}
    exercise_cache: dict[int, Exercise] = {}
    for wk in recent_sessions:
        sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == wk.id)
        s_list = session.exec(sets_stmt).all()
        session_sets[wk.id] = s_list
        for ws in s_list:
            if ws.exercise_id not in exercise_cache:
                ex = session.get(Exercise, ws.exercise_id)
                if ex:
                    exercise_cache[ws.exercise_id] = ex

    # Per-muscle RIR trend: find last 3 sessions that trained each muscle
    muscles_at_risk = []
    reasons = []

    for muscle in TRACKED_MUSCLES:
        sessions_with_muscle = []
        for wk in recent_sessions:
            sets = session_sets.get(wk.id, [])
            muscle_straight_sets = [
                ws for ws in sets
                if ws.set_type == "straight"
                and ws.rir is not None
                and ws.exercise_id in exercise_cache
                and muscle in _parse_muscles(exercise_cache[ws.exercise_id].primary_muscles)
            ]
            if muscle_straight_sets:
                avg_rir = sum(ws.rir for ws in muscle_straight_sets) / len(muscle_straight_sets)
                sessions_with_muscle.append(avg_rir)
            if len(sessions_with_muscle) == 3:
                break

        if len(sessions_with_muscle) == 3 and all(r < 1.5 for r in sessions_with_muscle):
            muscles_at_risk.append(muscle)
            reasons.append(f"{muscle.capitalize()} RIR has averaged below 1.5 for 3 consecutive sessions")

    # Average readiness over last 7 sessions
    readiness_values = [
        wk.readiness_rating for wk in recent_sessions[:7]
        if wk.readiness_rating is not None
    ]
    avg_readiness = sum(readiness_values) / len(readiness_values) if readiness_values else None

    if avg_readiness is not None and avg_readiness < 2.5:
        reasons.append(f"Readiness ratings have averaged {avg_readiness:.1f}/5 over the past week")

    # Days since last deload
    last_deload_days_ago = None
    deload_stmt = (
        select(MesocycleWeek)
        .where(MesocycleWeek.is_deload == True)
        .order_by(MesocycleWeek.id.desc())
    )
    last_deload_week = session.exec(deload_stmt).first()
    if last_deload_week:
        # Find a planned session in that week that was completed
        ps_stmt = select(PlannedSession).where(
            PlannedSession.mesocycle_week_id == last_deload_week.id,
            PlannedSession.session_id != None,
        )
        deload_ps = session.exec(ps_stmt).first()
        if deload_ps and deload_ps.session_id:
            deload_wk = session.get(WorkoutSession, deload_ps.session_id)
            if deload_wk and deload_wk.completed_at:
                delta = datetime.utcnow() - deload_wk.completed_at
                last_deload_days_ago = delta.days

    if last_deload_days_ago is not None and last_deload_days_ago > 28:
        reasons.append(f"Last deload was {last_deload_days_ago} days ago")

    # Average post-session RPE over last 5 sessions
    rpe_values = [
        wk.post_session_rpe for wk in recent_sessions[:5]
        if wk.post_session_rpe is not None
    ]
    avg_rpe = sum(rpe_values) / len(rpe_values) if rpe_values else None

    if avg_rpe is not None and avg_rpe >= 8:
        reasons.append(f"Session RPE has averaged {avg_rpe:.1f}/10 — workouts are very hard")

    # Weekly check-in contribution
    checkin_data = None
    cutoff = datetime.utcnow() - timedelta(days=8)
    recent_checkin = session.exec(
        select(WeeklyCheckin)
        .where(WeeklyCheckin.user_id == USER_ID)
        .order_by(WeeklyCheckin.created_at.desc())
    ).first()
    if recent_checkin and recent_checkin.created_at >= cutoff:
        checkin_data = {
            "energy": recent_checkin.energy,
            "sleep_quality": recent_checkin.sleep_quality,
            "stress": recent_checkin.stress,
            "soreness": recent_checkin.soreness,
        }
        checkin_score_raw = 0.0
        if recent_checkin.energy <= 2:
            checkin_score_raw += 1.5
        if recent_checkin.stress >= 4:
            checkin_score_raw += 1.0
        if recent_checkin.sleep_quality <= 2:
            checkin_score_raw += 1.0
        if recent_checkin.soreness >= 4:
            checkin_score_raw += 0.5
        if checkin_score_raw > 0:
            reasons.append("Weekly check-in indicates elevated fatigue (low energy/sleep or high stress/soreness)")
    else:
        checkin_score_raw = 0.0

    checkin_score = min(3.0, checkin_score_raw)

    # Compute fatigue score (0-10)
    # Component 1: muscle risk score (0-4): 1 point per muscle at risk, capped at 4
    muscle_score = min(4.0, len(muscles_at_risk) * 1.0)

    # Component 2: readiness score (0-3): inverse of avg readiness (1=bad → 3pts, 5=great → 0pts)
    readiness_score = 0.0
    if avg_readiness is not None:
        readiness_score = max(0.0, (3.0 - avg_readiness) * (3.0 / 4.0))

    # Component 3: deload recency score (0-3): 28 days → 1.5, 42+ days → 3
    deload_score = 0.0
    if last_deload_days_ago is not None:
        deload_score = min(3.0, max(0.0, (last_deload_days_ago - 21) / 7.0))
    elif len(recent_sessions) >= 8:
        deload_score = 2.0

    # Component 4: RPE score (0-2): RPE ≤6 → 0, RPE 10 → 2
    rpe_score = 0.0
    if avg_rpe is not None:
        rpe_score = max(0.0, min(2.0, (avg_rpe - 6.0) * 0.5))

    fatigue_score = round(min(10.0, muscle_score + readiness_score + deload_score + rpe_score + checkin_score), 1)

    deload_recommended = fatigue_score >= 6.0 or len(muscles_at_risk) >= 3

    if fatigue_score >= 8:
        overall_fatigue = "critical"
    elif fatigue_score >= 6:
        overall_fatigue = "high"
    elif fatigue_score >= 3:
        overall_fatigue = "moderate"
    else:
        overall_fatigue = "low"

    return {
        "overall_fatigue": overall_fatigue,
        "fatigue_score": fatigue_score,
        "deload_recommended": deload_recommended,
        "reasons": reasons,
        "muscles_at_risk": muscles_at_risk,
        "last_deload_days_ago": last_deload_days_ago,
        "checkin": checkin_data,
    }
