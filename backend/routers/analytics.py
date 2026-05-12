from datetime import timedelta
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from models import Exercise, PersonalRecord, BodyMeasurement, WorkoutSession, WorkoutSet
from routers.profile import _BIG4
from routers.volume import _aggregate_sets_by_muscle

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

USER_ID = 1

# Muscle most associated with each big-4 lift for sweet spot detection
_LIFT_MUSCLE = {
    "squat":    "quads",
    "bench":    "chest",
    "deadlift": "back",
    "ohp":      "shoulders",
}

_SWEET_SPOT_BUCKETS = ["0–5", "6–9", "10–13", "14–17", "18+"]


def _bucket(sets: float) -> str:
    if sets <= 5:
        return "0–5"
    if sets <= 9:
        return "6–9"
    if sets <= 13:
        return "10–13"
    if sets <= 17:
        return "14–17"
    return "18+"


@router.get("/strength-ratio-history")
def strength_ratio_history(session: Session = Depends(get_session)):
    result = {}
    for lift_key, canonical_name in _BIG4:
        ex = session.exec(select(Exercise).where(Exercise.name == canonical_name)).first()
        if not ex:
            result[lift_key] = []
            continue

        prs = session.exec(
            select(PersonalRecord)
            .where(
                PersonalRecord.user_id == USER_ID,
                PersonalRecord.exercise_id == ex.id,
                PersonalRecord.pr_type == "e1rm",
            )
            .order_by(PersonalRecord.achieved_at)
        ).all()

        points = []
        for pr in prs:
            pr_date_str = pr.achieved_at.strftime("%Y-%m-%d")
            bm = session.exec(
                select(BodyMeasurement)
                .where(
                    BodyMeasurement.user_id == USER_ID,
                    BodyMeasurement.body_weight != None,
                    BodyMeasurement.date <= pr_date_str,
                )
                .order_by(BodyMeasurement.date.desc())
            ).first()
            if bm and bm.body_weight:
                ratio = round(pr.value / bm.body_weight, 3)
                points.append({
                    "date": pr_date_str,
                    "e1rm": round(pr.value, 1),
                    "body_weight": bm.body_weight,
                    "ratio": ratio,
                })

        result[lift_key] = points if len(points) >= 2 else []

    return {"lifts": result}


@router.get("/volume-sweet-spot")
def volume_sweet_spot(session: Session = Depends(get_session)):
    # Pre-load all exercises for set aggregation
    all_exercises = {ex.id: ex for ex in session.exec(select(Exercise)).all()}

    muscles_out = {}
    for lift_key, canonical_name in _BIG4:
        target_muscle = _LIFT_MUSCLE[lift_key]
        ex = session.exec(select(Exercise).where(Exercise.name == canonical_name)).first()
        if not ex:
            continue

        prs = session.exec(
            select(PersonalRecord)
            .where(
                PersonalRecord.user_id == USER_ID,
                PersonalRecord.exercise_id == ex.id,
                PersonalRecord.pr_type == "e1rm",
            )
            .order_by(PersonalRecord.achieved_at)
        ).all()

        if len(prs) < 3:
            continue

        bucket_counts: dict[str, int] = {b: 0 for b in _SWEET_SPOT_BUCKETS}

        for pr in prs:
            pr_session = session.get(WorkoutSession, pr.session_id)
            if not pr_session or not pr_session.started_at:
                continue
            anchor = pr_session.started_at
            window_start = anchor - timedelta(days=7)

            window_sessions = session.exec(
                select(WorkoutSession)
                .where(
                    WorkoutSession.completed_at != None,
                    WorkoutSession.completed_at >= window_start,
                    WorkoutSession.completed_at <= anchor,
                )
            ).all()

            all_sets = []
            for ws_session in window_sessions:
                sets = session.exec(
                    select(WorkoutSet).where(WorkoutSet.session_id == ws_session.id)
                ).all()
                all_sets.extend(sets)

            muscle_sets = _aggregate_sets_by_muscle(all_sets, all_exercises)
            volume = muscle_sets.get(target_muscle, 0)
            bucket_counts[_bucket(volume)] += 1

        peak = max(bucket_counts, key=lambda b: bucket_counts[b])
        muscles_out[target_muscle] = {
            "buckets": [{"label": b, "count": bucket_counts[b]} for b in _SWEET_SPOT_BUCKETS],
            "peak_bucket": peak,
            "pr_count": len(prs),
        }

    return {"muscles": muscles_out}
