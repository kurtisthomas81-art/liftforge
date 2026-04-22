import os
import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
import httpx
from database import get_session
from models import UserProfile, UserEquipment, WorkoutSession, WorkoutSet, Exercise

router = APIRouter(prefix="/api/chat", tags=["chat"])

USER_ID = 1
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")


class ChatRequest(BaseModel):
    message: str
    context_type: str = "general"  # general | exercise | session


def _get_profile_context(session: Session) -> str:
    stmt = select(UserProfile).where(UserProfile.user_id == USER_ID)
    profile = session.exec(stmt).first()
    if not profile:
        return "units: lbs, experience: intermediate"
    eq_stmt = select(UserEquipment).where(
        UserEquipment.user_id == USER_ID, UserEquipment.available == True
    )
    equipment = session.exec(eq_stmt).all()
    eq_list = ", ".join(e.equipment for e in equipment) if equipment else "standard gym"
    return (
        f"User: {profile.display_name}, units: {profile.unit_preference}, "
        f"experience: {profile.experience_level}, equipment: {eq_list}"
    )


def _get_session_context(session: Session) -> str:
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at == None)
        .order_by(WorkoutSession.started_at.desc())
    )
    active = session.exec(stmt).first()
    if not active:
        return "No active session."

    sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == active.id)
    sets = session.exec(sets_stmt).all()

    if not sets:
        return f"Active session: {active.name or 'Unnamed'} — no sets logged yet."

    exercise_map: dict[int, list] = {}
    for ws in sets:
        exercise_map.setdefault(ws.exercise_id, []).append(ws)

    lines = [f"Active session: {active.name or 'Unnamed'}"]
    for ex_id, ex_sets in exercise_map.items():
        ex = session.get(Exercise, ex_id)
        name = ex.name if ex else f"Exercise {ex_id}"
        set_summaries = [
            f"Set {s.set_number}: {s.weight or 'BW'}x{s.reps}"
            + (f" RIR {s.rir}" if s.rir is not None else "")
            for s in sorted(ex_sets, key=lambda x: x.set_number)
        ]
        lines.append(f"  {name}: {', '.join(set_summaries)}")

    return "\n".join(lines)


def _get_recent_sessions_context(session: Session) -> str:
    stmt = (
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID)
        .where(WorkoutSession.completed_at != None)
        .order_by(WorkoutSession.started_at.desc())
        .limit(3)
    )
    sessions = session.exec(stmt).all()
    if not sessions:
        return "No recent sessions."

    lines = ["Recent sessions:"]
    for wk in sessions:
        sets_stmt = select(WorkoutSet).where(WorkoutSet.session_id == wk.id)
        sets = session.exec(sets_stmt).all()
        lines.append(f"  {wk.started_at.strftime('%Y-%m-%d') if wk.started_at else '?'}: {wk.name or 'Unnamed'} — {len(sets)} sets")

    return "\n".join(lines)


@router.post("")
async def chat(payload: ChatRequest, session: Session = Depends(get_session)):
    profile_ctx = _get_profile_context(session)

    if payload.context_type == "session":
        extra_ctx = _get_session_context(session)
    else:
        extra_ctx = _get_recent_sessions_context(session)

    # Extract units and experience for system prompt
    stmt = select(UserProfile).where(UserProfile.user_id == USER_ID)
    profile = session.exec(stmt).first()
    units = profile.unit_preference if profile else "lbs"
    experience = profile.experience_level if profile else "intermediate"

    system_prompt = (
        f"You are a knowledgeable hypertrophy coach. You understand RP Strength methodology, "
        f"volume landmarks (MEV/MAV/MRV), RIR-based autoregulation, and evidence-based training. "
        f"Give concise, actionable advice. User trains with {units}. Experience: {experience}."
    )

    full_prompt = (
        f"{profile_ctx}\n\n{extra_ctx}\n\nUser question: {payload.message}"
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "system": system_prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            reply = data.get("response", "No response from model.")
    except httpx.ConnectError:
        reply = "AI coach is offline. Check that Ollama is running on your host."
    except httpx.TimeoutException:
        reply = "AI coach timed out. The model may be loading — try again in a moment."
    except Exception as e:
        reply = "AI coach is offline. Check that Ollama is running on your host."

    return {"reply": reply}
