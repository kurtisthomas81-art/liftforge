import json
import re
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from database import get_session
from models import WorkoutSession, WorkoutSet, Exercise, Mesocycle, MesocycleWeek, PlannedSession, SplitDay

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

        working_sets = [ws for ws in sets if ws.set_type != "warmup"]
        result.append(
            {
                "id": wk.id,
                "name": wk.name,
                "started_at": wk.started_at.isoformat() if wk.started_at else None,
                "completed_at": wk.completed_at.isoformat() if wk.completed_at else None,
                "set_count": len(working_sets),
                "total_weight_moved": round(sum((ws.weight or 0) * ws.reps for ws in working_sets), 1),
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

        working_sets = [s for s in sets if s.set_type != "warmup"]
        max_weight = max((s.weight or 0) for s in working_sets) if working_sets else 0
        total_volume = sum((s.weight or 0) * s.reps for s in working_sets)
        best_1rm = max(
            _epley_1rm(s.weight, s.reps)
            for s in working_sets
            if s.weight and s.reps
        ) if any(s.weight and s.reps for s in working_sets) else 0

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


@router.get("/calendar")
def calendar_data(
    year: int = Query(..., description="Calendar year"),
    month: int = Query(..., description="Calendar month (1-12)"),
    session: Session = Depends(get_session),
):
    """Sessions and planned sessions for a given month."""
    # Compute month boundaries
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    start_str = month_start.isoformat()
    end_str = month_end.isoformat() + "T23:59:59"

    # Completed sessions this month
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at != None)
        .where(WorkoutSession.started_at >= start_str)
        .where(WorkoutSession.started_at <= end_str)
        .order_by(WorkoutSession.started_at.asc())
    )
    sessions_in_month = session.exec(stmt).all()

    sessions_out = []
    for wk in sessions_in_month:
        sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == wk.id)
        sets = session.exec(sets_stmt).all()
        muscle_set: set = set()
        for ws in sets:
            ex = session.get(Exercise, ws.exercise_id)
            if ex:
                for m in json.loads(ex.primary_muscles):
                    muscle_set.add(m)

        sessions_out.append({
            "date": wk.started_at.date().isoformat() if wk.started_at else None,
            "session_id": wk.id,
            "session_name": wk.name or "Unnamed Session",
            "muscles": sorted(muscle_set),
            "planned_session_id": None,
        })

    # Planned sessions for the month (from active mesocycles)
    planned_out = []
    active_meso_stmt = (
        select(Mesocycle)
        .where(Mesocycle.user_id == USER_ID)
        .where(Mesocycle.status == "active")
        .where(Mesocycle.start_date != None)
    )
    active_mesos = session.exec(active_meso_stmt).all()

    for meso in active_mesos:
        try:
            meso_start = date.fromisoformat(meso.start_date)
        except Exception:
            continue

        weeks_stmt = select(MesocycleWeek).where(
            MesocycleWeek.mesocycle_id == meso.id
        ).order_by(MesocycleWeek.week_number)
        weeks = session.exec(weeks_stmt).all()

        for week in weeks:
            week_monday = meso_start + timedelta(weeks=week.week_number - 1)
            ps_stmt = select(PlannedSession).where(
                PlannedSession.mesocycle_week_id == week.id
            )
            planned_sessions = session.exec(ps_stmt).all()

            for ps in planned_sessions:
                # day_of_week: 0=Mon, 6=Sun
                session_date = week_monday + timedelta(days=ps.day_of_week)

                # Skip already completed or outside this month
                if ps.session_id:
                    continue
                if not (month_start <= session_date <= month_end):
                    continue

                # Get split day name and muscle focus
                split_day_name = "Training Day"
                muscle_focus = []
                if ps.split_day_id:
                    sd = session.get(SplitDay, ps.split_day_id)
                    if sd:
                        split_day_name = sd.name
                        try:
                            muscle_focus = json.loads(sd.muscle_focus)
                        except Exception:
                            muscle_focus = []

                _vm = re.match(r'^(.*?)\s+([A-C])$', split_day_name)
                base_name = _vm.group(1) if _vm else split_day_name
                variant = _vm.group(2) if (_vm and meso.num_variants > 1) else None
                planned_out.append({
                    "date": session_date.isoformat(),
                    "planned_session_id": ps.id,
                    "split_day_name": split_day_name,
                    "base_session_name": base_name,
                    "variant": variant,
                    "muscle_focus": muscle_focus,
                })

    return {"sessions": sessions_out, "planned": planned_out}


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


@router.get("/search")
def search_notes(q: str = Query("", min_length=1), session: Session = Depends(get_session)):
    """Full-text search across session names, session notes, and set notes."""
    if not q.strip():
        return []
    term = q.strip().lower()

    # Sessions whose name or notes match
    all_sessions_stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at != None)
        .order_by(WorkoutSession.started_at.desc())
    )
    all_sessions = session.exec(all_sessions_stmt).all()

    results = []
    seen_session_ids: set[int] = set()

    for wk in all_sessions:
        name_match = term in (wk.name or "").lower()
        notes_match = term in (wk.notes or "").lower()

        # Check set notes for this session
        sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == wk.id)
        sets = session.exec(sets_stmt).all()

        matching_set_notes = []
        for ws in sets:
            if ws.notes and term in ws.notes.lower():
                ex = session.get(Exercise, ws.exercise_id)
                matching_set_notes.append({
                    "exercise_name": ex.name if ex else "Unknown",
                    "note": ws.notes,
                })

        if name_match or notes_match or matching_set_notes:
            seen_session_ids.add(wk.id)
            results.append({
                "session_id": wk.id,
                "session_name": wk.name or "Unnamed Session",
                "started_at": wk.started_at.isoformat() if wk.started_at else None,
                "match_type": "name" if name_match else ("notes" if notes_match else "set_notes"),
                "session_notes": wk.notes or "",
                "matching_set_notes": matching_set_notes,
            })

    return results
