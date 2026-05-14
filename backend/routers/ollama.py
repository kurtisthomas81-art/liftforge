import os
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
import httpx
from database import get_session
from models import (
    UserProfile, UserEquipment, WorkoutSession, WorkoutSet, Exercise,
    Mesocycle, PersonalRecord, WeeklyCheckin, Injury, BodyMeasurement,
)
from routers.profile import grade_strength_level
from routers.volume import fatigue_report

router = APIRouter(prefix="/api/chat", tags=["chat"])

USER_ID = 1
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

# ── Static knowledge block ─────────────────────────────────────────────────────
# Curated RP methodology facts injected into every prompt.
# This prevents hallucination on core concepts without a retrieval system.

_KNOWLEDGE = """
RP METHODOLOGY REFERENCE (use this to ground your answers — do not recite it verbatim):
• MEV (Minimum Effective Volume): fewest sets/week that produce adaptation. Below this, gains stall.
• MAV (Maximum Adaptive Volume): the target training zone where adaptation is maximized.
• MRV (Maximum Recoverable Volume): the ceiling above which recovery is compromised. Never recommend exceeding MRV.
• RIR (Reps In Reserve) scale: 0 = true failure (never prescribe), 1 = one rep left (high intensity, use sparingly),
  2–3 = hypertrophy zone (ideal for most working sets), 4+ = too easy (increase load or add a set).
• Deload: a planned low-volume week (~50% sets, RIR 4+). Indicated when fatigue score ≥ 6/10,
  3+ muscles at risk, or 4–6 weeks of accumulation without a break.
• Progressive overload via autoregulation (AR): when avg RIR ≤ 1 on working sets across 2 consecutive sessions
  for the same exercise, increase weight next session. Typical increments: hip/knee dominant compounds +10 lbs,
  other compounds +5 lbs, isolations +2.5 lbs.
• Recovery timeline: most muscles need 48–72 h before the next hard session.
  Heavy axial-load compounds (squat, deadlift) need 72 h. Isolations recover faster.
• The fatigue score (0–10) in this app is computed from: per-muscle RIR trends,
  avg session readiness, days since last deload, avg post-session RPE, and weekly check-in data.
  Score ≥ 6 = high fatigue; ≥ 8 = critical. Deload is recommended at ≥ 6.
""".strip()

# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM = f"""You are a personal strength coach assistant for a self-hosted workout tracker app.
You have access to this athlete's complete training data in the context block below.

{_KNOWLEDGE}

RULES — follow these exactly, without exception:
1. Ground every specific recommendation in the athlete's logged data. Before suggesting a weight
   or set/rep change, cite the relevant session: "Your last logged [exercise] was Xwt × Y reps at RIR Z."
2. Never give injury treatment, rehabilitation, or medical advice of any kind.
   If the athlete mentions pain or injury, respond only with:
   "For injury concerns, please consult a sports medicine professional or physiotherapist."
3. Do not suggest abandoning or completely restructuring the current mesocycle mid-block.
   Suggest adjustments within the existing program (modify RIR target, swap an exercise, adjust volume).
4. When the context lacks data to answer a specific question, say "I don't have enough data on that"
   and explain what information would help. Never fabricate numbers.
5. Keep responses concise: 3–5 sentences for simple questions; a short bulleted list for
   programming questions. Do not pad with disclaimers beyond what the rules require.
""".strip()

# ── Context builders ───────────────────────────────────────────────────────────

def _parse_muscles(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return []


def _get_profile_context(session: Session) -> tuple[str, str]:
    """Returns (context_text, units)."""
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == USER_ID)).first()
    if not profile:
        return "No profile data.", "lbs"

    eq_stmt = select(UserEquipment).where(
        UserEquipment.user_id == USER_ID, UserEquipment.available == True
    )
    equipment = session.exec(eq_stmt).all()
    eq_list = ", ".join(e.equipment for e in equipment) if equipment else "standard gym"

    lines = [
        f"Name: {profile.display_name or 'Athlete'} | "
        f"Experience: {(profile.experience_level or 'intermediate').capitalize()} | "
        f"Sex: {(profile.sex or 'male').capitalize()} | "
        f"Units: {profile.unit_preference or 'lbs'}",
        f"Equipment: {eq_list}",
    ]
    return "\n".join(lines), profile.unit_preference or "lbs"


def _get_mesocycle_context(session: Session) -> tuple[str, str | None]:
    """Returns (context_text, short_label_for_summary)."""
    meso = session.exec(
        select(Mesocycle)
        .where(Mesocycle.user_id == USER_ID, Mesocycle.status == "active")
        .order_by(Mesocycle.created_at.desc())
    ).first()

    if not meso:
        return "No active mesocycle.", None

    is_deload = meso.current_week == meso.deload_week
    deload_note = " (THIS IS A DELOAD WEEK — prescribe ~50% volume, RIR 4+)" if is_deload else ""

    label = f"{meso.name} — Week {meso.current_week} of {meso.weeks_total}"
    text = (
        f"Mesocycle: {meso.name} — Week {meso.current_week} of {meso.weeks_total}"
        f"{deload_note}\n"
        f"Goal: {meso.goal.replace('_', ' ').title()} | "
        f"Periodization: {meso.periodization_type.replace('_', ' ').title()} | "
        f"Deload on week: {meso.deload_week}"
    )
    return text, label


def _get_fatigue_context(session: Session) -> tuple[str, float, str]:
    """Returns (context_text, score, overall_fatigue)."""
    try:
        report = fatigue_report(session=session)
    except Exception:
        return "Fatigue data unavailable.", 0.0, "unknown"

    score = report.get("fatigue_score", 0.0)
    overall = report.get("overall_fatigue", "low")
    deload_rec = report.get("deload_recommended", False)
    reasons = report.get("reasons", [])
    at_risk = report.get("muscles_at_risk", [])
    last_deload = report.get("last_deload_days_ago")
    checkin = report.get("checkin")

    lines = [
        f"Score: {score}/10 ({overall}){' — DELOAD RECOMMENDED' if deload_rec else ''}",
    ]
    if at_risk:
        lines.append(f"Muscles at risk (RIR < 1.5 for 3 sessions): {', '.join(at_risk)}")
    if reasons:
        lines.append("Reasons: " + "; ".join(reasons))
    if last_deload is not None:
        lines.append(f"Last deload: {last_deload} days ago")
    if checkin:
        lines.append(
            f"Latest check-in: Energy {checkin['energy']}/5, "
            f"Sleep {checkin['sleep_quality']}/5, "
            f"Stress {checkin['stress']}/5, "
            f"Soreness {checkin['soreness']}/5"
        )

    return "\n".join(lines), score, overall


def _get_strength_context(session: Session) -> str:
    try:
        data = grade_strength_level(session)
    except Exception:
        return "Strength data unavailable."

    overall = data.get("overall_level")
    bw = data.get("body_weight")
    lines = [f"Overall level: {(overall or 'unknown').capitalize()}"]
    if bw:
        lines[0] += f" | Body weight: {bw} lbs"

    for lift in data.get("lifts", []):
        e1rm = lift.get("e1rm")
        level = lift.get("level")
        ratio = lift.get("ratio")
        name = lift.get("exercise_name", lift.get("lift_key", "?"))
        if e1rm is not None:
            ratio_str = f" ({ratio:.2f}× BW)" if ratio else ""
            level_str = f" — {level.capitalize()}" if level else ""
            lines.append(f"{name}: {e1rm} lbs e1RM{ratio_str}{level_str}")
        else:
            lines.append(f"{name}: no PR recorded")

    return "\n".join(lines)


def _get_injury_context(session: Session) -> tuple[str, int]:
    """Returns (context_text, injury_count)."""
    injuries = session.exec(
        select(Injury).where(Injury.user_id == USER_ID, Injury.is_active == True)
    ).all()

    if not injuries:
        return "No active injuries.", 0

    lines = []
    for inj in injuries:
        note = f" ({inj.notes})" if inj.notes else ""
        lines.append(f"{inj.body_part.replace('_', ' ').title()} — {inj.severity}{note}")
    return "Active injuries:\n" + "\n".join(f"  • {l}" for l in lines), len(injuries)


def _get_last_session_context(session: Session) -> str:
    last = session.exec(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID, WorkoutSession.completed_at != None)
        .order_by(WorkoutSession.completed_at.desc())
    ).first()

    if not last:
        return "No completed sessions yet."

    date_str = last.completed_at.strftime("%Y-%m-%d") if last.completed_at else "?"
    lines = [f"Session: {last.name or 'Unnamed'} on {date_str}"]

    sets = session.exec(
        select(WorkoutSet).where(WorkoutSet.session_id == last.id)
    ).all()

    if not sets:
        lines.append("  No sets recorded.")
        return "\n".join(lines)

    by_ex: dict[int, list] = {}
    for ws in sets:
        if ws.set_type == "warmup":
            continue
        by_ex.setdefault(ws.exercise_id, []).append(ws)

    total_weight = 0.0
    for ex_id, ex_sets in by_ex.items():
        ex = session.get(Exercise, ex_id)
        name = ex.name if ex else f"Exercise {ex_id}"
        set_parts = []
        for ws in sorted(ex_sets, key=lambda s: s.set_number):
            if ws.weight and ws.reps:
                part = f"{ws.weight}×{ws.reps}"
                if ws.rir is not None:
                    part += f" RIR {ws.rir}"
                set_parts.append(part)
                total_weight += ws.weight * ws.reps
        if set_parts:
            lines.append(f"  {name}: {', '.join(set_parts)}")

    if last.post_session_rpe is not None:
        lines.append(f"Post-session RPE: {last.post_session_rpe}/10")
    if total_weight > 0:
        lines.append(f"Total weight moved: {round(total_weight):,} lbs")

    return "\n".join(lines)


def _get_recovery_context(session: Session) -> str:
    TRACKED = ["chest", "back", "quads", "hamstrings", "shoulders", "biceps", "triceps", "calves"]
    RECOVERY_HOURS = {"quads": 72, "hamstrings": 72, "back": 72, "chest": 48,
                      "shoulders": 48, "biceps": 48, "triceps": 48, "calves": 24}

    recent = session.exec(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID, WorkoutSession.completed_at != None)
        .order_by(WorkoutSession.completed_at.desc())
        .limit(10)
    ).all()

    if not recent:
        return "No recovery data."

    muscle_last: dict[str, datetime] = {}
    muscle_rir: dict[str, list[float]] = {m: [] for m in TRACKED}

    ex_cache: dict[int, Exercise] = {}
    for wk in recent:
        sets = session.exec(
            select(WorkoutSet).where(WorkoutSet.session_id == wk.id)
        ).all()
        for ws in sets:
            if ws.set_type == "warmup":
                continue
            if ws.exercise_id not in ex_cache:
                ex = session.get(Exercise, ws.exercise_id)
                if ex:
                    ex_cache[ws.exercise_id] = ex
            ex = ex_cache.get(ws.exercise_id)
            if not ex:
                continue
            muscles = _parse_muscles(ex.primary_muscles)
            for m in muscles:
                if m in TRACKED:
                    if m not in muscle_last and wk.completed_at:
                        muscle_last[m] = wk.completed_at
                    if ws.rir is not None and len(muscle_rir[m]) < 3:
                        muscle_rir[m].append(ws.rir)

    now = datetime.utcnow()
    lines = []
    for m in TRACKED:
        last_dt = muscle_last.get(m)
        if not last_dt:
            continue
        hours_ago = (now - last_dt).total_seconds() / 3600
        days_ago = hours_ago / 24
        needed_h = RECOVERY_HOURS.get(m, 48)
        if hours_ago < needed_h * 0.5:
            status = "red (too soon)"
        elif hours_ago < needed_h:
            status = "amber (recovering)"
        else:
            status = "green (ready)"
        rir_vals = muscle_rir[m]
        avg_rir = f"avg RIR {sum(rir_vals)/len(rir_vals):.1f}" if rir_vals else "no RIR data"
        lines.append(f"  {m.capitalize()}: {days_ago:.0f}d ago — {avg_rir} — {status}")

    return "Per-muscle recovery:\n" + ("\n".join(lines) if lines else "  No recent data.")


def _get_active_session_context(session: Session) -> str | None:
    active = session.exec(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == USER_ID, WorkoutSession.completed_at == None)
        .order_by(WorkoutSession.started_at.desc())
    ).first()
    if not active:
        return None

    sets = session.exec(
        select(WorkoutSet).where(WorkoutSet.session_id == active.id)
    ).all()

    if not sets:
        return f"Active session in progress: {active.name or 'Unnamed'} — no sets logged yet."

    by_ex: dict[int, list] = {}
    ex_cache: dict[int, Exercise] = {}
    for ws in sets:
        if ws.set_type == "warmup":
            continue
        by_ex.setdefault(ws.exercise_id, []).append(ws)
        if ws.exercise_id not in ex_cache:
            ex = session.get(Exercise, ws.exercise_id)
            if ex:
                ex_cache[ws.exercise_id] = ex

    lines = [f"Active session in progress: {active.name or 'Unnamed'}"]
    for ex_id, ex_sets in by_ex.items():
        ex = ex_cache.get(ex_id)
        name = ex.name if ex else f"Exercise {ex_id}"
        done = [ws for ws in ex_sets if ws.is_done]
        parts = []
        for ws in sorted(done, key=lambda s: s.set_number):
            if ws.weight and ws.reps:
                p = f"{ws.weight}×{ws.reps}"
                if ws.rir is not None:
                    p += f" RIR {ws.rir}"
                parts.append(p)
        if parts:
            lines.append(f"  {name}: {', '.join(parts)} (done so far)")
    return "\n".join(lines)


# ── Chat endpoint ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context_type: str = "general"


@router.post("")
async def chat(payload: ChatRequest, session: Session = Depends(get_session)):
    # Build all context
    profile_text, units = _get_profile_context(session)
    meso_text, meso_label = _get_mesocycle_context(session)
    fatigue_text, fatigue_score, fatigue_level = _get_fatigue_context(session)
    strength_text = _get_strength_context(session)
    injury_text, injury_count = _get_injury_context(session)
    recovery_text = _get_recovery_context(session)

    # Active session takes priority over last session
    active_ctx = _get_active_session_context(session)
    if active_ctx:
        session_text = active_ctx
    else:
        session_text = _get_last_session_context(session)

    context_block = f"""=== TRAINING CONTEXT ===

ATHLETE PROFILE:
{profile_text}
{injury_text}

CURRENT PROGRAM:
{meso_text}

FATIGUE STATUS:
{fatigue_text}

STRENGTH PROFILE (Big 4 e1RM):
{strength_text}

{'ACTIVE SESSION:' if active_ctx else 'LAST COMPLETED SESSION:'}
{session_text}

MUSCLE RECOVERY:
{recovery_text}

=== END CONTEXT ==="""

    full_prompt = f"{context_block}\n\nAthlete question: {payload.message}"

    context_summary = {
        "mesocycle": meso_label,
        "fatigue_score": fatigue_score,
        "fatigue_level": fatigue_level,
        "injury_count": injury_count,
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "system": _SYSTEM,
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
        print(f"[ollama] unexpected error: {e}")
        reply = "AI coach error — check server logs."

    return {"reply": reply, "context_summary": context_summary}
