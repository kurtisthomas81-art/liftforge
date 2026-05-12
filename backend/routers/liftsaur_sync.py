import re
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import UserProfile, WorkoutSession, WorkoutSet, Exercise

router = APIRouter(prefix="/api/liftsaur", tags=["liftsaur"])

USER_ID = 1
LIFTOSAUR_BASE = "https://www.liftosaur.com/api/v1"
DEFAULT_SESSION_NAME = "Imported Workout"


class TokenRequest(BaseModel):
    token: str


def _get_profile(session: Session) -> UserProfile:
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == USER_ID)).first()
    if not profile:
        profile = UserProfile(user_id=USER_ID)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def _parse_record(text: str) -> dict | None:
    # Format: "2026-04-24 16:48:59 +00:00" (space separator, timezone offset)
    date_match = re.match(r'(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})', text)
    if not date_match:
        return None
    try:
        started_at = datetime.fromisoformat(f"{date_match.group(1)}T{date_match.group(2)}")
    except ValueError:
        return None

    day_match = re.search(r'dayName:\s*"([^"]+)"', text)
    prog_match = re.search(r'program:\s*"([^"]+)"', text)
    session_name = (
        day_match.group(1) if day_match
        else prog_match.group(1) if prog_match
        else DEFAULT_SESSION_NAME
    )

    ex_block_match = re.search(r'exercises:\s*\{(.+)\}', text, re.DOTALL)
    exercises = []
    if ex_block_match:
        block = ex_block_match.group(1)
        for ex_text in re.split(r'\s*\|\s*|\n', block):
            ex_text = ex_text.strip()
            if not ex_text:
                continue
            parts = [p.strip() for p in ex_text.split(' / ')]
            if not parts:
                continue

            ex_name = parts[0].split(',')[0].strip()
            if not ex_name:
                continue

            sets = []
            set_number = 1
            for part in parts[1:]:
                part = part.strip()
                if part.startswith(('warmup:', 'target:')):
                    continue
                # Each part may be comma-separated individual sets: "1x5 180lb, 1x3 205lb"
                for set_str in re.split(r',\s*', part):
                    set_str = set_str.strip()
                    if not set_str:
                        continue
                    m = re.match(r'(\d+)x(\d+)\s+([\d.]+)lb', set_str)
                    if m:
                        count = int(m.group(1))
                        reps = int(m.group(2))
                        weight = float(m.group(3))
                        for _ in range(count):
                            sets.append({'set_number': set_number, 'reps': reps, 'weight': weight})
                            set_number += 1

            if sets:
                exercises.append({'name': ex_name, 'sets': sets})

    return {'started_at': started_at, 'session_name': session_name, 'exercises': exercises}


def _fetch_all_history(token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    records = []
    cursor = None

    with httpx.Client(timeout=30) as client:
        while True:
            params = {"limit": 200}
            if cursor is not None:
                params["cursor"] = cursor

            resp = client.get(f"{LIFTOSAUR_BASE}/history", headers=headers, params=params)
            if resp.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Liftosaur API token")
            if resp.status_code == 403:
                raise HTTPException(status_code=403, detail="Liftosaur premium subscription required")
            resp.raise_for_status()

            body = resp.json()
            data = body.get("data", {})
            for rec in data.get("records", []):
                parsed = _parse_record(rec.get("text", ""))
                if parsed:
                    records.append(parsed)

            if not data.get("hasMore"):
                break
            cursor = data.get("nextCursor")
            if cursor is None:
                break

    return records


def _resolve_exercise(name: str, session: Session, ex_cache: dict) -> tuple[Exercise, bool]:
    """Returns (exercise, is_newly_created)."""
    key = name.lower()
    if key in ex_cache:
        return ex_cache[key], False

    new_ex = Exercise(name=name, is_custom=True)
    session.add(new_ex)
    session.flush()
    ex_cache[key] = new_ex
    return new_ex, True


@router.put("/token")
def save_token(body: TokenRequest, session: Session = Depends(get_session)):
    profile = _get_profile(session)
    profile.liftsaur_api_token = body.token or None
    session.add(profile)
    session.commit()
    return {"ok": True}


@router.get("/token")
def token_status(session: Session = Depends(get_session)):
    profile = _get_profile(session)
    return {"connected": bool(profile.liftsaur_api_token)}


@router.post("/sync")
def sync_liftosaur(session: Session = Depends(get_session)):
    profile = _get_profile(session)
    if not profile.liftsaur_api_token:
        raise HTTPException(status_code=400, detail="No Liftosaur token saved")

    records = _fetch_all_history(profile.liftsaur_api_token)

    # Pre-populate exercise cache — one query, zero per-miss scans
    ex_cache: dict[str, Exercise] = {
        ex.name.lower(): ex
        for ex in session.exec(select(Exercise)).all()
    }

    # Pre-load existing session keys for O(1) duplicate detection
    existing_keys: set[tuple[str, str]] = {
        (ws.started_at.date().isoformat(), ws.name or "")
        for ws in session.exec(
            select(WorkoutSession).where(WorkoutSession.user_id == USER_ID)
        ).all()
        if ws.started_at
    }

    imported_sessions = 0
    skipped_sessions = 0
    imported_sets = 0
    new_exercise_names: set[str] = set()

    for rec in records:
        key = (rec["started_at"].date().isoformat(), rec["session_name"])
        if key in existing_keys:
            skipped_sessions += 1
            continue

        ws = WorkoutSession(
            user_id=USER_ID,
            name=rec["session_name"],
            started_at=rec["started_at"],
            completed_at=rec["started_at"] + timedelta(hours=1),
            source="liftosaur",
        )
        session.add(ws)
        session.flush()
        existing_keys.add(key)
        imported_sessions += 1

        for ex_data in rec["exercises"]:
            ex, is_new = _resolve_exercise(ex_data["name"], session, ex_cache)
            if is_new:
                new_exercise_names.add(ex.name)

            for s in ex_data["sets"]:
                session.add(WorkoutSet(
                    session_id=ws.id,
                    exercise_id=ex.id,
                    set_number=s["set_number"],
                    weight=s["weight"],
                    reps=s["reps"],
                ))
                imported_sets += 1

    session.commit()

    return {
        "imported_sessions": imported_sessions,
        "imported_sets": imported_sets,
        "skipped_sessions": skipped_sessions,
        "new_exercises": list(new_exercise_names),
    }


@router.delete("/imported")
def clear_imported(session: Session = Depends(get_session)):
    """Delete all Liftosaur-imported sessions and their sets."""
    imported = session.exec(
        select(WorkoutSession).where(
            WorkoutSession.user_id == USER_ID,
            WorkoutSession.source == "liftosaur",
        )
    ).all()
    deleted = 0
    for ws in imported:
        sets = session.exec(select(WorkoutSet).where(WorkoutSet.session_id == ws.id)).all()
        for s in sets:
            session.delete(s)
        session.delete(ws)
        deleted += 1
    session.commit()
    return {"deleted_sessions": deleted}
