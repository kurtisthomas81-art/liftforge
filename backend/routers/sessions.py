import json
from typing import Optional
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import (
    WorkoutSession, WorkoutSet, Exercise, WorkoutTemplate, TemplateExercise,
    UserProfile, UserEquipment, Mesocycle, MesocycleWeek, PlannedSession, SplitDay,
    MuscleVolumeLandmark,
)
from engine.meso_builder import (
    _parse_list as _mb_parse, _movement_fatigue, _warmup_sets_needed,
    _apply_secondary_credits, _rest_for_exercise, _fit_to_time,
    _exercise_budget, _select_exercises,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

USER_ID = 1


class SessionCreate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    readiness_rating: Optional[int] = None


class SessionUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    readiness_rating: Optional[int] = None
    post_session_rpe: Optional[int] = None


class SetCreate(BaseModel):
    exercise_id: int
    set_number: int = 1
    weight: Optional[float] = None
    reps: int = 0
    rir: Optional[int] = None
    notes: Optional[str] = None
    set_type: str = "straight"
    superset_group: Optional[int] = None


class SetUpdate(BaseModel):
    exercise_id: Optional[int] = None
    set_number: Optional[int] = None
    weight: Optional[float] = None
    reps: Optional[int] = None
    rir: Optional[int] = None
    notes: Optional[str] = None
    set_type: Optional[str] = None


def _serialize_set(ws: WorkoutSet) -> dict:
    return {
        "id": ws.id,
        "session_id": ws.session_id,
        "exercise_id": ws.exercise_id,
        "set_number": ws.set_number,
        "weight": ws.weight,
        "reps": ws.reps,
        "rir": ws.rir,
        "notes": ws.notes,
        "set_type": ws.set_type,
        "superset_group": ws.superset_group,
    }


def _serialize_session(wk: WorkoutSession) -> dict:
    return {
        "id": wk.id,
        "user_id": wk.user_id,
        "name": wk.name,
        "notes": wk.notes,
        "started_at": wk.started_at.isoformat() if wk.started_at else None,
        "completed_at": wk.completed_at.isoformat() if wk.completed_at else None,
        "readiness_rating": wk.readiness_rating,
        "post_session_rpe": wk.post_session_rpe,
    }


@router.get("")
def list_sessions(
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
):
    offset = (page - 1) * page_size
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .order_by(WorkoutSession.started_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    sessions = session.exec(stmt).all()
    return [_serialize_session(s) for s in sessions]


@router.get("/active")
def get_active_session(session: Session = Depends(get_session)):
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at == None)
        .order_by(WorkoutSession.started_at.desc())
    )
    active = session.exec(stmt).first()
    if not active:
        return None
    return _serialize_session(active)


@router.post("")
def create_session(payload: SessionCreate, session: Session = Depends(get_session)):
    wk = WorkoutSession(
        user_id=USER_ID,
        name=payload.name,
        notes=payload.notes,
        started_at=datetime.utcnow(),
        readiness_rating=payload.readiness_rating,
    )
    session.add(wk)
    session.commit()
    session.refresh(wk)
    return _serialize_session(wk)


@router.post("/generate")
def generate_session(db: Session = Depends(get_session)):
    profile = db.exec(select(UserProfile).where(UserProfile.user_id == USER_ID)).first()
    duration = profile.preferred_session_minutes if profile else 60
    experience_level = getattr(profile, "experience_level", "intermediate") or "intermediate"

    meso = db.exec(
        select(Mesocycle).where(Mesocycle.user_id == USER_ID, Mesocycle.status == "active")
    ).first()
    goal = meso.goal if meso else "hypertrophy"

    reps_by_goal = {"strength": (3, 6), "hypertrophy": (8, 12), "recomp": (10, 15)}
    reps_min, reps_max = reps_by_goal.get(goal, (8, 12))

    # ── Resolve target muscles from today's planned session ───────────────────
    target_muscles: list[str] = []
    if meso:
        today_dow = date.today().weekday()
        week_obj = db.exec(
            select(MesocycleWeek).where(
                MesocycleWeek.mesocycle_id == meso.id,
                MesocycleWeek.week_number == meso.current_week,
            )
        ).first()
        if week_obj:
            planned = db.exec(
                select(PlannedSession).where(
                    PlannedSession.mesocycle_week_id == week_obj.id,
                    PlannedSession.day_of_week == today_dow,
                )
            ).first()
            if planned and planned.split_day_id:
                split_day = db.get(SplitDay, planned.split_day_id)
                if split_day:
                    target_muscles = _mb_parse(split_day.muscle_focus)

    # Fallback: muscles below MAV this week
    if not target_muscles:
        monday = date.today() - timedelta(days=date.today().weekday())
        week_sessions = db.exec(
            select(WorkoutSession).where(
                WorkoutSession.user_id == USER_ID,
                WorkoutSession.started_at >= monday.isoformat(),
            )
        ).all()
        all_sets_week: list = []
        ex_map: dict[int, Exercise] = {}
        for wk_s in week_sessions:
            s_list = db.exec(select(WorkoutSet).where(WorkoutSet.session_id == wk_s.id)).all()
            all_sets_week.extend(s_list)
            for ws in s_list:
                if ws.exercise_id not in ex_map:
                    ex = db.get(Exercise, ws.exercise_id)
                    if ex:
                        ex_map[ws.exercise_id] = ex
        sets_by_muscle: dict[str, int] = {}
        for ws in all_sets_week:
            if ws.set_type == "warmup":
                continue
            ex = ex_map.get(ws.exercise_id)
            if not ex:
                continue
            for m in _mb_parse(ex.primary_muscles):
                sets_by_muscle[m] = sets_by_muscle.get(m, 0) + 1
        landmarks_db = {lm.muscle: lm for lm in db.exec(
            select(MuscleVolumeLandmark).where(MuscleVolumeLandmark.user_id == USER_ID)
        ).all()}
        target_muscles = [m for m, lm in landmarks_db.items() if sets_by_muscle.get(m, 0) < lm.mav_low]

    if not target_muscles:
        target_muscles = ["chest", "back", "shoulders"]

    # ── Available equipment ───────────────────────────────────────────────────
    equip_rows = db.exec(
        select(UserEquipment).where(UserEquipment.user_id == USER_ID, UserEquipment.available == True)
    ).all()
    available_equipment = {r.equipment for r in equip_rows}

    # ── Exercise selection via engine ─────────────────────────────────────────
    all_exercises_db = db.exec(select(Exercise)).all()
    exercises_db = [
        {
            "id": ex.id,
            "name": ex.name,
            "mechanics": ex.mechanics,
            "movement_pattern": ex.movement_pattern or "",
            "force": ex.force or "",
            "primary_muscles": _mb_parse(ex.primary_muscles),
            "secondary_muscles": _mb_parse(ex.secondary_muscles),
            "equipment_required": _mb_parse(ex.equipment_required),
        }
        for ex in all_exercises_db
    ]

    compounds_only = experience_level == "beginner"
    max_per_muscle = 1 if compounds_only else (2 if len(target_muscles) >= 4 else 3)
    time_cap = _exercise_budget(duration, goal)
    max_total = min(time_cap, 4) if compounds_only else time_cap

    selected = _select_exercises(
        target_muscles, available_equipment, exercises_db, goal,
        max_per_muscle=max_per_muscle,
        max_total=max_total,
        compounds_only=compounds_only,
    )

    # ── Assign sets and compute secondary credits ─────────────────────────────
    secondary_credits: dict[str, float] = {}
    activated_muscles: set[str] = set()

    exercise_plan: list[dict] = []
    for ex in selected:
        mechanics = ex.get("mechanics", "isolation")
        target_sets = 4 if mechanics == "compound" else 3

        # Reduce sets for muscles with secondary coverage
        primaries = _mb_parse(ex.get("primary_muscles", []))
        primary = primaries[0] if primaries else None
        if primary:
            credit = secondary_credits.get(primary, 0.0)
            if credit >= target_sets * 0.5:
                target_sets = max(2, target_sets - 1)

        warmup_sets = _warmup_sets_needed(ex, activated_muscles)
        rest_seconds = _rest_for_exercise(ex)

        rmin, rmax = reps_min, reps_max
        if mechanics == "isolation":
            rmin, rmax = max(reps_min, 10), max(reps_max, 15)

        exercise_plan.append({
            **ex,
            "target_sets": target_sets,
            "reps_min": rmin,
            "reps_max": rmax,
            "warmup_sets": warmup_sets,
            "rest_seconds": rest_seconds,
        })

        # Update tracking
        _apply_secondary_credits(ex, secondary_credits, target_sets)
        for m in primaries:
            activated_muscles.add(m)
        for m in _mb_parse(ex.get("secondary_muscles", [])):
            activated_muscles.add(m)

    # ── Fit to time budget (reduce sets, never drop exercises) ────────────────
    exercise_plan = _fit_to_time(exercise_plan, duration, sets_key="target_sets")

    # ── Build session ─────────────────────────────────────────────────────────
    muscles_label = "/".join(m.capitalize() for m in target_muscles[:2])
    session_name = (
        f"{duration}-min {goal.capitalize()} — {muscles_label}"
        if muscles_label else f"{duration}-min {goal.capitalize()}"
    )

    wk = WorkoutSession(user_id=USER_ID, name=session_name, started_at=datetime.utcnow())
    db.add(wk)
    db.commit()
    db.refresh(wk)

    exercises_out = [
        {
            "exercise_id": ex["id"],
            "name": ex["name"],
            "mechanics": ex.get("mechanics", "isolation"),
            "movement_pattern": ex.get("movement_pattern", ""),
            "sets": ex["target_sets"],
            "reps_min": ex["reps_min"],
            "reps_max": ex["reps_max"],
            "warmup_sets": ex["warmup_sets"],
            "rest_seconds": ex["rest_seconds"],
        }
        for ex in exercise_plan
    ]

    return {
        "session_id": wk.id,
        "session_name": session_name,
        "goal": goal,
        "exercises": exercises_out,
    }


@router.patch("/{session_id}")
def update_session(
    session_id: int,
    payload: SessionUpdate,
    session: Session = Depends(get_session),
):
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        raise HTTPException(status_code=404, detail="Session not found")
    if payload.name is not None:
        wk.name = payload.name
    if payload.notes is not None:
        wk.notes = payload.notes
    if payload.readiness_rating is not None:
        wk.readiness_rating = payload.readiness_rating
    if payload.post_session_rpe is not None:
        wk.post_session_rpe = payload.post_session_rpe
    session.add(wk)
    session.commit()
    session.refresh(wk)
    return _serialize_session(wk)


@router.post("/{session_id}/finish")
def finish_session(session_id: int, session: Session = Depends(get_session)):
    from routers.goals import check_goals_for_session
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        raise HTTPException(status_code=404, detail="Session not found")
    wk.completed_at = datetime.utcnow()
    session.add(wk)
    session.commit()
    session.refresh(wk)
    result = _serialize_session(wk)
    result["achieved_goals"] = check_goals_for_session(session_id, session)
    return result


@router.get("/{session_id}")
def get_session_detail(session_id: int, session: Session = Depends(get_session)):
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        raise HTTPException(status_code=404, detail="Session not found")

    sets_stmt = (
        select(WorkoutSet)
        .where(WorkoutSet.session_id == session_id)
        .order_by(WorkoutSet.exercise_id, WorkoutSet.set_number)
    )
    sets = session.exec(sets_stmt).all()

    # Group sets by exercise
    exercise_map: dict[int, dict] = {}
    for ws in sets:
        if ws.exercise_id not in exercise_map:
            ex = session.get(Exercise, ws.exercise_id)
            exercise_map[ws.exercise_id] = {
                "exercise_id": ws.exercise_id,
                "exercise_name": ex.name if ex else "Unknown",
                "superset_group": ws.superset_group,
                "sets": [],
            }
        exercise_map[ws.exercise_id]["sets"].append(_serialize_set(ws))

    data = _serialize_session(wk)
    data["exercises"] = list(exercise_map.values())
    return data


@router.post("/{session_id}/sets")
def add_set(
    session_id: int,
    payload: SetCreate,
    session: Session = Depends(get_session),
):
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        raise HTTPException(status_code=404, detail="Session not found")

    ws = WorkoutSet(
        session_id=session_id,
        exercise_id=payload.exercise_id,
        set_number=payload.set_number,
        weight=payload.weight,
        reps=payload.reps,
        rir=payload.rir,
        notes=payload.notes,
        set_type=payload.set_type,
        superset_group=payload.superset_group,
    )
    session.add(ws)
    session.commit()
    session.refresh(ws)
    return _serialize_set(ws)


@router.put("/{session_id}/sets/{set_id}")
def update_set(
    session_id: int,
    set_id: int,
    payload: SetUpdate,
    session: Session = Depends(get_session),
):
    ws = session.get(WorkoutSet, set_id)
    if not ws or ws.session_id != session_id:
        raise HTTPException(status_code=404, detail="Set not found")
    if payload.exercise_id is not None:
        ws.exercise_id = payload.exercise_id
    if payload.set_number is not None:
        ws.set_number = payload.set_number
    if payload.weight is not None:
        ws.weight = payload.weight
    if payload.reps is not None:
        ws.reps = payload.reps
    if payload.rir is not None:
        ws.rir = payload.rir
    if payload.notes is not None:
        ws.notes = payload.notes
    if payload.set_type is not None:
        ws.set_type = payload.set_type
    session.add(ws)
    session.commit()
    session.refresh(ws)
    return _serialize_set(ws)


@router.delete("/{session_id}/sets/{set_id}")
def delete_set(
    session_id: int,
    set_id: int,
    session: Session = Depends(get_session),
):
    ws = session.get(WorkoutSet, set_id)
    if not ws or ws.session_id != session_id:
        raise HTTPException(status_code=404, detail="Set not found")
    session.delete(ws)
    session.commit()
    return {"ok": True}


class SwapExercisePayload(BaseModel):
    old_exercise_id: int
    new_exercise_id: int


@router.post("/{session_id}/swap-exercise")
def swap_exercise(
    session_id: int,
    payload: SwapExercisePayload,
    session: Session = Depends(get_session),
):
    # Verify session belongs to user without selecting readiness_rating
    exists = session.exec(
        select(WorkoutSession.id).where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == USER_ID,
        )
    ).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Session not found")

    sets = session.exec(
        select(WorkoutSet).where(
            WorkoutSet.session_id == session_id,
            WorkoutSet.exercise_id == payload.old_exercise_id,
        )
    ).all()

    for ws in sets:
        ws.exercise_id = payload.new_exercise_id
        session.add(ws)
    session.commit()
    return {"ok": True, "swapped": len(sets)}


class PairExercisesPayload(BaseModel):
    exercise_ids: list[int]


@router.post("/{session_id}/pair-exercises")
def pair_exercises(
    session_id: int,
    payload: PairExercisesPayload,
    session: Session = Depends(get_session),
):
    if len(payload.exercise_ids) != 2:
        raise HTTPException(status_code=400, detail="Exactly 2 exercise_ids required")
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find next unused superset_group for this session
    existing = session.exec(
        select(WorkoutSet).where(WorkoutSet.session_id == session_id)
    ).all()
    used_groups = {ws.superset_group for ws in existing if ws.superset_group is not None}
    group_id = max(used_groups, default=0) + 1

    for ex_id in payload.exercise_ids:
        sets = session.exec(
            select(WorkoutSet).where(
                WorkoutSet.session_id == session_id,
                WorkoutSet.exercise_id == ex_id,
            )
        ).all()
        for ws in sets:
            ws.superset_group = group_id
            session.add(ws)
    session.commit()
    return {"superset_group": group_id}


@router.delete("/{session_id}/pair-exercises/{group}")
def unpair_exercises(
    session_id: int,
    group: int,
    session: Session = Depends(get_session),
):
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        raise HTTPException(status_code=404, detail="Session not found")

    sets = session.exec(
        select(WorkoutSet).where(
            WorkoutSet.session_id == session_id,
            WorkoutSet.superset_group == group,
        )
    ).all()
    for ws in sets:
        ws.superset_group = None
        session.add(ws)
    session.commit()
    return {"ok": True}


class SaveAsTemplatePayload(BaseModel):
    name: str


@router.post("/{session_id}/save-as-template")
def save_session_as_template(
    session_id: int,
    payload: SaveAsTemplatePayload,
    session: Session = Depends(get_session),
):
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        raise HTTPException(status_code=404, detail="Session not found")

    tpl = WorkoutTemplate(user_id=USER_ID, name=payload.name, notes=wk.notes or "")
    session.add(tpl)
    session.commit()
    session.refresh(tpl)

    # Collect unique exercises in order of first appearance
    sets_stmt = (
        select(WorkoutSet)
        .where(WorkoutSet.session_id == session_id)
        .order_by(WorkoutSet.exercise_id, WorkoutSet.set_number)
    )
    all_sets = session.exec(sets_stmt).all()

    # Group by exercise_id preserving insertion order
    seen: dict[int, list] = {}
    for ws in all_sets:
        seen.setdefault(ws.exercise_id, []).append(ws)

    for order_idx, (exercise_id, ex_sets) in enumerate(seen.items(), start=1):
        working = [s for s in ex_sets if s.set_type != "warmup"]
        set_count = len(working) if working else len(ex_sets)
        te = TemplateExercise(
            template_id=tpl.id,
            exercise_id=exercise_id,
            order_in_template=order_idx,
            target_sets=set_count,
            target_reps_min=8,
            target_reps_max=12,
            target_rir=2,
            notes="",
            superset_group=ex_sets[0].superset_group,
        )
        session.add(te)
    session.commit()

    return {"template_id": tpl.id, "name": tpl.name}


@router.post("/sandbox")
def create_sandbox_session(session: Session = Depends(get_session)):
    """Create a pre-populated test session for UI exploration."""
    SANDBOX_EXERCISES = [
        ("Barbell Bench Press", [
            {"set_type": "warmup", "weight": 95,  "reps": 10},
            {"set_type": "warmup", "weight": 115, "reps": 5},
            {"set_type": "straight", "weight": 135, "reps": 8},
            {"set_type": "straight", "weight": 135, "reps": 8},
            {"set_type": "straight", "weight": 135, "reps": 8},
        ]),
        ("Barbell Back Squat", [
            {"set_type": "warmup", "weight": 135, "reps": 8},
            {"set_type": "warmup", "weight": 155, "reps": 5},
            {"set_type": "straight", "weight": 185, "reps": 5},
            {"set_type": "straight", "weight": 185, "reps": 5},
            {"set_type": "straight", "weight": 185, "reps": 5},
        ]),
        ("Barbell Row", [
            {"set_type": "warmup", "weight": 95, "reps": 10},
            {"set_type": "straight", "weight": 135, "reps": 8},
            {"set_type": "straight", "weight": 135, "reps": 8},
            {"set_type": "straight", "weight": 135, "reps": 8},
        ]),
    ]

    wk = WorkoutSession(user_id=USER_ID, name="[Sandbox] Test Workout", started_at=datetime.utcnow())
    session.add(wk)
    session.commit()
    session.refresh(wk)

    for ex_name, sets in SANDBOX_EXERCISES:
        ex = session.exec(select(Exercise).where(Exercise.name == ex_name)).first()
        if not ex:
            continue
        for i, s in enumerate(sets, start=1):
            ws = WorkoutSet(
                session_id=wk.id,
                exercise_id=ex.id,
                set_number=i,
                weight=s["weight"],
                reps=s["reps"],
                set_type=s["set_type"],
            )
            session.add(ws)

    session.commit()
    return _serialize_session(wk)


@router.delete("/all")
def delete_all_sessions(session: Session = Depends(get_session)):
    all_sessions = session.exec(select(WorkoutSession).where(WorkoutSession.user_id == USER_ID)).all()
    for wk in all_sessions:
        sets = session.exec(select(WorkoutSet).where(WorkoutSet.session_id == wk.id)).all()
        for ws in sets:
            session.delete(ws)
        session.delete(wk)
    session.commit()
    return {"deleted_sessions": len(all_sessions)}


@router.delete("/{session_id}")
def delete_session(session_id: int, session: Session = Depends(get_session)):
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        raise HTTPException(status_code=404, detail="Session not found")
    sets = session.exec(select(WorkoutSet).where(WorkoutSet.session_id == session_id)).all()
    for ws in sets:
        session.delete(ws)
    session.delete(wk)
    session.commit()
    return {"ok": True}
