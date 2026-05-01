"""
Mesocycle builder engine.

generate_mesocycle() returns a list of week structures, each containing
a list of planned sessions with their planned exercises. The caller
persists these into the database.
"""
import json
import math
from typing import Optional


def _round_to_nearest(value: float, increment: float = 2.5) -> float:
    return round(value / increment) * increment


def _rep_range_for_goal(goal: str, mechanics: str) -> tuple[int, int]:
    """Standard (unchanged) rep range by goal."""
    if goal == "strength":
        return (3, 6)
    if goal == "recomp":
        return (10, 15)
    if mechanics == "compound":
        return (8, 12)
    return (10, 20)


def _rir_for_goal(goal: str, is_deload: bool = False) -> int:
    base = 1 if goal == "strength" else 2
    return base + (1 if is_deload else 0)


# ── Periodization helpers ──────────────────────────────────────────────────────

def _rep_range_linear(goal: str, week_number: int, weeks_total: int) -> tuple[int, int]:
    """Linear: high reps week 1 → low reps final working week."""
    working_weeks = max(weeks_total - 1, 1)  # last week = deload
    progress = min(1.0, (week_number - 1) / max(working_weeks - 1, 1))
    if goal == "strength":
        reps_max = round(10 - progress * 7)   # 10 → 3
        reps_min = round(8 - progress * 5)    # 8 → 3
    else:
        reps_max = round(20 - progress * 12)  # 20 → 8
        reps_min = round(15 - progress * 9)   # 15 → 6
    reps_min = max(3, reps_min)
    reps_max = max(reps_min + 2, reps_max)
    return (reps_min, reps_max)


# DUP: each entry is (reps_min, reps_max, rir, label)
_DUP_PATTERNS: dict[str, list[tuple]] = {
    "hypertrophy": [(8, 12, 2, "Hypertrophy"), (3, 6, 1, "Strength"), (12, 20, 3, "Volume")],
    "strength":    [(3, 6, 1, "Strength"), (6, 10, 2, "Power"), (2, 4, 1, "Peaking")],
    "recomp":      [(10, 15, 2, "Hypertrophy"), (4, 6, 1, "Strength"), (15, 20, 3, "Volume")],
}


def _dup_params(goal: str, day_number: int) -> tuple[int, int, int, str]:
    """Return (reps_min, reps_max, rir, label) for this day in the DUP rotation."""
    pattern = _DUP_PATTERNS.get(goal, _DUP_PATTERNS["hypertrophy"])
    return pattern[(day_number - 1) % len(pattern)]


# Block phases: (reps_min, reps_max, rir, label)
_BLOCK_PHASES = {
    "accumulation":    (12, 20, 3, "Accumulation"),
    "hypertrophy":     (8, 12, 2, "Intensification"),
    "strength":        (3, 6, 1, "Peak"),
}


def _block_phase(week_number: int, weeks_total: int) -> str:
    working_weeks = max(weeks_total - 1, 1)
    progress = (week_number - 1) / max(working_weeks - 1, 1)
    if progress < 0.40:
        return "accumulation"
    if progress < 0.75:
        return "hypertrophy"
    return "strength"


def _select_exercises(
    muscles: list[str],
    available_equipment: set[str],
    exercises_db: list[dict],
    goal: str,
    max_per_muscle: int = 3,
) -> list[dict]:
    """
    For each muscle in the list, pick the best exercises respecting equipment
    and goal. Compounds first, then isolation. Returns de-duped exercise list
    in session order.
    """
    selected_ids: set[int] = set()
    result: list[dict] = []

    for muscle in muscles:
        candidates = [
            ex for ex in exercises_db
            if muscle in ex.get("primary_muscles", [])
            and set(ex.get("equipment_required", [])).issubset(available_equipment)
        ]

        # Sort: compound first, then by id (stable ordering)
        compounds = [e for e in candidates if e.get("mechanics") == "compound"]
        isolations = [e for e in candidates if e.get("mechanics") == "isolation"]

        ordered = compounds + isolations
        count = 0
        for ex in ordered:
            if count >= max_per_muscle:
                break
            if ex["id"] in selected_ids:
                continue
            selected_ids.add(ex["id"])
            result.append(ex)
            count += 1

    return result


def _sets_for_week(mev: int, week_number: int, mrv: int) -> int:
    """Weekly sets for a muscle = MEV + (week-1)*2, capped at MRV."""
    return min(mev + (week_number - 1) * 2, mrv)


def _deload_sets(normal_sets: int, mev: int) -> int:
    return max(mev, normal_sets // 2)


def preview_mesocycle(
    split_template: dict,
    goal: str,
    weeks: int,
    available_equipment: list[str],
    exercises_db: list[dict],
    landmarks: dict,
    periodization_type: str = "standard",
) -> list[dict]:
    """
    Returns per-day exercise selection (week-1 parameters) without persisting.
    Each entry: {"day_index", "day_name", "muscle_focus", "exercises": [...]}
    """
    equip_set = set(available_equipment)
    days = split_template.get("days", [])

    # Sessions per muscle across all days (needed for per-session set calc)
    sessions_per_muscle: dict[str, int] = {}
    for d in days:
        d_muscles = d.get("muscle_focus", [])
        if isinstance(d_muscles, str):
            try:
                d_muscles = json.loads(d_muscles)
            except Exception:
                d_muscles = []
        for m in d_muscles:
            sessions_per_muscle[m] = sessions_per_muscle.get(m, 0) + 1

    result = []
    for idx, day in enumerate(days):
        muscles: list[str] = day.get("muscle_focus", [])
        if isinstance(muscles, str):
            try:
                muscles = json.loads(muscles)
            except Exception:
                muscles = []

        day_muscle_count = len(muscles)
        max_per_muscle = 1 if day_muscle_count >= 7 else (2 if day_muscle_count >= 4 else 3)
        exercises_for_day = _select_exercises(muscles, equip_set, exercises_db, goal, max_per_muscle=max_per_muscle)

        preview_exercises = []
        for ex in exercises_for_day:
            ex_muscles = ex.get("primary_muscles", [])
            if isinstance(ex_muscles, str):
                try:
                    ex_muscles = json.loads(ex_muscles)
                except Exception:
                    ex_muscles = []
            primary = ex_muscles[0] if ex_muscles else None
            lm = landmarks.get(primary, {"mev": 8, "mav_low": 12, "mav_high": 20, "mrv": 22})
            mev = lm.get("mev", 8)
            mrv = lm.get("mrv", 22)
            weekly_sets = _sets_for_week(mev, 1, mrv)
            num_sessions = sessions_per_muscle.get(primary, 1)
            per_session = min(max(2, math.ceil(weekly_sets / num_sessions)), 6)

            mechanics = ex.get("mechanics", "compound")
            if periodization_type == "linear":
                reps_min, reps_max = _rep_range_linear(goal, 1, weeks)
                rir = 3
            elif periodization_type == "dup":
                reps_min, reps_max, rir, _ = _dup_params(goal, day["day_number"])
            elif periodization_type == "block":
                phase = _block_phase(1, weeks)
                reps_min, reps_max, rir, _ = _BLOCK_PHASES[phase]
            else:
                reps_min, reps_max = _rep_range_for_goal(goal, mechanics)
                rir = _rir_for_goal(goal)

            preview_exercises.append({
                "exercise_id": ex["id"],
                "exercise_name": ex["name"],
                "primary_muscle": primary,
                "target_sets": per_session,
                "target_reps_min": reps_min,
                "target_reps_max": reps_max,
                "target_rir": rir,
            })

        result.append({
            "day_index": idx,
            "day_name": day["name"],
            "muscle_focus": muscles,
            "exercises": preview_exercises,
        })

    return result


def generate_mesocycle(
    split_template: dict,
    goal: str,
    weeks: int,
    deload_week: int,
    landmarks: dict,            # muscle -> {"mev", "mav_low", "mav_high", "mrv"}
    available_equipment: list[str],
    exercises_db: list[dict],   # list of dicts with id, name, primary_muscles, mechanics, equipment_required
    periodization_type: str = "standard",
    day_exercises: Optional[dict[int, list[int]]] = None,  # day_index -> [exercise_id, ...]
) -> list[dict]:
    """
    Returns a list of week dicts:
    [
      {
        "week_number": 1,
        "is_deload": False,
        "sessions": [
          {
            "day_number": 1,
            "split_day_name": "Upper A",
            "muscles": [...],
            "exercises": [
              {
                "exercise_id": 3,
                "exercise_name": "...",
                "order_in_session": 1,
                "target_sets": 3,
                "target_reps_min": 8,
                "target_reps_max": 12,
                "target_rir": 2,
                "notes": "",
              },
              ...
            ]
          },
          ...
        ]
      },
      ...
    ]
    """
    equip_set = set(available_equipment)
    days = split_template.get("days", [])
    ex_by_id = {ex["id"]: ex for ex in exercises_db}

    result = []
    for week_num in range(1, weeks + 1):
        is_deload = (week_num == deload_week)
        week_sessions = []

        for day in days:
            muscles: list[str] = day.get("muscle_focus", [])
            if isinstance(muscles, str):
                try:
                    muscles = json.loads(muscles)
                except Exception:
                    muscles = []

            day_idx = day["day_number"] - 1
            if day_exercises and day_idx in day_exercises:
                exercises_for_day = [ex_by_id[eid] for eid in day_exercises[day_idx] if eid in ex_by_id]
            else:
                # Determine max_per_muscle based on how many muscles are in the day
                # Full body days get 1-2 per muscle, focused days get up to 3
                day_muscle_count = len(muscles)
                max_per_muscle = 1 if day_muscle_count >= 7 else (2 if day_muscle_count >= 4 else 3)

                exercises_for_day = _select_exercises(
                    muscles, equip_set, exercises_db, goal, max_per_muscle=max_per_muscle
                )

            # Distribute sets from weekly volume across sessions that hit each muscle
            # Count how many sessions per week hit each muscle
            sessions_per_muscle: dict[str, int] = {}
            for d in days:
                d_muscles = d.get("muscle_focus", [])
                if isinstance(d_muscles, str):
                    try:
                        d_muscles = json.loads(d_muscles)
                    except Exception:
                        d_muscles = []
                for m in d_muscles:
                    sessions_per_muscle[m] = sessions_per_muscle.get(m, 0) + 1

            session_exercises = []
            order = 1
            for ex in exercises_for_day:
                ex_muscles = ex.get("primary_muscles", [])
                if isinstance(ex_muscles, str):
                    try:
                        ex_muscles = json.loads(ex_muscles)
                    except Exception:
                        ex_muscles = []

                # Get landmark for primary muscle
                primary = ex_muscles[0] if ex_muscles else None
                lm = landmarks.get(primary, {"mev": 8, "mav_low": 12, "mav_high": 20, "mrv": 22})
                mev = lm.get("mev", 8)
                mrv = lm.get("mrv", 22)

                # Weekly sets for this muscle in this week
                if is_deload:
                    prev_week_sets = _sets_for_week(mev, week_num - 1, mrv)
                    weekly_sets = _deload_sets(prev_week_sets, mev)
                else:
                    weekly_sets = _sets_for_week(mev, week_num, mrv)

                # Per-session sets = weekly_sets / sessions_per_muscle
                num_sessions = sessions_per_muscle.get(primary, 1)
                per_session = max(2, math.ceil(weekly_sets / num_sessions))
                # Cap per-session sets to reasonable range
                per_session = min(per_session, 6)

                mechanics = ex.get("mechanics", "compound")
                session_label = ""

                if is_deload:
                    reps_min, reps_max = _rep_range_for_goal(goal, mechanics)
                    rir = 3
                elif periodization_type == "linear":
                    reps_min, reps_max = _rep_range_linear(goal, week_num, weeks)
                    progress = (week_num - 1) / max(weeks - 2, 1)
                    rir = max(1, round(3 - min(1.0, progress) * 2))
                elif periodization_type == "dup":
                    reps_min, reps_max, rir, session_label = _dup_params(goal, day["day_number"])
                elif periodization_type == "block":
                    phase = _block_phase(week_num, weeks)
                    reps_min, reps_max, rir, session_label = _BLOCK_PHASES[phase]
                else:  # standard
                    reps_min, reps_max = _rep_range_for_goal(goal, mechanics)
                    rir = _rir_for_goal(goal, is_deload)

                session_exercises.append({
                    "exercise_id": ex["id"],
                    "exercise_name": ex["name"],
                    "order_in_session": order,
                    "target_sets": per_session,
                    "target_reps_min": reps_min,
                    "target_reps_max": reps_max,
                    "target_rir": rir,
                    "notes": session_label,
                })
                order += 1

            week_sessions.append({
                "day_number": day["day_number"],
                "split_day_name": day["name"],
                "split_day_id": day.get("id"),
                "muscles": muscles,
                "exercises": session_exercises,
            })

        result.append({
            "week_number": week_num,
            "is_deload": is_deload,
            "sessions": week_sessions,
        })

    return result
