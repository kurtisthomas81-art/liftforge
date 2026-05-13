import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import Exercise, ExerciseImportQueue, WorkoutSet

router = APIRouter(prefix="/api/import-queue", tags=["import-queue"])


class ResolvePayload(BaseModel):
    exercise_id: Optional[int] = None
    create: bool = False
    name: Optional[str] = None  # optional rename when creating as new


@router.get("")
def list_queue(db: Session = Depends(get_session)):
    items = db.exec(
        select(ExerciseImportQueue)
        .where(ExerciseImportQueue.status == "pending")
        .order_by(ExerciseImportQueue.created_at)
    ).all()
    return {
        "pending_count": len(items),
        "items": [
            {
                "id": item.id,
                "raw_name": item.raw_name,
                "source": item.source,
                "set_count": len(json.loads(item.pending_sets or "[]")),
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
    }


@router.post("/{item_id}/resolve")
def resolve_item(item_id: int, payload: ResolvePayload, db: Session = Depends(get_session)):
    item = db.get(ExerciseImportQueue, item_id)
    if not item or item.status != "pending":
        raise HTTPException(status_code=404, detail="Queue item not found or already resolved")

    pending_sets = json.loads(item.pending_sets or "[]")

    if payload.exercise_id:
        ex = db.get(Exercise, payload.exercise_id)
        if not ex:
            raise HTTPException(status_code=404, detail="Exercise not found")
        # Auto-add raw_name as alias so future imports never queue it again
        aliases = json.loads(ex.aliases or "[]")
        if item.raw_name.lower() not in {a.lower() for a in aliases}:
            aliases.append(item.raw_name)
            ex.aliases = json.dumps(aliases)
            db.add(ex)
        target_id = ex.id
    elif payload.create:
        name = (payload.name or item.raw_name).strip()
        new_ex = Exercise(name=name, is_custom=True)
        db.add(new_ex)
        db.flush()
        target_id = new_ex.id
    else:
        raise HTTPException(status_code=400, detail="Provide exercise_id or set create=true")

    for s in pending_sets:
        db.add(WorkoutSet(
            session_id=s["session_id"],
            exercise_id=target_id,
            set_number=s["set_number"],
            weight=s.get("weight"),
            reps=s.get("reps", 0),
            set_type=s.get("set_type", "straight"),
        ))

    item.status = "resolved"
    item.resolved_exercise_id = target_id
    db.add(item)
    db.commit()
    return {"ok": True, "sets_imported": len(pending_sets)}


@router.delete("/{item_id}")
def dismiss_item(item_id: int, db: Session = Depends(get_session)):
    item = db.get(ExerciseImportQueue, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    item.status = "dismissed"
    db.add(item)
    db.commit()
    return {"ok": True}
