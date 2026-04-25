import re
import httpx
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import UserProfile, WorkoutSession, WorkoutSet, Exercise

router = APIRouter(prefix="/api/liftsaur", tags=["liftsaur"])

USER_ID = 1
LIFTOSAUR_BASE = "https://www.liftosaur.com/api/v1"


# ── Request/response models ────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    token: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_profile(session: Session) -> UserProfile:
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == USER_ID)).first()
    if not profile:
        profile = UserProfile(user_id=USER_ID)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def _parse_record(text: str) -> dict | None:
    """Parse one Liftosaur history record text into structured data."""
    # Date at the start: 2026-03-01T10:00:00Z
    date_match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', text)
    if not date_match:
        return None
    try:
        started_at = datetime.fromisoformat(date_match.group(1))
    except ValueError:
        return None

    # Session name: prefer dayName, fall back to program name
    day_match = re.search(r'dayName:\s*"([^"]+)"', text)
    prog_match = re.search(r'program:\s*"([^"]+)"', text)
    session_name = (
        day_match.group(1) if day_match
        else prog_match.group(1) if prog_match
        else "Imported Workout"
    )

    # Exercises block: exercises: { ... }
    ex_block_match = re.search(r'exercises:\s*\{(.+)\}', text, re.DOTALL)
    exercises = []
    if ex_block_match:
        block = ex_block_match.group(1)
        # Exercises may be separated by " | " or newlines
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
                # Summary: "3x5 185lb"
                summary = re.match(r'(\d+)x(\d+)\s+([\d.]+)lb', part)
                if summary:
                    count = int(summary.group(1))
                    reps = int(summary.group(2))
                    weight = float(summary.group(3))
                    for _ in range(count):
                        sets.append({'set_number': set_number, 'reps': reps, 'weight': weight})
                        set_number += 1
                    continue
                # Individual: "5 185lb" or "185lb x5"
                ind = re.match(r'(\d+)\s+([\d.]+)lb', part) or re.match(r'([\d.]+)lb\s*x(\d+)', part)
                if ind:
                    reps, weight = int(ind.group(1)), float(ind.group(2))
                    sets.append({'set_number': set_number, 'reps': reps, 'weight': weight})
                    set_number += 1

            if sets:
                exercises.append({'name': ex_name, 'sets': sets})

    return {'started_at': started_at, 'session_name': session_name, 'exercises': exercises}


def _fetch_all_history(token: str) -> list[dict]:
    """Fetch all history pages from Liftosaur, return list of parsed records."""
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


def _resolve_exercise(name: str, session: Session, ex_cache: dict) -> Exercise:
    """Find existing exercise by name (case-insensitive) or create a custom one."""
    key = name.lower()
    if key in ex_cache:
        return ex_cache[key]

    all_exercises = session.exec(select(Exercise)).all()
    for ex in all_exercises:
        if ex.name.lower() == key:
            ex_cache[key] = ex
            return ex

    new_ex = Exercise(name=name, is_custom=True)
    session.add(new_ex)
    session.commit()
    session.refresh(new_ex)
    ex_cache[key] = new_ex
    return new_ex


def _session_exists(started_at: datetime, name: str, db: Session) -> bool:
    date_str = started_at.date().isoformat()
    existing = db.exec(
        select(WorkoutSession).where(WorkoutSession.user_id == USER_ID)
    ).all()
    for ws in existing:
        if ws.started_at and ws.started_at.date().isoformat() == date_str and ws.name == name:
            return True
    return False


# ── Endpoints ──────────────────────────────────────────────────────────────────

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

    imported_sessions = 0
    skipped_sessions = 0
    imported_sets = 0
    new_exercise_names: list[str] = []
    ex_cache: dict[str, Exercise] = {}

    for rec in records:
        if _session_exists(rec["started_at"], rec["session_name"], session):
            skipped_sessions += 1
            continue

        ws = WorkoutSession(
            user_id=USER_ID,
            name=rec["session_name"],
            started_at=rec["started_at"],
            completed_at=rec["started_at"] + timedelta(hours=1),
        )
        session.add(ws)
        session.commit()
        session.refresh(ws)
        imported_sessions += 1

        for ex_data in rec["exercises"]:
            before_count = len(ex_cache)
            ex = _resolve_exercise(ex_data["name"], session, ex_cache)
            if len(ex_cache) > before_count and ex.name not in new_exercise_names:
                new_exercise_names.append(ex.name)

            for s in ex_data["sets"]:
                wset = WorkoutSet(
                    session_id=ws.id,
                    exercise_id=ex.id,
                    set_number=s["set_number"],
                    weight=s["weight"],
                    reps=s["reps"],
                )
                session.add(wset)
                imported_sets += 1

        session.commit()

    return {
        "imported_sessions": imported_sessions,
        "imported_sets": imported_sets,
        "skipped_sessions": skipped_sessions,
        "new_exercises": new_exercise_names,
    }
