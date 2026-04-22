import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import WorkoutTemplate, TemplateExercise, Exercise, WorkoutSession, WorkoutSet

router = APIRouter(prefix="/api/templates", tags=["templates"])

USER_ID = 1


# ── Pydantic schemas ────────────────────────────────────────────────────────────

class TemplateExerciseIn(BaseModel):
    exercise_id: int
    order_in_template: int = 1
    target_sets: int = 3
    target_reps_min: int = 8
    target_reps_max: int = 12
    target_rir: int = 2
    notes: str = ""


class TemplateCreate(BaseModel):
    name: str
    notes: str = ""
    exercises: List[TemplateExerciseIn] = []


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    exercises: Optional[List[TemplateExerciseIn]] = None


class SaveAsTemplatePayload(BaseModel):
    name: str


# ── Serializers ─────────────────────────────────────────────────────────────────

def _serialize_template_list(tpl: WorkoutTemplate, exercise_count: int, muscles: list) -> dict:
    return {
        "id": tpl.id,
        "name": tpl.name,
        "notes": tpl.notes,
        "created_at": tpl.created_at.isoformat() if tpl.created_at else None,
        "exercise_count": exercise_count,
        "muscles": muscles,
    }


def _serialize_template_detail(tpl: WorkoutTemplate, te_list: list, session: Session) -> dict:
    exercises_out = []
    muscle_set: set = set()
    for te in te_list:
        ex = session.get(Exercise, te.exercise_id)
        ex_name = ex.name if ex else "Unknown"
        if ex:
            for m in json.loads(ex.primary_muscles):
                muscle_set.add(m)
        exercises_out.append({
            "id": te.id,
            "exercise_id": te.exercise_id,
            "exercise_name": ex_name,
            "order_in_template": te.order_in_template,
            "target_sets": te.target_sets,
            "target_reps_min": te.target_reps_min,
            "target_reps_max": te.target_reps_max,
            "target_rir": te.target_rir,
            "notes": te.notes,
        })
    return {
        "id": tpl.id,
        "name": tpl.name,
        "notes": tpl.notes,
        "created_at": tpl.created_at.isoformat() if tpl.created_at else None,
        "exercise_count": len(exercises_out),
        "muscles": sorted(muscle_set),
        "exercises": exercises_out,
    }


# ── Routes ───────────────────────────────────────────────────────────────────────

@router.get("")
def list_templates(session: Session = Depends(get_session)):
    stmt = select(WorkoutTemplate).where(WorkoutTemplate.user_id == USER_ID).order_by(WorkoutTemplate.created_at.desc())
    templates = session.exec(stmt).all()

    result = []
    for tpl in templates:
        te_stmt = select(TemplateExercise).where(TemplateExercise.template_id == tpl.id)
        te_list = session.exec(te_stmt).all()

        muscle_set: set = set()
        for te in te_list:
            ex = session.get(Exercise, te.exercise_id)
            if ex:
                for m in json.loads(ex.primary_muscles):
                    muscle_set.add(m)

        result.append(_serialize_template_list(tpl, len(te_list), sorted(muscle_set)))
    return result


@router.get("/{template_id}")
def get_template(template_id: int, session: Session = Depends(get_session)):
    tpl = session.get(WorkoutTemplate, template_id)
    if not tpl or tpl.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Template not found")

    te_stmt = (
        select(TemplateExercise)
        .where(TemplateExercise.template_id == template_id)
        .order_by(TemplateExercise.order_in_template)
    )
    te_list = session.exec(te_stmt).all()
    return _serialize_template_detail(tpl, te_list, session)


@router.post("")
def create_template(payload: TemplateCreate, session: Session = Depends(get_session)):
    tpl = WorkoutTemplate(user_id=USER_ID, name=payload.name, notes=payload.notes)
    session.add(tpl)
    session.commit()
    session.refresh(tpl)

    te_list = []
    for idx, ex_in in enumerate(payload.exercises):
        te = TemplateExercise(
            template_id=tpl.id,
            exercise_id=ex_in.exercise_id,
            order_in_template=ex_in.order_in_template if ex_in.order_in_template else idx + 1,
            target_sets=ex_in.target_sets,
            target_reps_min=ex_in.target_reps_min,
            target_reps_max=ex_in.target_reps_max,
            target_rir=ex_in.target_rir,
            notes=ex_in.notes,
        )
        session.add(te)
        te_list.append(te)
    session.commit()

    # Refresh all
    for te in te_list:
        session.refresh(te)
    return _serialize_template_detail(tpl, te_list, session)


@router.put("/{template_id}")
def update_template(template_id: int, payload: TemplateUpdate, session: Session = Depends(get_session)):
    tpl = session.get(WorkoutTemplate, template_id)
    if not tpl or tpl.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Template not found")

    if payload.name is not None:
        tpl.name = payload.name
    if payload.notes is not None:
        tpl.notes = payload.notes
    session.add(tpl)
    session.commit()
    session.refresh(tpl)

    if payload.exercises is not None:
        # Delete old exercises and replace
        old_stmt = select(TemplateExercise).where(TemplateExercise.template_id == template_id)
        old_te = session.exec(old_stmt).all()
        for te in old_te:
            session.delete(te)
        session.commit()

        te_list = []
        for idx, ex_in in enumerate(payload.exercises):
            te = TemplateExercise(
                template_id=tpl.id,
                exercise_id=ex_in.exercise_id,
                order_in_template=ex_in.order_in_template if ex_in.order_in_template else idx + 1,
                target_sets=ex_in.target_sets,
                target_reps_min=ex_in.target_reps_min,
                target_reps_max=ex_in.target_reps_max,
                target_rir=ex_in.target_rir,
                notes=ex_in.notes,
            )
            session.add(te)
            te_list.append(te)
        session.commit()
        for te in te_list:
            session.refresh(te)
    else:
        te_stmt = (
            select(TemplateExercise)
            .where(TemplateExercise.template_id == template_id)
            .order_by(TemplateExercise.order_in_template)
        )
        te_list = session.exec(te_stmt).all()

    return _serialize_template_detail(tpl, te_list, session)


@router.delete("/{template_id}")
def delete_template(template_id: int, session: Session = Depends(get_session)):
    tpl = session.get(WorkoutTemplate, template_id)
    if not tpl or tpl.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Template not found")

    te_stmt = select(TemplateExercise).where(TemplateExercise.template_id == template_id)
    for te in session.exec(te_stmt).all():
        session.delete(te)
    session.delete(tpl)
    session.commit()
    return {"ok": True}


@router.post("/{template_id}/start")
def start_from_template(template_id: int, session: Session = Depends(get_session)):
    tpl = session.get(WorkoutTemplate, template_id)
    if not tpl or tpl.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="Template not found")

    wk = WorkoutSession(
        user_id=USER_ID,
        name=tpl.name,
        started_at=datetime.utcnow(),
    )
    session.add(wk)
    session.commit()
    session.refresh(wk)

    te_stmt = (
        select(TemplateExercise)
        .where(TemplateExercise.template_id == template_id)
        .order_by(TemplateExercise.order_in_template)
    )
    te_list = session.exec(te_stmt).all()

    for te in te_list:
        # Add first placeholder set for each exercise
        ws = WorkoutSet(
            session_id=wk.id,
            exercise_id=te.exercise_id,
            set_number=1,
            reps=0,
            set_type="straight",
        )
        session.add(ws)
    session.commit()

    return {"session_id": wk.id}
