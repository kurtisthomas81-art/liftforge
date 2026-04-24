import json
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import WorkoutSession, WorkoutSet, Exercise, WorkoutTemplate, TemplateExercise

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
    wk = session.get(WorkoutSession, session_id)
    if not wk:
        raise HTTPException(status_code=404, detail="Session not found")
    wk.completed_at = datetime.utcnow()
    session.add(wk)
    session.commit()
    session.refresh(wk)
    return _serialize_session(wk)


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
        )
        session.add(te)
    session.commit()

    return {"template_id": tpl.id, "name": tpl.name}
