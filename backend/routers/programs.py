import json
from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import (
    SplitTemplate, SplitDay,
    Mesocycle, MesocycleWeek, PlannedSession, PlannedExercise,
    WorkoutSession, Exercise, UserEquipment, MuscleVolumeLandmark
)

router = APIRouter(prefix="/api/programs", tags=["programs"])

USER_ID = 1


# ── Serialisers ────────────────────────────────────────────────────────────────

def _serialize_template(t: SplitTemplate, days: list[SplitDay] = None) -> dict:
    d = {
        "id": t.id,
        "name": t.name,
        "slug": t.slug,
        "days_per_week": t.days_per_week,
        "split_type": t.split_type,
        "description": t.description,
        "frequency_note": t.frequency_note,
        "is_recommended": t.is_recommended,
    }
    if days is not None:
        d["days"] = [_serialize_split_day(day) for day in sorted(days, key=lambda x: x.day_number)]
    return d


def _serialize_split_day(day: SplitDay) -> dict:
    try:
        muscles = json.loads(day.muscle_focus)
    except Exception:
        muscles = []
    return {
        "id": day.id,
        "template_id": day.template_id,
        "day_number": day.day_number,
        "name": day.name,
        "muscle_focus": muscles,
    }


def _serialize_mesocycle(m: Mesocycle) -> dict:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "name": m.name,
        "split_template_id": m.split_template_id,
        "weeks_total": m.weeks_total,
        "current_week": m.current_week,
        "status": m.status,
        "goal": m.goal,
        "start_date": m.start_date,
        "deload_week": m.deload_week,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _serialize_planned_session(ps: PlannedSession, exercises: list = None) -> dict:
    d = {
        "id": ps.id,
        "mesocycle_week_id": ps.mesocycle_week_id,
        "split_day_id": ps.split_day_id,
        "day_of_week": ps.day_of_week,
        "session_id": ps.session_id,
    }
    if exercises is not None:
        d["exercises"] = exercises
    return d


def _serialize_planned_exercise(pe: PlannedExercise, exercise_name: str = "") -> dict:
    return {
        "id": pe.id,
        "planned_session_id": pe.planned_session_id,
        "exercise_id": pe.exercise_id,
        "exercise_name": exercise_name,
        "order_in_session": pe.order_in_session,
        "target_sets": pe.target_sets,
        "target_reps_min": pe.target_reps_min,
        "target_reps_max": pe.target_reps_max,
        "target_rir": pe.target_rir,
        "notes": pe.notes,
    }


# ── Splits ─────────────────────────────────────────────────────────────────────

@router.get("/splits")
def list_splits(session: Session = Depends(get_session)):
    """List all split templates grouped by days_per_week."""
    templates = session.exec(select(SplitTemplate)).all()
    days_all = session.exec(select(SplitDay)).all()

    days_by_template: dict[int, list] = {}
    for d in days_all:
        days_by_template.setdefault(d.template_id, []).append(d)

    grouped: dict[int, list] = {}
    for t in templates:
        days = days_by_template.get(t.id, [])
        entry = _serialize_template(t, days)
        grouped.setdefault(t.days_per_week, []).append(entry)

    result = []
    for dpw in sorted(grouped.keys()):
        result.append({
            "days_per_week": dpw,
            "templates": grouped[dpw],
        })
    return result


@router.get("/splits/{slug}")
def get_split(slug: str, session: Session = Depends(get_session)):
    """Template detail with all days."""
    stmt = select(SplitTemplate).where(SplitTemplate.slug == slug)
    template = session.exec(stmt).first()
    if not template:
        raise HTTPException(status_code=404, detail="Split not found")

    days_stmt = select(SplitDay).where(SplitDay.template_id == template.id)
    days = session.exec(days_stmt).all()
    return _serialize_template(template, days)


# ── Mesocycles ─────────────────────────────────────────────────────────────────

class MesocycleCreate(BaseModel):
    split_slug: Optional[str] = None
    goal: str = "hypertrophy"
    weeks: int = 5
    start_date: Optional[str] = None
    name: Optional[str] = None
    days_of_week: list[int] = []  # maps split day_number-1 → day_of_week (0=Mon)
    # For custom splits
    custom_days: Optional[list[dict]] = None  # [{"name": "Push", "muscle_focus": [...]}]


class MesocycleUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


class PlannedExerciseCreate(BaseModel):
    exercise_id: int
    order_in_session: int = 1
    target_sets: int
    target_reps_min: int
    target_reps_max: int
    target_rir: int = 2
    notes: str = ""


def _build_planned_sessions(
    meso_id: int,
    weeks_data: list[dict],
    days_of_week: list[int],
    session: Session,
    days_lookup: dict,  # day_number -> SplitDay.id
):
    """Persist MesocycleWeeks + PlannedSessions + PlannedExercises."""
    for week_data in weeks_data:
        week = MesocycleWeek(
            mesocycle_id=meso_id,
            week_number=week_data["week_number"],
            is_deload=week_data["is_deload"],
        )
        session.add(week)
        session.commit()
        session.refresh(week)

        for idx, sess_data in enumerate(week_data["sessions"]):
            dow = days_of_week[idx] if idx < len(days_of_week) else idx
            day_num = sess_data["day_number"]
            split_day_id = days_lookup.get(day_num)

            ps = PlannedSession(
                mesocycle_week_id=week.id,
                split_day_id=split_day_id,
                day_of_week=dow,
                session_id=None,
            )
            session.add(ps)
            session.commit()
            session.refresh(ps)

            for ex_data in sess_data["exercises"]:
                pe = PlannedExercise(
                    planned_session_id=ps.id,
                    exercise_id=ex_data["exercise_id"],
                    order_in_session=ex_data["order_in_session"],
                    target_sets=ex_data["target_sets"],
                    target_reps_min=ex_data["target_reps_min"],
                    target_reps_max=ex_data["target_reps_max"],
                    target_rir=ex_data["target_rir"],
                    notes=ex_data.get("notes", ""),
                )
                session.add(pe)
            session.commit()


@router.post("/mesocycles")
def create_mesocycle(payload: MesocycleCreate, session: Session = Depends(get_session)):
    from engine.meso_builder import generate_mesocycle

    # Deactivate any existing active mesocycles
    active_stmt = select(Mesocycle).where(
        Mesocycle.user_id == USER_ID,
        Mesocycle.status == "active",
    )
    for old in session.exec(active_stmt).all():
        old.status = "abandoned"
        session.add(old)
    session.commit()

    # Resolve split template
    template = None
    days = []
    days_lookup: dict[int, int] = {}  # day_number -> split_day id

    if payload.split_slug:
        stmt = select(SplitTemplate).where(SplitTemplate.slug == payload.split_slug)
        template = session.exec(stmt).first()
        if not template:
            raise HTTPException(status_code=404, detail="Split template not found")
        days_stmt = select(SplitDay).where(SplitDay.template_id == template.id)
        days = sorted(session.exec(days_stmt).all(), key=lambda d: d.day_number)
        days_lookup = {d.day_number: d.id for d in days}

    # Determine days_per_week from template or custom_days
    if template:
        days_per_week = template.days_per_week
    elif payload.custom_days:
        days_per_week = len(payload.custom_days)
    else:
        raise HTTPException(status_code=400, detail="split_slug or custom_days required")

    deload_week = payload.weeks  # last week is deload by default
    start = payload.start_date or date.today().isoformat()

    # Auto-name
    name = payload.name
    if not name:
        from datetime import datetime as dt
        now = dt.utcnow()
        month_year = now.strftime("%B %Y")
        name = f"Mesocycle {month_year}"

    meso = Mesocycle(
        user_id=USER_ID,
        name=name,
        split_template_id=template.id if template else None,
        weeks_total=payload.weeks,
        current_week=1,
        status="active",
        goal=payload.goal,
        start_date=start,
        deload_week=deload_week,
    )
    session.add(meso)
    session.commit()
    session.refresh(meso)

    # Get user equipment
    eq_stmt = select(UserEquipment).where(
        UserEquipment.user_id == USER_ID,
        UserEquipment.available == True,
    )
    user_equipment = [e.equipment for e in session.exec(eq_stmt).all()]
    if not user_equipment:
        # Fall back to bodyweight + common free weights
        user_equipment = ["bodyweight", "dumbbells", "barbell", "bench", "rack", "cable_machine", "machine"]

    # Get landmarks
    lm_stmt = select(MuscleVolumeLandmark).where(MuscleVolumeLandmark.user_id == USER_ID)
    landmarks_raw = session.exec(lm_stmt).all()
    landmarks = {lm.muscle: {"mev": lm.mev, "mav_low": lm.mav_low, "mav_high": lm.mav_high, "mrv": lm.mrv}
                 for lm in landmarks_raw}

    # Get all exercises as dicts
    all_exercises = session.exec(select(Exercise)).all()
    exercises_db = []
    for ex in all_exercises:
        try:
            pm = json.loads(ex.primary_muscles)
        except Exception:
            pm = []
        try:
            eq = json.loads(ex.equipment_required)
        except Exception:
            eq = []
        exercises_db.append({
            "id": ex.id,
            "name": ex.name,
            "primary_muscles": pm,
            "mechanics": ex.mechanics,
            "equipment_required": eq,
        })

    # Build template data structure for engine
    if template:
        template_data = {
            "days": [
                {
                    "day_number": d.day_number,
                    "id": d.id,
                    "name": d.name,
                    "muscle_focus": d.muscle_focus,
                }
                for d in days
            ]
        }
    else:
        template_data = {
            "days": [
                {
                    "day_number": i + 1,
                    "id": None,
                    "name": cd["name"],
                    "muscle_focus": json.dumps(cd.get("muscle_focus", [])),
                }
                for i, cd in enumerate(payload.custom_days)
            ]
        }

    weeks_data = generate_mesocycle(
        split_template=template_data,
        goal=payload.goal,
        weeks=payload.weeks,
        deload_week=deload_week,
        landmarks=landmarks,
        available_equipment=user_equipment,
        exercises_db=exercises_db,
    )

    # Ensure days_of_week has enough entries
    dow_list = list(payload.days_of_week)
    while len(dow_list) < days_per_week:
        dow_list.append(len(dow_list) % 7)

    _build_planned_sessions(meso.id, weeks_data, dow_list, session, days_lookup)

    return _serialize_mesocycle(meso)


@router.get("/mesocycles")
def list_mesocycles(session: Session = Depends(get_session)):
    stmt = (
        select(Mesocycle)
        .where(Mesocycle.user_id == USER_ID)
        .order_by(Mesocycle.created_at.desc())
    )
    return [_serialize_mesocycle(m) for m in session.exec(stmt).all()]


@router.get("/mesocycles/active")
def get_active_mesocycle(session: Session = Depends(get_session)):
    """Current active mesocycle with this week's planned sessions."""
    stmt = select(Mesocycle).where(
        Mesocycle.user_id == USER_ID,
        Mesocycle.status == "active",
    )
    meso = session.exec(stmt).first()
    if not meso:
        return None

    data = _serialize_mesocycle(meso)

    # Get current week's planned sessions
    week_stmt = select(MesocycleWeek).where(
        MesocycleWeek.mesocycle_id == meso.id,
        MesocycleWeek.week_number == meso.current_week,
    )
    week = session.exec(week_stmt).first()
    if week:
        ps_stmt = select(PlannedSession).where(PlannedSession.mesocycle_week_id == week.id)
        planned_sessions = session.exec(ps_stmt).all()

        sessions_out = []
        for ps in sorted(planned_sessions, key=lambda x: x.day_of_week):
            # Get split day name
            split_day_name = ""
            if ps.split_day_id:
                sd = session.get(SplitDay, ps.split_day_id)
                if sd:
                    split_day_name = sd.name

            pe_stmt = select(PlannedExercise).where(
                PlannedExercise.planned_session_id == ps.id
            ).order_by(PlannedExercise.order_in_session)
            exercises = session.exec(pe_stmt).all()

            ex_list = []
            for pe in exercises:
                ex = session.get(Exercise, pe.exercise_id)
                ex_list.append(_serialize_planned_exercise(pe, ex.name if ex else ""))

            sessions_out.append({
                **_serialize_planned_session(ps),
                "split_day_name": split_day_name,
                "exercises": ex_list,
            })

        data["current_week_sessions"] = sessions_out
        data["current_week_is_deload"] = week.is_deload
    else:
        data["current_week_sessions"] = []
        data["current_week_is_deload"] = False

    # Attach split template info
    if meso.split_template_id:
        tmpl = session.get(SplitTemplate, meso.split_template_id)
        if tmpl:
            data["split_name"] = tmpl.name

    return data


@router.get("/mesocycles/{id}")
def get_mesocycle(id: int, session: Session = Depends(get_session)):
    meso = session.get(Mesocycle, id)
    if not meso or meso.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Mesocycle not found")

    data = _serialize_mesocycle(meso)

    # Load all weeks
    weeks_stmt = select(MesocycleWeek).where(
        MesocycleWeek.mesocycle_id == meso.id
    ).order_by(MesocycleWeek.week_number)
    weeks = session.exec(weeks_stmt).all()

    weeks_out = []
    for week in weeks:
        ps_stmt = select(PlannedSession).where(
            PlannedSession.mesocycle_week_id == week.id
        )
        planned_sessions = session.exec(ps_stmt).all()

        sessions_out = []
        for ps in sorted(planned_sessions, key=lambda x: x.day_of_week):
            split_day_name = ""
            if ps.split_day_id:
                sd = session.get(SplitDay, ps.split_day_id)
                if sd:
                    split_day_name = sd.name

            pe_stmt = select(PlannedExercise).where(
                PlannedExercise.planned_session_id == ps.id
            ).order_by(PlannedExercise.order_in_session)
            exercises = session.exec(pe_stmt).all()

            ex_list = []
            for pe in exercises:
                ex = session.get(Exercise, pe.exercise_id)
                ex_list.append(_serialize_planned_exercise(pe, ex.name if ex else ""))

            sessions_out.append({
                **_serialize_planned_session(ps),
                "split_day_name": split_day_name,
                "exercises": ex_list,
                "completed": ps.session_id is not None,
            })

        weeks_out.append({
            "id": week.id,
            "week_number": week.week_number,
            "is_deload": week.is_deload,
            "sessions": sessions_out,
        })

    data["weeks"] = weeks_out

    if meso.split_template_id:
        tmpl = session.get(SplitTemplate, meso.split_template_id)
        if tmpl:
            data["split_name"] = tmpl.name

    return data


@router.patch("/mesocycles/{id}")
def update_mesocycle(id: int, payload: MesocycleUpdate, session: Session = Depends(get_session)):
    meso = session.get(Mesocycle, id)
    if not meso or meso.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Mesocycle not found")
    if payload.name is not None:
        meso.name = payload.name
    if payload.status is not None:
        meso.status = payload.status
    session.add(meso)
    session.commit()
    session.refresh(meso)
    return _serialize_mesocycle(meso)


@router.post("/mesocycles/{id}/advance")
def advance_mesocycle(id: int, session: Session = Depends(get_session)):
    """Increment current_week. If we've hit total, mark complete."""
    meso = session.get(Mesocycle, id)
    if not meso or meso.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Mesocycle not found")

    if meso.current_week >= meso.weeks_total:
        meso.status = "completed"
        session.add(meso)
        session.commit()
        return {"status": "completed", "message": "Mesocycle complete"}

    meso.current_week += 1
    session.add(meso)
    session.commit()
    session.refresh(meso)
    return _serialize_mesocycle(meso)


# ── Planned Sessions ───────────────────────────────────────────────────────────

@router.get("/planned/{id}")
def get_planned_session(id: int, session: Session = Depends(get_session)):
    ps = session.get(PlannedSession, id)
    if not ps:
        raise HTTPException(status_code=404, detail="Planned session not found")

    split_day_name = ""
    muscles: list[str] = []
    if ps.split_day_id:
        sd = session.get(SplitDay, ps.split_day_id)
        if sd:
            split_day_name = sd.name
            try:
                muscles = json.loads(sd.muscle_focus)
            except Exception:
                muscles = []

    # Get mesocycle info
    week = session.get(MesocycleWeek, ps.mesocycle_week_id)
    meso = session.get(Mesocycle, week.mesocycle_id) if week else None
    meso_name = meso.name if meso else ""
    week_num = week.week_number if week else 1

    pe_stmt = select(PlannedExercise).where(
        PlannedExercise.planned_session_id == ps.id
    ).order_by(PlannedExercise.order_in_session)
    planned_exercises = session.exec(pe_stmt).all()

    # Find previous week's same split day for reference
    prev_week_sessions: dict[int, dict] = {}
    if week and meso:
        prev_week_stmt = select(MesocycleWeek).where(
            MesocycleWeek.mesocycle_id == meso.id,
            MesocycleWeek.week_number == week.week_number - 1,
        )
        prev_week = session.exec(prev_week_stmt).first()
        if prev_week:
            prev_ps_stmt = select(PlannedSession).where(
                PlannedSession.mesocycle_week_id == prev_week.id,
                PlannedSession.split_day_id == ps.split_day_id,
            )
            prev_ps = session.exec(prev_ps_stmt).first()
            if prev_ps and prev_ps.session_id:
                from models import WorkoutSet
                sets_stmt = select(WorkoutSet).where(
                    WorkoutSet.session_id == prev_ps.session_id
                )
                prev_sets = session.exec(sets_stmt).all()
                for ws in prev_sets:
                    if ws.exercise_id not in prev_week_sessions:
                        prev_week_sessions[ws.exercise_id] = {
                            "max_weight": ws.weight or 0,
                            "reps": ws.reps,
                            "rir": ws.rir,
                        }
                    else:
                        if (ws.weight or 0) > prev_week_sessions[ws.exercise_id]["max_weight"]:
                            prev_week_sessions[ws.exercise_id] = {
                                "max_weight": ws.weight or 0,
                                "reps": ws.reps,
                                "rir": ws.rir,
                            }

    ex_list = []
    for pe in planned_exercises:
        ex = session.get(Exercise, pe.exercise_id)
        ex_data = _serialize_planned_exercise(pe, ex.name if ex else "")

        # Attach last-week reference
        prev = prev_week_sessions.get(pe.exercise_id)
        if prev:
            ex_data["last_week"] = prev

            # Overload suggestion
            lw = prev["max_weight"]
            lr = prev["reps"]
            lrir = prev.get("rir")
            if lrir is not None and lrir >= 2 and lr >= pe.target_reps_max:
                new_weight = round(lw * 1.025 / 2.5) * 2.5
                ex_data["suggestion"] = f"Try {new_weight} lbs x {lr}"
            elif lrir is not None and lrir <= 1:
                ex_data["suggestion"] = "Hold weight or reduce reps"
            else:
                ex_data["suggestion"] = None
        else:
            ex_data["last_week"] = None
            ex_data["suggestion"] = None

        ex_list.append(ex_data)

    return {
        **_serialize_planned_session(ps),
        "split_day_name": split_day_name,
        "muscles": muscles,
        "mesocycle_name": meso_name,
        "week_number": week_num,
        "exercises": ex_list,
    }


@router.put("/planned/{id}/exercises")
def update_planned_exercises(
    id: int,
    exercises: list[PlannedExerciseCreate],
    session: Session = Depends(get_session),
):
    ps = session.get(PlannedSession, id)
    if not ps:
        raise HTTPException(status_code=404, detail="Planned session not found")

    # Delete existing
    existing_stmt = select(PlannedExercise).where(PlannedExercise.planned_session_id == id)
    for pe in session.exec(existing_stmt).all():
        session.delete(pe)
    session.commit()

    # Insert new
    for ex_data in exercises:
        pe = PlannedExercise(
            planned_session_id=id,
            exercise_id=ex_data.exercise_id,
            order_in_session=ex_data.order_in_session,
            target_sets=ex_data.target_sets,
            target_reps_min=ex_data.target_reps_min,
            target_reps_max=ex_data.target_reps_max,
            target_rir=ex_data.target_rir,
            notes=ex_data.notes,
        )
        session.add(pe)
    session.commit()

    return {"ok": True, "count": len(exercises)}


@router.post("/planned/{id}/start")
def start_planned_session(id: int, session: Session = Depends(get_session)):
    """Create a WorkoutSession linked to this PlannedSession."""
    ps = session.get(PlannedSession, id)
    if not ps:
        raise HTTPException(status_code=404, detail="Planned session not found")

    # Build auto-name from split day name
    name_parts = []
    if ps.split_day_id:
        sd = session.get(SplitDay, ps.split_day_id)
        if sd:
            name_parts.append(sd.name)

    week = session.get(MesocycleWeek, ps.mesocycle_week_id)
    if week:
        name_parts.append(f"Week {week.week_number}")

    from datetime import date as dt_date
    today = dt_date.today().strftime("%B %d")
    name_parts.append(today)
    session_name = " — ".join(name_parts)

    wk = WorkoutSession(
        user_id=USER_ID,
        name=session_name,
        started_at=datetime.utcnow(),
    )
    session.add(wk)
    session.commit()
    session.refresh(wk)

    ps.session_id = wk.id
    session.add(ps)
    session.commit()

    return {
        "session_id": wk.id,
        "name": wk.name,
        "started_at": wk.started_at.isoformat(),
    }
