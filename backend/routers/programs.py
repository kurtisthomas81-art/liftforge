import json
import re
from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import (
    SplitTemplate, SplitDay,
    Mesocycle, MesocycleWeek, PlannedSession, PlannedExercise,
    WorkoutSession, WorkoutSet, Exercise, UserEquipment, MuscleVolumeLandmark,
    UserProfile, Injury,
)

router = APIRouter(prefix="/api/programs", tags=["programs"])

USER_ID = 1


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_injury_exclusions(db: Session) -> tuple[set, set]:
    """Return (excluded_patterns, excluded_muscles) based on the user's active injuries."""
    from engine.meso_builder import INJURY_EXCLUDED_PATTERNS, INJURY_EXCLUDED_MUSCLES
    injuries = db.exec(
        select(Injury).where(Injury.user_id == USER_ID, Injury.is_active == True)
    ).all()
    excluded_patterns: set = set()
    excluded_muscles: set = set()
    for inj in injuries:
        excluded_patterns |= INJURY_EXCLUDED_PATTERNS.get(inj.body_part, set())
        excluded_muscles  |= INJURY_EXCLUDED_MUSCLES.get(inj.body_part, set())
    return excluded_patterns, excluded_muscles


def _parse_variant(name: str):
    """Extract trailing A/B/C variant letter from a split day name.
    'Full Body A' → ('Full Body', 'A');  'Push' → ('Push', None)"""
    m = re.match(r'^(.*?)\s+([A-C])$', name or '')
    if m:
        return m.group(1), m.group(2)
    return (name or ''), None


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
    except (json.JSONDecodeError, TypeError):
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
        "num_variants": m.num_variants,
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
        "superset_group": pe.superset_group,
        "set_technique": pe.set_technique or "straight",
    }


# ── Program presets ────────────────────────────────────────────────────────────

@router.get("/presets")
def get_program_presets():
    """Return quick-start program style presets for the mesocycle wizard."""
    from program_presets import PROGRAM_PRESETS
    return PROGRAM_PRESETS


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
    periodization_type: str = "standard"  # standard|linear|dup|block
    session_minutes: Optional[int] = None
    # Optional exercise overrides from wizard preview (day_index -> [exercise_id, ...])
    day_exercises: Optional[dict[str, list[int]]] = None
    num_variants: int = 2   # 1=no variation, 2=A/B, 3=A/B/C
    session_mode: str = "auto"  # "auto" | "custom_slots"
    custom_slot_sessions: Optional[list[dict]] = None  # [{day_name, slots, slot_exercises, variant}]


class MesocycleUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


class SlotValidationPayload(BaseModel):
    slots: list[str]
    equipment: Optional[list[str]] = None
    goal: str = "hypertrophy"
    experience_level: str = "intermediate"


class CustomSlotPreviewPayload(BaseModel):
    sessions: list[dict]   # [{day_name: str, slots: [str], variant: str}]
    goal: str = "hypertrophy"
    equipment: Optional[list[str]] = None
    experience_level: str = "intermediate"
    num_variants: int = 2


class PlannedExerciseCreate(BaseModel):
    exercise_id: int
    order_in_session: int = 1
    target_sets: int
    target_reps_min: int
    target_reps_max: int
    target_rir: int = 2
    notes: str = ""
    superset_group: Optional[int] = None
    set_technique: str = "straight"


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
                    superset_group=ex_data.get("superset_group"),
                    set_technique=ex_data.get("set_technique", "straight"),
                )
                session.add(pe)
            session.commit()


def _resolve_meso_resources(payload: MesocycleCreate, session: Session) -> tuple:
    """Return (template, days, template_data, user_equipment, landmarks, exercises_db, experience_level)."""
    template = None
    days = []

    if payload.split_slug:
        stmt = select(SplitTemplate).where(SplitTemplate.slug == payload.split_slug)
        template = session.exec(stmt).first()
        if not template:
            raise HTTPException(status_code=404, detail="Split template not found")
        days_stmt = select(SplitDay).where(SplitDay.template_id == template.id)
        days = sorted(session.exec(days_stmt).all(), key=lambda d: d.day_number)

    if not template and not payload.custom_days:
        raise HTTPException(status_code=400, detail="split_slug or custom_days required")

    eq_stmt = select(UserEquipment).where(
        UserEquipment.user_id == USER_ID,
        UserEquipment.available == True,
    )
    user_equipment = [e.equipment for e in session.exec(eq_stmt).all()]
    if not user_equipment:
        user_equipment = ["bodyweight", "dumbbells", "barbell", "bench", "rack", "cable_machine", "machine"]

    lm_stmt = select(MuscleVolumeLandmark).where(MuscleVolumeLandmark.user_id == USER_ID)
    landmarks_raw = session.exec(lm_stmt).all()
    landmarks = {
        lm.muscle: {"mev": lm.mev, "mav_low": lm.mav_low, "mav_high": lm.mav_high, "mrv": lm.mrv}
        for lm in landmarks_raw
    }

    all_exercises = session.exec(select(Exercise)).all()
    exercises_db = []
    for ex in all_exercises:
        try:
            pm = json.loads(ex.primary_muscles)
        except (json.JSONDecodeError, TypeError):
            pm = []
        try:
            sm = json.loads(ex.secondary_muscles) if ex.secondary_muscles else []
        except (json.JSONDecodeError, TypeError):
            sm = []
        try:
            eq = json.loads(ex.equipment_required)
        except (json.JSONDecodeError, TypeError):
            eq = []
        exercises_db.append({
            "id": ex.id,
            "name": ex.name,
            "primary_muscles": pm,
            "secondary_muscles": sm,
            "mechanics": ex.mechanics,
            "equipment_required": eq,
            "movement_pattern": ex.movement_pattern or "",
            "force": ex.force or "",
            "sub_pattern": ex.sub_pattern or "",
        })

    if template:
        template_data = {
            "split_type": template.split_type,
            "days": [
                {"day_number": d.day_number, "id": d.id, "name": d.name, "muscle_focus": d.muscle_focus}
                for d in days
            ]
        }
    else:
        template_data = {
            "split_type": "custom",
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

    profile = session.exec(select(UserProfile).where(UserProfile.user_id == USER_ID)).first()
    experience_level = profile.experience_level if profile else "intermediate"

    return template, days, template_data, user_equipment, landmarks, exercises_db, experience_level


@router.post("/mesocycles/validate-slots")
def validate_slot_list(payload: SlotValidationPayload, session: Session = Depends(get_session)):
    """Return per-slot prescriptions, warnings, balance info, and estimated session time."""
    from engine.meso_builder import PATTERN_PRESCRIPTION, _rep_set_for_pattern, COMPOUND_SET_SECONDS, REST_COMPOUND, REST_ISOLATION, ISOLATION_SET_SECONDS

    all_exercises = session.exec(select(Exercise)).all()
    available = set(payload.equipment) if payload.equipment else {
        "bodyweight", "dumbbells", "barbell", "bench", "rack", "cable_machine", "machine"
    }

    SLOT_MUSCLES = {
        "knee_dominant":   ["quads", "glutes", "hamstrings"],
        "hip_dominant":    ["hamstrings", "glutes", "lower_back"],
        "horizontal_push": ["chest", "triceps", "shoulders"],
        "vertical_push":   ["shoulders", "triceps"],
        "horizontal_pull": ["back", "lats", "biceps"],
        "vertical_pull":   ["lats", "biceps"],
        "core":            ["abs", "core"],
        "":                [],
    }
    SLOT_FATIGUE = {sp: rx["fatigue"] for sp, rx in PATTERN_PRESCRIPTION.items()}

    is_beginner = payload.experience_level == "beginner"
    warnings = []
    slot_details = []
    push_count = 0
    pull_count = 0
    muscle_coverage: list[str] = []
    total_minutes = 10  # warmup reserve

    axial_slots = [s for s in payload.slots if s in ("knee_dominant", "hip_dominant")]
    if len(axial_slots) > 1:
        warnings.append({
            "type": "axial_overload",
            "message": "Two high-fatigue compounds (e.g. squat + deadlift) in one session — high CNS demand. Consider splitting across days.",
            "severity": "warning",
        })

    for slot in payload.slots:
        sets, reps_min, reps_max, rir = _rep_set_for_pattern(slot, payload.goal, is_beginner, 1, 5)
        fatigue = SLOT_FATIGUE.get(slot, "low")
        rest = REST_COMPOUND if fatigue in ("high", "medium") else REST_ISOLATION
        set_time = COMPOUND_SET_SECONDS if fatigue in ("high", "medium") else ISOLATION_SET_SECONDS
        est_minutes = round((sets * (set_time + rest)) / 60)
        total_minutes += est_minutes

        muscles = SLOT_MUSCLES.get(slot, [])
        for m in muscles:
            if m not in muscle_coverage:
                muscle_coverage.append(m)

        if slot in ("horizontal_push", "vertical_push"):
            push_count += 1
        if slot in ("horizontal_pull", "vertical_pull"):
            pull_count += 1

        slot_details.append({
            "slot": slot,
            "prescription": {"sets": sets, "reps_min": reps_min, "reps_max": reps_max, "rir": rir},
            "estimated_minutes": est_minutes,
            "primary_muscles_covered": muscles,
        })

    if abs(push_count - pull_count) > 1:
        warnings.append({
            "type": "push_pull_imbalance",
            "message": f"Push: {push_count} compound(s), Pull: {pull_count} compound(s) — aim for a 1:1 ratio.",
            "severity": "warning",
        })

    return {
        "warnings": warnings,
        "slots": slot_details,
        "push_pull_balance": {"push": push_count, "pull": pull_count, "balanced": abs(push_count - pull_count) <= 1},
        "total_estimated_minutes": total_minutes,
        "muscle_coverage": muscle_coverage,
    }


@router.post("/mesocycles/preview-custom-slots")
def preview_custom_slots(payload: CustomSlotPreviewPayload, session: Session = Depends(get_session)):
    """Return exercise assignments for user-defined slot lists. Same shape as /mesocycles/preview."""
    from engine.meso_builder import (
        _select_session_exercises, _select_for_slot, _rep_set_for_pattern,
        _warmup_sets_needed, _rest_for_exercise, _fit_to_time,
        _apply_secondary_credits, _parse_list,
    )

    all_exercises = session.exec(select(Exercise)).all()
    exercises_db = []
    for ex in all_exercises:
        try:
            pm = json.loads(ex.primary_muscles)
        except (json.JSONDecodeError, TypeError):
            pm = []
        try:
            sm = json.loads(ex.secondary_muscles) if ex.secondary_muscles else []
        except (json.JSONDecodeError, TypeError):
            sm = []
        try:
            eq = json.loads(ex.equipment_required)
        except (json.JSONDecodeError, TypeError):
            eq = []
        exercises_db.append({
            "id": ex.id, "name": ex.name, "primary_muscles": pm, "secondary_muscles": sm,
            "mechanics": ex.mechanics, "equipment_required": eq,
            "movement_pattern": ex.movement_pattern or "",
            "force": ex.force or "", "sub_pattern": ex.sub_pattern or "",
        })

    ex_by_id = {ex["id"]: ex for ex in exercises_db}
    available = set(payload.equipment) if payload.equipment else {
        "bodyweight", "dumbbells", "barbell", "bench", "rack", "cable_machine", "machine"
    }
    is_beginner = payload.experience_level == "beginner"
    result = []

    for sess_def in payload.sessions:
        slots = sess_def.get("slots", [])
        slot_exercise_ids = sess_def.get("slot_exercises", [])
        variant = sess_def.get("variant", "A")
        day_name = sess_def.get("day_name", "Custom")

        # Build per-slot exercises respecting any pinned IDs
        exercises_for_day = []
        selected_ids: set[int] = set()
        variant_index = {"A": 0, "B": 1, "C": 2}.get(variant, 0)
        for i, slot in enumerate(slots):
            pinned_id = slot_exercise_ids[i] if i < len(slot_exercise_ids) else None
            if pinned_id and pinned_id in ex_by_id:
                ex = ex_by_id[pinned_id]
                exercises_for_day.append(ex)
                selected_ids.add(ex["id"])
            else:
                ex = _select_for_slot(slot, available, exercises_db, selected_ids,
                                      payload.experience_level, variant_index)
                if ex:
                    exercises_for_day.append(ex)
                    selected_ids.add(ex["id"])

        activated_muscles: set[str] = set()
        secondary_credits: dict[str, float] = {}
        preview_exercises = []

        for ex in exercises_for_day:
            primaries = _parse_list(ex.get("primary_muscles", []))
            primary = primaries[0] if primaries else None
            sub_pattern = ex.get("sub_pattern", "")
            sets, reps_min, reps_max, rir = _rep_set_for_pattern(sub_pattern, payload.goal, is_beginner, 1, 5)
            warmup_sets = _warmup_sets_needed(ex, activated_muscles)
            rest_seconds = _rest_for_exercise(ex)

            preview_exercises.append({
                "exercise_id": ex["id"], "exercise_name": ex["name"],
                "primary_muscle": primary, "mechanics": ex.get("mechanics", "compound"),
                "movement_pattern": ex.get("movement_pattern", ""), "sub_pattern": sub_pattern,
                "target_sets": sets, "target_reps_min": reps_min, "target_reps_max": reps_max,
                "target_rir": rir, "warmup_sets": warmup_sets, "rest_seconds": rest_seconds,
            })
            for m in primaries:
                activated_muscles.add(m)
            _apply_secondary_credits(ex, secondary_credits, sets)

        result.append({
            "day_name": day_name, "variant": variant, "slots": slots, "exercises": preview_exercises,
        })

    from engine.balance_checker import check_program_balance
    return {"sessions": result, "balance": check_program_balance(result)}


@router.post("/mesocycles/preview")
def preview_mesocycle_endpoint(payload: MesocycleCreate, session: Session = Depends(get_session)):
    from engine.meso_builder import preview_mesocycle
    from engine.balance_checker import check_program_balance
    _, _, template_data, user_equipment, landmarks, exercises_db, experience_level = _resolve_meso_resources(payload, session)
    excluded_patterns, excluded_muscles = _get_injury_exclusions(session)
    sessions = preview_mesocycle(
        split_template=template_data,
        goal=payload.goal,
        weeks=payload.weeks,
        available_equipment=user_equipment,
        exercises_db=exercises_db,
        landmarks=landmarks,
        periodization_type=payload.periodization_type,
        session_minutes=payload.session_minutes,
        experience_level=experience_level,
        num_variants=payload.num_variants,
        excluded_patterns=excluded_patterns,
        excluded_muscles=excluded_muscles,
    )
    return {"sessions": sessions, "balance": check_program_balance(sessions)}


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

    template, days, template_data, user_equipment, landmarks, exercises_db, experience_level = _resolve_meso_resources(payload, session)

    days_lookup: dict[int, int] = {d.day_number: d.id for d in days}
    if template:
        days_per_week = template.days_per_week
    else:
        days_per_week = len(payload.custom_days)

    deload_week = payload.weeks
    start = payload.start_date or date.today().isoformat()

    name = payload.name
    if not name:
        from datetime import datetime as dt
        now = dt.utcnow()
        name = f"Mesocycle {now.strftime('%B %Y')}"

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
        periodization_type=payload.periodization_type,
        num_variants=payload.num_variants,
        session_counter=0,
    )
    session.add(meso)
    session.commit()
    session.refresh(meso)

    day_exercises_override = None
    if payload.day_exercises:
        day_exercises_override = {int(k): v for k, v in payload.day_exercises.items()}

    excluded_patterns, excluded_muscles = _get_injury_exclusions(session)
    weeks_data = generate_mesocycle(
        split_template=template_data,
        goal=payload.goal,
        weeks=payload.weeks,
        deload_week=deload_week,
        landmarks=landmarks,
        available_equipment=user_equipment,
        exercises_db=exercises_db,
        periodization_type=payload.periodization_type,
        day_exercises=day_exercises_override,
        session_minutes=payload.session_minutes,
        experience_level=experience_level,
        num_variants=payload.num_variants,
        session_mode=payload.session_mode,
        custom_slot_sessions=payload.custom_slot_sessions,
        excluded_patterns=excluded_patterns,
        excluded_muscles=excluded_muscles,
    )

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

            base_name, variant = _parse_variant(split_day_name)
            sessions_out.append({
                **_serialize_planned_session(ps),
                "split_day_name": split_day_name,
                "base_session_name": base_name,
                "variant": variant if meso.num_variants > 1 else None,
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


@router.get("/mesocycles/{id}/adherence")
def get_mesocycle_adherence(id: int, session: Session = Depends(get_session)):
    meso = session.get(Mesocycle, id)
    if not meso or meso.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Mesocycle not found")

    weeks_stmt = select(MesocycleWeek).where(
        MesocycleWeek.mesocycle_id == meso.id
    ).order_by(MesocycleWeek.week_number)
    weeks = session.exec(weeks_stmt).all()

    total_planned = 0
    total_completed = 0
    weeks_out = []

    for week in weeks:
        ps_stmt = select(PlannedSession).where(PlannedSession.mesocycle_week_id == week.id)
        planned = session.exec(ps_stmt).all()
        planned_count = len(planned)
        completed_count = sum(1 for ps in planned if ps.session_id is not None)
        total_planned += planned_count
        total_completed += completed_count
        weeks_out.append({
            "week_number": week.week_number,
            "is_deload": week.is_deload,
            "planned": planned_count,
            "completed": completed_count,
            "pct": round(completed_count / planned_count * 100) if planned_count else 0,
        })

    overall_pct = round(total_completed / total_planned * 100) if total_planned else 0
    return {
        "overall": {"planned": total_planned, "completed": total_completed, "pct": overall_pct},
        "weeks": weeks_out,
        "current_week": meso.current_week,
    }


@router.get("/mesocycles/{id}/review")
def get_mesocycle_review(id: int, session: Session = Depends(get_session)):
    from routers.volume import _parse_muscles

    meso = session.get(Mesocycle, id)
    if not meso or meso.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Mesocycle not found")

    weeks_stmt = select(MesocycleWeek).where(
        MesocycleWeek.mesocycle_id == id
    ).order_by(MesocycleWeek.week_number)
    weeks = session.exec(weeks_stmt).all()

    exercise_cache: dict[int, Exercise] = {}
    total_planned = 0
    total_completed = 0
    week_muscle_sets: list[dict] = []   # one dict per week: {muscle: set_count}
    week_muscle_rir: list[dict] = []    # one dict per week: {muscle: [rir values]}

    for week in weeks:
        ps_list = session.exec(
            select(PlannedSession).where(PlannedSession.mesocycle_week_id == week.id)
        ).all()
        total_planned += len(ps_list)
        total_completed += sum(1 for ps in ps_list if ps.session_id)

        muscle_sets: dict[str, int] = {}
        muscle_rir: dict[str, list] = {}
        for ps in ps_list:
            if not ps.session_id:
                continue
            sets = session.exec(
                select(WorkoutSet).where(WorkoutSet.session_id == ps.session_id)
            ).all()
            for ws in sets:
                if ws.set_type == "warmup":
                    continue
                if ws.exercise_id not in exercise_cache:
                    ex = session.get(Exercise, ws.exercise_id)
                    if ex:
                        exercise_cache[ws.exercise_id] = ex
                ex = exercise_cache.get(ws.exercise_id)
                if not ex:
                    continue
                for m in _parse_muscles(ex.primary_muscles):
                    muscle_sets[m] = muscle_sets.get(m, 0) + 1
                    if ws.rir is not None:
                        muscle_rir.setdefault(m, []).append(ws.rir)
        week_muscle_sets.append(muscle_sets)
        week_muscle_rir.append(muscle_rir)

    landmarks = {
        lm.muscle: lm for lm in session.exec(
            select(MuscleVolumeLandmark).where(MuscleVolumeLandmark.user_id == USER_ID)
        ).all()
    }

    all_muscles: set[str] = set()
    for wms in week_muscle_sets:
        all_muscles.update(wms.keys())

    muscles_out = []
    for muscle in sorted(all_muscles):
        # Per-week set counts (all weeks including deload)
        sets_per_week = [wms.get(muscle, 0) for wms in week_muscle_sets]

        # Non-deload weeks only for averages
        non_deload = [
            wms.get(muscle, 0)
            for wms, wk in zip(week_muscle_sets, weeks)
            if not wk.is_deload
        ]
        avg_sets = round(sum(non_deload) / len(non_deload), 1) if non_deload else 0
        peak_sets = max(non_deload) if non_deload else 0

        # RIR trend: early (first half) vs late (second half)
        all_rir = [r for wrir in week_muscle_rir for r in wrir.get(muscle, [])]
        if len(all_rir) < 2:
            avg_rir_early = None
            avg_rir_late = None
        else:
            half = len(all_rir) // 2
            avg_rir_early = round(sum(all_rir[:half]) / half, 1)
            avg_rir_late = round(sum(all_rir[half:]) / (len(all_rir) - half), 1)

        lm = landmarks.get(muscle)
        suggestion = None
        suggested_mrv = None
        suggested_mev = None
        if lm and len(non_deload) >= 2:
            weeks_above_mav = sum(1 for c in non_deload if c > lm.mav_high)
            weeks_below_mev = sum(1 for c in non_deload if 0 < c < lm.mev)
            if weeks_above_mav >= len(non_deload) // 2:
                suggestion = "raise_mrv"
                suggested_mrv = peak_sets + 2
            elif weeks_below_mev >= len(non_deload) // 2:
                suggestion = "lower_mev"
                suggested_mev = max(1, round(avg_sets) - 1)

        muscles_out.append({
            "muscle": muscle,
            "sets_per_week": sets_per_week,
            "avg_sets_per_week": avg_sets,
            "peak_sets_per_week": peak_sets,
            "avg_rir_early": avg_rir_early,
            "avg_rir_late": avg_rir_late,
            "landmark": {
                "mev": lm.mev, "mav_low": lm.mav_low,
                "mav_high": lm.mav_high, "mrv": lm.mrv,
            } if lm else None,
            "suggestion": suggestion,
            "suggested_mrv": suggested_mrv,
            "suggested_mev": suggested_mev,
        })

    adherence_pct = round(total_completed / total_planned * 100) if total_planned else 0
    return {
        "mesocycle_id": id,
        "name": meso.name,
        "goal": meso.goal,
        "weeks_total": meso.weeks_total,
        "adherence": {
            "pct": adherence_pct,
            "planned": total_planned,
            "completed": total_completed,
        },
        "muscles": muscles_out,
        "weeks": [{"week_number": wk.week_number, "is_deload": wk.is_deload} for wk in weeks],
    }


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

            base_name, variant = _parse_variant(split_day_name)
            sessions_out.append({
                **_serialize_planned_session(ps),
                "split_day_name": split_day_name,
                "base_session_name": base_name,
                "variant": variant if meso.num_variants > 1 else None,
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

def _ar_increment(sub_pattern: str, max_weight: float) -> float:
    """Movement-based fixed increment with a 1%-of-weight floor."""
    if sub_pattern == "hip_dominant":
        fixed = 10.0
    elif sub_pattern == "knee_dominant":
        fixed = 5.0
    else:
        fixed = 2.5
    if max_weight > 0 and fixed / max_weight < 0.01:
        fixed = round(max_weight * 0.025 / 2.5) * 2.5
    return fixed


def _compute_ar(exercise_id: int, db: Session) -> dict:
    """Return AR suggestion if avg RIR ≤ 1 in both of the last 2 completed sessions."""
    sets_stmt = (
        select(WorkoutSet, WorkoutSession)
        .join(WorkoutSession, WorkoutSet.session_id == WorkoutSession.id)
        .where(
            WorkoutSet.exercise_id == exercise_id,
            WorkoutSet.set_type == "straight",
            WorkoutSet.rir.isnot(None),
            WorkoutSession.completed_at.isnot(None),
        )
        .order_by(WorkoutSession.id.desc())
    )
    rows = db.exec(sets_stmt).all()

    # Group into distinct sessions (preserve order, newest first)
    sessions_seen: list[int] = []
    sets_by_session: dict[int, list] = {}
    for ws, _ in rows:
        if ws.session_id not in sets_by_session:
            sessions_seen.append(ws.session_id)
            sets_by_session[ws.session_id] = []
        sets_by_session[ws.session_id].append(ws)

    if len(sessions_seen) < 2:
        return {"ar_triggered": False, "ar_suggested_weight": None}

    for sid in sessions_seen[:2]:
        s_sets = sets_by_session[sid]
        if not s_sets:
            return {"ar_triggered": False, "ar_suggested_weight": None}
        avg_rir = sum(ws.rir for ws in s_sets) / len(s_sets)
        if avg_rir > 1.0:
            return {"ar_triggered": False, "ar_suggested_weight": None}

    # Both sessions had avg RIR ≤ 1 — compute bump from most recent session
    recent_sets = sets_by_session[sessions_seen[0]]
    max_weight = max((ws.weight or 0) for ws in recent_sets)
    if max_weight <= 0:
        return {"ar_triggered": False, "ar_suggested_weight": None}

    ex = db.get(Exercise, exercise_id)
    increment = _ar_increment(ex.sub_pattern if ex else "", max_weight)
    suggested = round((max_weight + increment) / 2.5) * 2.5
    return {"ar_triggered": True, "ar_suggested_weight": suggested}


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
            except (json.JSONDecodeError, TypeError):
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
                increment = _ar_increment(ex.sub_pattern if ex else "", lw)
                new_weight = round((lw + increment) / 2.5) * 2.5
                ex_data["suggestion"] = f"Try {new_weight} lbs x {lr}"
            elif lrir is not None and lrir <= 1:
                ex_data["suggestion"] = "Hold weight or reduce reps"
            else:
                ex_data["suggestion"] = None
        else:
            ex_data["last_week"] = None
            ex_data["suggestion"] = None

        ar = _compute_ar(pe.exercise_id, session)
        ex_data["ar_triggered"] = ar["ar_triggered"]
        ex_data["ar_suggested_weight"] = ar["ar_suggested_weight"]

        ex_list.append(ex_data)

    base_name, variant = _parse_variant(split_day_name)
    return {
        **_serialize_planned_session(ps),
        "split_day_name": split_day_name,
        "base_session_name": base_name,
        "variant": variant if (meso and meso.num_variants > 1) else None,
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
            superset_group=ex_data.superset_group,
            set_technique=ex_data.set_technique,
        )
        session.add(pe)
    session.commit()

    return {"ok": True, "count": len(exercises)}


# ── Published program library ──────────────────────────────────────────────────

@router.get("/library")
def list_library(session: Session = Depends(get_session)):
    from published_programs import PROGRAMS
    return list(PROGRAMS.values())


@router.get("/library/{slug}/preview")
def preview_library_program(slug: str, session: Session = Depends(get_session)):
    """Return program metadata + week-1 session templates with resolved exercise names/IDs."""
    from published_programs import PROGRAMS, build_schedule

    prog = PROGRAMS.get(slug)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")

    all_exercises = session.exec(select(Exercise)).all()
    exercise_lookup = {ex.name: ex.id for ex in all_exercises}
    id_to_name = {ex.id: ex.name for ex in all_exercises}

    weeks_data = build_schedule(slug, exercise_lookup)

    # Collect unique session types from week 1 (representative template)
    seen_labels: set[str] = set()
    session_types = []
    for w in weeks_data:
        if w["is_deload"]:
            continue
        for s in w["sessions"]:
            label = s["split_day_name"]
            if label not in seen_labels:
                seen_labels.add(label)
                session_types.append({
                    "label": label,
                    "exercises": [
                        {
                            "exercise_id": e["exercise_id"],
                            "exercise_name": id_to_name.get(e["exercise_id"], e.get("exercise_name", "")),
                            "sets": e["target_sets"],
                            "reps_min": e["target_reps_min"],
                            "reps_max": e["target_reps_max"],
                            "rir": e["target_rir"],
                            "notes": e.get("notes", ""),
                        }
                        for e in s["exercises"]
                    ],
                })

    return {
        **{k: prog[k] for k in ("slug", "name", "author", "description", "goal", "difficulty", "days_per_week", "weeks", "deload_week", "day_slots")},
        "session_types": session_types,
    }


@router.get("/library/{slug}/sessions")
def library_template_sessions(slug: str, session: Session = Depends(get_session)):
    """Return unique (non-deload) session templates with sub_pattern per exercise — used by the builder pre-load flow."""
    from published_programs import PROGRAMS, build_schedule

    prog = PROGRAMS.get(slug)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")

    all_exercises = session.exec(select(Exercise)).all()
    exercise_lookup = {ex.name: ex.id for ex in all_exercises}
    id_to_ex = {ex.id: ex for ex in all_exercises}

    weeks_data = build_schedule(slug, exercise_lookup)

    seen_labels: set[str] = set()
    sessions_out = []
    for w in weeks_data:
        if w["is_deload"]:
            continue
        for s in w["sessions"]:
            label = s["split_day_name"]
            if label in seen_labels:
                continue
            seen_labels.add(label)
            exercises = []
            for e in s["exercises"]:
                ex_obj = id_to_ex.get(e["exercise_id"])
                exercises.append({
                    "exercise_id": e["exercise_id"],
                    "exercise_name": e.get("exercise_name", ex_obj.name if ex_obj else ""),
                    "sub_pattern": ex_obj.sub_pattern if ex_obj else "",
                    "target_sets": e["target_sets"],
                    "target_reps_min": e["target_reps_min"],
                    "target_reps_max": e["target_reps_max"],
                    "target_rir": e["target_rir"],
                    "notes": e.get("notes", ""),
                })
            sessions_out.append({"label": label, "exercises": exercises})

    return {
        "slug": prog["slug"],
        "name": prog["name"],
        "goal": prog["goal"],
        "weeks": prog["weeks"],
        "days_per_week": prog["days_per_week"],
        "sessions": sessions_out,
    }


class LibraryInstallPayload(BaseModel):
    weeks: Optional[int] = None
    deload_week: Optional[int] = None
    day_slots: Optional[list[int]] = None
    session_overrides: Optional[dict] = None  # label → list of {exercise_id, sets, reps_min, reps_max, rir, notes}


@router.post("/library/{slug}/install")
def install_library_program(slug: str, payload: LibraryInstallPayload = LibraryInstallPayload(), db: Session = Depends(get_session)):
    from published_programs import PROGRAMS, build_schedule

    prog = PROGRAMS.get(slug)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")

    weeks_count = payload.weeks or prog["weeks"]
    deload_wk = payload.deload_week or prog["deload_week"]
    day_slots = payload.day_slots or prog["day_slots"]
    deload_wk = min(deload_wk, weeks_count)

    # Deactivate any existing active mesocycles
    active_stmt = select(Mesocycle).where(
        Mesocycle.user_id == USER_ID,
        Mesocycle.status == "active",
    )
    for old in db.exec(active_stmt).all():
        old.status = "abandoned"
        db.add(old)
    db.commit()

    all_exercises = db.exec(select(Exercise)).all()
    exercise_lookup = {ex.name: ex.id for ex in all_exercises}

    # Build base schedule then apply overrides and week-count adjustments
    base_weeks = build_schedule(slug, exercise_lookup)
    weeks_data = _apply_library_overrides(base_weeks, weeks_count, deload_wk, payload.session_overrides)

    meso = Mesocycle(
        user_id=USER_ID,
        name=prog["name"],
        split_template_id=None,
        weeks_total=weeks_count,
        current_week=1,
        status="active",
        goal=prog["goal"],
        start_date=date.today().isoformat(),
        deload_week=deload_wk,
        periodization_type="standard",
        created_at=datetime.utcnow(),
    )
    db.add(meso)
    db.commit()
    db.refresh(meso)

    _build_planned_sessions(meso.id, weeks_data, day_slots, db, {})

    return _serialize_mesocycle(meso)


def _apply_library_overrides(
    base_weeks: list[dict],
    weeks_count: int,
    deload_week: int,
    session_overrides: Optional[dict],
) -> list[dict]:
    """Extend/trim the schedule to weeks_count and apply exercise overrides."""
    import copy

    # Get working-week templates (non-deload)
    working = [w for w in base_weeks if not w["is_deload"]]
    if not working:
        working = base_weeks

    result = []
    for w_num in range(1, weeks_count + 1):
        is_deload = (w_num == deload_week)
        template = working[(w_num - 1) % len(working)]
        week = copy.deepcopy(template)
        week["week_number"] = w_num
        week["is_deload"] = is_deload

        if session_overrides:
            for sess in week["sessions"]:
                label = sess["split_day_name"]
                if label in session_overrides:
                    new_exs = session_overrides[label]
                    sess["exercises"] = [
                        {
                            "exercise_id": e["exercise_id"],
                            "exercise_name": e.get("exercise_name", ""),
                            "order_in_session": i + 1,
                            "target_sets": max(2, e["sets"] // 2) if is_deload else e["sets"],
                            "target_reps_min": e["reps_min"],
                            "target_reps_max": e["reps_max"],
                            "target_rir": min(4, e["rir"] + 2) if is_deload else e["rir"],
                            "notes": (e.get("notes", "") + " (Deload)").strip() if is_deload else e.get("notes", ""),
                        }
                        for i, e in enumerate(new_exs)
                    ]

        if is_deload and not session_overrides:
            # Scale default exercises for deload
            for sess in week["sessions"]:
                for ex in sess["exercises"]:
                    ex["target_sets"] = max(2, ex["target_sets"] // 2)
                    ex["target_rir"] = min(4, ex["target_rir"] + 2)

        result.append(week)

    return result


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

    # Increment mesocycle session counter (drives A/B/C variant tracking)
    if week:
        meso = session.get(Mesocycle, week.mesocycle_id)
        if meso:
            meso.session_counter = (meso.session_counter or 0) + 1
            session.add(meso)

    session.commit()

    return {
        "session_id": wk.id,
        "name": wk.name,
        "started_at": wk.started_at.isoformat(),
    }
