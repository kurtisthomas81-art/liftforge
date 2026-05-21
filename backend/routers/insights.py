from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from models import WorkoutSession, WorkoutSet, Exercise, MuscleVolumeLandmark, Mesocycle
from utils import parse_muscle_list as _parse_muscles
from engine.meso_builder import RECOVERY_HOURS
from routers.volume import _aggregate_sets_by_muscle, _get_landmarks

router = APIRouter(prefix="/api/insights", tags=["insights"])

USER_ID = 1

_TRACKED_MUSCLES = ["chest", "back", "quads", "hamstrings", "shoulders", "biceps", "triceps"]


def _get_active_goal(session: Session) -> str:
    meso = session.exec(
        select(Mesocycle)
        .where(Mesocycle.user_id == USER_ID, Mesocycle.status == "active")
    ).first()
    return meso.goal if meso and meso.goal else "general_fitness"


def _sets_this_week(session: Session) -> dict[str, float]:
    now = datetime.utcnow()
    offset = (now.weekday()) % 7
    monday = now - timedelta(days=offset)
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at.isnot(None))
        .where(WorkoutSession.started_at >= monday.isoformat())
    )
    sessions = session.exec(stmt).all()
    if not sessions:
        return {}

    session_ids = [s.id for s in sessions]
    all_sets = session.exec(
        select(WorkoutSet).where(WorkoutSet.session_id.in_(session_ids))
    ).all()
    exercises = {ex.id: ex for ex in session.exec(select(Exercise)).all()}
    return _aggregate_sets_by_muscle(all_sets, exercises)


def _last_trained_muscle(session: Session, muscle: str) -> tuple[float | None, float | None]:
    """Returns (hours_since_trained, avg_rir) for the most recent session that hit this muscle."""
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at.isnot(None))
        .order_by(WorkoutSession.started_at.desc())
        .limit(20)
    )
    sessions = session.exec(stmt).all()

    for wk in sessions:
        sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == wk.id)
        sets = session.exec(sets_stmt).all()
        for ws in sets:
            ex = session.get(Exercise, ws.exercise_id)
            if not ex:
                continue
            pm = _parse_muscles(ex.primary_muscles)
            sm = _parse_muscles(ex.secondary_muscles)
            if muscle in pm or muscle in sm:
                try:
                    started = datetime.fromisoformat(wk.started_at)
                    hours = (datetime.utcnow() - started).total_seconds() / 3600
                except (ValueError, TypeError):
                    hours = None
                rir_vals = [ws2.rir for ws2 in sets if ws2.rir is not None and ws2.set_type != "warmup"]
                avg_rir = round(sum(rir_vals) / len(rir_vals), 1) if rir_vals else None
                return hours, avg_rir

    return None, None


def _ar_hints(session: Session) -> dict[int, float]:
    """Return {exercise_id: suggested_weight} for exercises showing avg RIR ≤ 1 in last 2 sessions."""
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at.isnot(None))
        .order_by(WorkoutSession.started_at.desc())
        .limit(20)
    )
    sessions = session.exec(stmt).all()

    ex_session_data: dict[int, list] = {}
    for wk in sessions:
        sets = session.exec(select(WorkoutSet).where(WorkoutSet.session_id == wk.id)).all()
        for ws in sets:
            if ws.rir is None or ws.set_type == "warmup" or not ws.weight:
                continue
            ex_session_data.setdefault(ws.exercise_id, []).append(ws)

    hints = {}
    for ex_id, sets in ex_session_data.items():
        if len(sets) < 2:
            continue
        rir_vals = [ws.rir for ws in sets]
        if sum(rir_vals) / len(rir_vals) <= 1:
            best_weight = max(ws.weight for ws in sets if ws.weight)
            hints[ex_id] = round(best_weight * 1.025 / 2.5) * 2.5
    return hints


@router.get("")
def get_insights(session: Session = Depends(get_session)):
    cards = []
    goal = _get_active_goal(session)
    landmarks = _get_landmarks(session, goal)
    muscle_sets = _sets_this_week(session)
    ar = _ar_hints(session)

    # 1. Deload signal — check fatigue from recent volume and RIR patterns
    try:
        from routers.volume import fatigue_report as _fatigue_fn
        fatigue = _fatigue_fn(session)
        if fatigue.get("fatigue_score", 0) >= 6:
            cards.append({
                "type": "deload",
                "headline": "High training load",
                "body": "Your fatigue score is elevated. A lighter week (Recovery Week / Deload) would help your body absorb your training.",
                "action": {"label": "See Recovery", "url": "/recovery"},
                "priority": 1,
            })
    except Exception:
        pass

    # 2. Recovery ready — muscle recovered AND last RIR ≤ 2
    if len(cards) < 3:
        for muscle in _TRACKED_MUSCLES:
            hours_since, avg_rir = _last_trained_muscle(session, muscle)
            if hours_since is None:
                continue
            needed = RECOVERY_HOURS.get(muscle, 48)
            if hours_since >= needed and avg_rir is not None and avg_rir <= 2:
                cards.append({
                    "type": "recovery",
                    "headline": f"Your {muscle} is ready",
                    "body": f"Last trained {round(hours_since / 24, 1)} days ago at RIR {avg_rir}. Good session window.",
                    "action": {"label": "Start Workout", "url": "/log"},
                    "priority": 2,
                })
            if len(cards) >= 3:
                break

    # 3. Autoregulation — exercise ready for a weight jump
    if len(cards) < 3 and ar:
        ex_id = next(iter(ar))
        ex = session.get(Exercise, ex_id)
        if ex:
            cards.append({
                "type": "overload",
                "headline": f"{ex.name} is ready to progress",
                "body": f"Your last 2 sessions showed very low reps in reserve. Try {ar[ex_id]} lbs next session.",
                "action": {"label": "Start Workout", "url": "/log"},
                "priority": 3,
            })

    # 4. Volume below MEV
    if len(cards) < 3:
        lagging = []
        for muscle in _TRACKED_MUSCLES:
            sets = muscle_sets.get(muscle, 0)
            lm = landmarks.get(muscle)
            if lm and sets < lm.get("mev", 0):
                lagging.append(muscle)
        if len(lagging) >= 3:
            names = ", ".join(lagging[:3])
            cards.append({
                "type": "volume",
                "headline": "Some muscles need more volume",
                "body": f"You haven't hit minimum volume for {names} this week.",
                "action": {"label": "View Volume", "url": "/program"},
                "priority": 4,
            })

    cards.sort(key=lambda c: c["priority"])
    return cards[:3]
