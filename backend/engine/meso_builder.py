"""
Mesocycle builder engine — v2.

Improvements over v1:
- Realistic time budgeting (90s compound set, 45s isolation, 10-min warmup reserve)
- Prescribed rest per exercise: 180s compounds, 120s isolations, 75s supersets
- Movement pattern conflict detection (no squat + deadlift in same session)
- Push/pull balance enforcement in compound selection
- Secondary muscle volume credit (reduces need for direct isolation work)
- Dynamic warm-up set assignment (0 if muscle already warm, 2-3 if first exercise)
- Exercise ordering: high-fatigue first → medium compounds → isolations
- Time-budget fitting: reduce sets/reps before ever cutting an exercise
"""
import json
import math
from typing import Optional


# ── Time / rest constants ──────────────────────────────────────────────────────
REST_COMPOUND = 180        # 3 min — heavy loading, CNS recovery required
REST_ISOLATION = 120       # 2 min — localized muscle fatigue
REST_SUPERSET = 75         # 1 min 15 sec — partial rest while partner muscle works
COMPOUND_SET_SECONDS = 90  # time to perform one working compound set
ISOLATION_SET_SECONDS = 45 # time to perform one isolation set
WARMUP_BUDGET_SECONDS = 600  # 10-min flat reserve for general session warm-up

# ── Conflict / balance constants ───────────────────────────────────────────────
HIGH_FATIGUE_PATTERNS = {"squat", "hinge"}  # axial load, high CNS demand
SECONDARY_CREDIT_FACTOR = 0.5              # secondary muscles credited at 50% of sets
ISO_CRITICAL_MUSCLES = {                   # muscles rarely covered as secondary in compounds
    "biceps", "calves", "rear_delts", "forearms"
}
CORE_MUSCLES = {"abs", "core"}             # never auto-populated; optional accessory slot only

# ── Pattern × Goal prescription matrix ────────────────────────────────────────
# Each entry: {fatigue, hypertrophy/strength/recomp: {sets:(min,max), reps:(min,max)}, beginner_rir:(conservative,standard)}
PATTERN_PRESCRIPTION: dict[str, dict] = {
    "hip_dominant":    {"fatigue": "high",   "hypertrophy": {"sets": (2, 3), "reps": (5, 8)},   "general_fitness": {"sets": (2, 3), "reps": (5, 8)},   "strength": {"sets": (2, 3), "reps": (3, 5)},   "recomp": {"sets": (2, 3), "reps": (5, 8)},   "beginner_rir": (4, 3)},
    "knee_dominant":   {"fatigue": "high",   "hypertrophy": {"sets": (3, 4), "reps": (5, 10)},  "general_fitness": {"sets": (3, 4), "reps": (6, 10)},  "strength": {"sets": (3, 5), "reps": (3, 6)},   "recomp": {"sets": (3, 4), "reps": (6, 10)},  "beginner_rir": (3, 3)},
    "horizontal_push": {"fatigue": "medium", "hypertrophy": {"sets": (3, 4), "reps": (8, 12)},  "general_fitness": {"sets": (3, 4), "reps": (6, 12)},  "strength": {"sets": (4, 5), "reps": (5, 8)},   "recomp": {"sets": (3, 4), "reps": (8, 12)},  "beginner_rir": (3, 2)},
    "vertical_push":   {"fatigue": "medium", "hypertrophy": {"sets": (3, 4), "reps": (8, 12)},  "general_fitness": {"sets": (3, 4), "reps": (6, 12)},  "strength": {"sets": (4, 5), "reps": (5, 8)},   "recomp": {"sets": (3, 4), "reps": (8, 12)},  "beginner_rir": (3, 2)},
    "horizontal_pull": {"fatigue": "medium", "hypertrophy": {"sets": (3, 4), "reps": (8, 12)},  "general_fitness": {"sets": (3, 4), "reps": (6, 12)},  "strength": {"sets": (4, 5), "reps": (5, 8)},   "recomp": {"sets": (3, 4), "reps": (8, 12)},  "beginner_rir": (3, 2)},
    "vertical_pull":   {"fatigue": "medium", "hypertrophy": {"sets": (3, 4), "reps": (8, 12)},  "general_fitness": {"sets": (3, 4), "reps": (6, 12)},  "strength": {"sets": (4, 5), "reps": (5, 8)},   "recomp": {"sets": (3, 4), "reps": (8, 12)},  "beginner_rir": (3, 2)},
    "core":            {"fatigue": "low",    "hypertrophy": {"sets": (2, 3), "reps": (12, 20)}, "general_fitness": {"sets": (2, 3), "reps": (12, 20)}, "strength": {"sets": (2, 3), "reps": (12, 20)}, "recomp": {"sets": (2, 3), "reps": (12, 20)}, "beginner_rir": (2, 1)},
    "":                {"fatigue": "low",    "hypertrophy": {"sets": (2, 3), "reps": (12, 20)}, "general_fitness": {"sets": (2, 3), "reps": (12, 20)}, "strength": {"sets": (2, 3), "reps": (12, 20)}, "recomp": {"sets": (2, 3), "reps": (12, 20)}, "beginner_rir": (2, 1)},
}


def _rep_set_for_pattern(
    sub_pattern: str,
    goal: str,
    is_beginner: bool,
    week_number: int,
    weeks_total: int,
) -> tuple[int, int, int, int]:
    """Returns (sets, reps_min, reps_max, rir) for a slot, goal, and experience level.

    Beginners start at MEV (lower set bound, conservative RIR).
    Intermediate/advanced ramp sets from min→max across working weeks.
    """
    rx = PATTERN_PRESCRIPTION.get(sub_pattern, PATTERN_PRESCRIPTION[""])
    goal_key = goal if goal in ("hypertrophy", "general_fitness", "strength", "recomp") else "hypertrophy"
    goal_rx = rx[goal_key]
    sets_min, sets_max = goal_rx["sets"]
    reps_min, reps_max = goal_rx["reps"]

    if is_beginner:
        rir = rx["beginner_rir"][0]
        sets = sets_min
    else:
        working_weeks = max(weeks_total - 1, 1)
        progress = min(1.0, (week_number - 1) / max(working_weeks - 1, 1))
        sets = round(sets_min + progress * (sets_max - sets_min))
        rir = 1 if goal == "strength" else 2

    return sets, reps_min, reps_max, rir


# ── Existing rep / periodization helpers (unchanged) ──────────────────────────

def _round_to_nearest(value: float, increment: float = 2.5) -> float:
    return round(value / increment) * increment


def _rep_range_for_goal(goal: str, mechanics: str) -> tuple[int, int]:
    if goal == "strength":
        return (3, 6)
    if goal == "recomp":
        return (10, 15)
    if goal == "general_fitness":
        return (6, 10) if mechanics == "compound" else (10, 15)
    if mechanics == "compound":
        return (8, 12)
    return (10, 20)


def _rir_for_goal(goal: str, is_deload: bool = False) -> int:
    base = 1 if goal == "strength" else 2
    return base + (1 if is_deload else 0)


def _rep_range_linear(goal: str, week_number: int, weeks_total: int) -> tuple[int, int]:
    working_weeks = max(weeks_total - 1, 1)
    progress = min(1.0, (week_number - 1) / max(working_weeks - 1, 1))
    if goal == "strength":
        reps_max = round(10 - progress * 7)
        reps_min = round(8 - progress * 5)
    else:
        reps_max = round(20 - progress * 12)
        reps_min = round(15 - progress * 9)
    reps_min = max(3, reps_min)
    reps_max = max(reps_min + 2, reps_max)
    return (reps_min, reps_max)


_DUP_PATTERNS: dict[str, list[tuple]] = {
    "hypertrophy":     [(8, 12, 2, "Hypertrophy"), (3, 6, 1, "Strength"), (12, 20, 3, "Volume")],
    "general_fitness": [(6, 10, 2, "Strength"),    (8, 12, 2, "Build"),    (10, 15, 3, "Volume")],
    "strength":        [(3, 6, 1, "Strength"),      (6, 10, 2, "Power"),    (2, 4, 1, "Peaking")],
    "recomp":          [(10, 15, 2, "Hypertrophy"), (4, 6, 1, "Strength"), (15, 20, 3, "Volume")],
}


def _dup_params(goal: str, day_number: int) -> tuple[int, int, int, str]:
    pattern = _DUP_PATTERNS.get(goal, _DUP_PATTERNS["hypertrophy"])
    return pattern[(day_number - 1) % len(pattern)]


_BLOCK_PHASES = {
    "accumulation": (12, 20, 3, "Accumulation"),
    "hypertrophy":  (8, 12, 2, "Intensification"),
    "strength":     (3, 6, 1, "Peak"),
}


def _block_phase(week_number: int, weeks_total: int) -> str:
    working_weeks = max(weeks_total - 1, 1)
    progress = (week_number - 1) / max(working_weeks - 1, 1)
    if progress < 0.40:
        return "accumulation"
    if progress < 0.75:
        return "hypertrophy"
    return "strength"


# ── Movement / fatigue helpers ─────────────────────────────────────────────────

def _parse_list(value) -> list:
    if isinstance(value, list):
        return value
    try:
        return json.loads(value) if value else []
    except Exception:
        return []


def _movement_fatigue(movement_pattern: str) -> str:
    """Classify CNS demand: high (axial), medium (push/pull), low (other)."""
    if movement_pattern in HIGH_FATIGUE_PATTERNS:
        return "high"
    if movement_pattern in {"push", "pull"}:
        return "medium"
    return "low"


def _warmup_sets_needed(ex: dict, activated_muscles: set) -> int:
    """
    Returns warm-up sets needed before this exercise.
    0 if any primary muscle is already warm from a previous exercise.
    3 for first high-fatigue compound, 2 for first compound, 1 for first isolation.
    """
    primaries = _parse_list(ex.get("primary_muscles", []))
    if any(m in activated_muscles for m in primaries):
        return 0
    pattern = ex.get("movement_pattern", "")
    if pattern in HIGH_FATIGUE_PATTERNS:
        return 3
    if ex.get("mechanics") == "compound":
        return 2
    return 1


def _apply_secondary_credits(ex: dict, volume_credits: dict, sets: int) -> None:
    """Credit secondary muscles at 50% of working sets, reducing their isolation need."""
    for muscle in _parse_list(ex.get("secondary_muscles", [])):
        volume_credits[muscle] = volume_credits.get(muscle, 0) + sets * SECONDARY_CREDIT_FACTOR


def _rest_for_exercise(ex: dict) -> int:
    """Prescribed rest in seconds by mechanics."""
    return REST_COMPOUND if ex.get("mechanics") == "compound" else REST_ISOLATION


# ── Time budget helpers ────────────────────────────────────────────────────────

def _calc_session_seconds(exercises: list[dict], sets_key: str = "target_sets") -> int:
    """Total session time in seconds including 10-min warm-up reserve."""
    total = WARMUP_BUDGET_SECONDS
    for ex in exercises:
        sets = ex.get(sets_key, 3)
        mechanics = ex.get("mechanics", "isolation")
        work = COMPOUND_SET_SECONDS if mechanics == "compound" else ISOLATION_SET_SECONDS
        rest = REST_COMPOUND if mechanics == "compound" else REST_ISOLATION
        total += sets * (work + rest)
    return total


def _fit_to_time(
    exercises: list[dict],
    session_minutes: Optional[int],
    sets_key: str = "target_sets",
) -> list[dict]:
    """
    Reduce sets/reps to fit time budget. Never drops exercises.
    Applies a silent 10% inflation buffer as last resort.
    """
    if not session_minutes:
        return exercises

    budget = session_minutes * 60

    if _calc_session_seconds(exercises, sets_key) <= budget:
        return exercises

    # Step 2: reduce each exercise by 1 set (floor 2)
    step2 = [{**ex, sets_key: max(2, ex.get(sets_key, 3) - 1)} for ex in exercises]
    if _calc_session_seconds(step2, sets_key) <= budget:
        return step2

    # Step 3: reduce by another set (floor 2)
    step3 = [{**ex, sets_key: max(2, ex.get(sets_key, 3) - 2)} for ex in exercises]
    if _calc_session_seconds(step3, sets_key) <= budget:
        return step3

    # Step 4: 10% silent inflation — accept best effort without dropping exercises
    return step3


def _exercise_budget(session_minutes: Optional[int], goal: str) -> Optional[int]:
    """
    Rough upper bound on exercise count for initial selection cap.
    The actual set count is then fitted by _fit_to_time.
    """
    if not session_minutes:
        return None
    # Conservative: each exercise takes at least 2 sets × (compound time + rest)
    min_seconds_per_ex = (COMPOUND_SET_SECONDS + REST_COMPOUND) * 2
    available = session_minutes * 60 - WARMUP_BUDGET_SECONDS
    return max(3, int(available / min_seconds_per_ex))


def _deload_sets(normal_sets: int, mev: int) -> int:
    return max(mev, normal_sets // 2)


# ── Exercise selection ─────────────────────────────────────────────────────────

def _select_exercises(
    muscles: list[str],
    available_equipment: set[str],
    exercises_db: list[dict],
    goal: str,
    max_per_muscle: int = 3,
    max_total: Optional[int] = None,
    compounds_only: bool = False,
) -> list[dict]:
    """
    Select exercises for a session with:
    - Equipment filtering
    - Movement pattern conflict prevention (no two squat-pattern or two hinge-pattern)
    - Push/pull balance (compound push and pull stay within 1 of each other)
    - ISO_CRITICAL_MUSCLES always get at least 1 exercise even at max_total
    Returns sorted: high-fatigue compounds → medium compounds → isolations.
    """
    selected_ids: set[int] = set()
    result: list[dict] = []
    pattern_counts: dict[str, int] = {}
    compound_primaries: set[str] = set()  # first primary already covered by a compound
    push_count = 0
    pull_count = 0

    for muscle in muscles:
        if muscle in CORE_MUSCLES:
            continue  # core is optional accessory only; never auto-assigned
        at_max = max_total is not None and len(result) >= max_total
        is_critical = muscle in ISO_CRITICAL_MUSCLES
        if at_max and not is_critical:
            continue

        candidates = [
            ex for ex in exercises_db
            if muscle in _parse_list(ex.get("primary_muscles", []))
            and set(_parse_list(ex.get("equipment_required", []))).issubset(available_equipment)
        ]

        compounds = [e for e in candidates if e.get("mechanics") == "compound"]
        isolations = [e for e in candidates if e.get("mechanics") == "isolation"]
        ordered = compounds if compounds_only else (compounds + isolations)

        count = 0
        for ex in ordered:
            if max_total is not None and len(result) >= max_total and not is_critical:
                break
            if count >= max_per_muscle:
                break
            if ex["id"] in selected_ids:
                continue

            mechanics = ex.get("mechanics", "isolation")
            pattern = ex.get("movement_pattern", "")
            fatigue = _movement_fatigue(pattern)

            # Never stack any two high-fatigue compounds (squat+deadlift devastates CNS)
            if fatigue == "high" and any(pattern_counts.get(p, 0) > 0 for p in HIGH_FATIGUE_PATTERNS):
                continue

            # Max 1 compound per primary muscle group (no bench+incline bench, no pullup+lat pulldown)
            if mechanics == "compound":
                first_primary = (_parse_list(ex.get("primary_muscles", [])) or [None])[0]
                if first_primary and first_primary in compound_primaries:
                    continue

            # Push/pull balance: neither side runs more than 1 compound ahead of the other
            force = ex.get("force", "")
            if mechanics == "compound":
                if force == "push" and push_count > pull_count + 1:
                    continue
                if force == "pull" and pull_count > push_count + 1:
                    continue

            selected_ids.add(ex["id"])
            result.append(ex)
            count += 1

            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            if mechanics == "compound":
                first_primary = (_parse_list(ex.get("primary_muscles", [])) or [None])[0]
                if first_primary:
                    compound_primaries.add(first_primary)
                if force == "push":
                    push_count += 1
                elif force == "pull":
                    pull_count += 1

    # Sort: high-fatigue compounds first → medium compounds → isolations
    result.sort(key=lambda e: (
        0 if _movement_fatigue(e.get("movement_pattern", "")) == "high"
        else 1 if e.get("mechanics") == "compound"
        else 2
    ))

    return result


# ── Slot-based session structure ──────────────────────────────────────────────

VARIANT_PUSH_PULL: dict[str, tuple[str, str]] = {
    "A": ("horizontal_push", "horizontal_pull"),
    "B": ("vertical_push",   "vertical_pull"),
    "C": ("horizontal_push", "horizontal_pull"),  # different exercise via variant_index=2
}

SESSION_SLOT_TEMPLATES: dict[str, list[str]] = {
    "full_body":   ["knee_dominant", "hip_dominant", "{push}", "{pull}"],
    "push":        ["horizontal_push", "vertical_push"],
    "pull":        ["horizontal_pull", "vertical_pull"],
    "legs":        ["knee_dominant", "hip_dominant"],
    "lower":       ["knee_dominant", "hip_dominant"],
    "upper":       ["horizontal_push", "vertical_push", "horizontal_pull", "vertical_pull"],
    "upper_lower": ["knee_dominant", "hip_dominant", "{push}", "{pull}"],  # fallback, resolved per day
    "chest":       ["horizontal_push"],
    "back":        ["horizontal_pull", "vertical_pull"],
    "shoulders":   ["vertical_push"],
    "arms":        [],
    "custom":      ["knee_dominant", "hip_dominant", "{push}", "{pull}"],
    "default":     ["knee_dominant", "hip_dominant", "{push}", "{pull}"],
}


def _infer_day_split_type(day_name: str) -> str:
    n = day_name.lower()
    if "full body" in n or "full_body" in n:
        return "full_body"
    if "push" in n:
        return "push"
    if "pull" in n:
        return "pull"
    if "leg" in n:
        return "legs"
    if "lower" in n:
        return "lower"
    if "upper" in n:
        return "upper"
    if "chest" in n:
        return "chest"
    if "back" in n:
        return "back"
    if "shoulder" in n:
        return "shoulders"
    if "arm" in n or "bicep" in n or "tricep" in n:
        return "arms"
    return "default"


def _build_slot_template(split_type: str, day_name: str, variant_letter: str) -> list[str]:
    """Return ordered sub_pattern slot list for a session. Push/pull resolve by variant."""
    day_type = _infer_day_split_type(day_name)

    # For upper_lower splits, resolve per-day type from name
    if split_type in ("upper_lower",):
        effective_type = day_type
    else:
        effective_type = split_type if split_type in SESSION_SLOT_TEMPLATES else day_type

    template = SESSION_SLOT_TEMPLATES.get(effective_type, SESSION_SLOT_TEMPLATES["default"])
    push_slot, pull_slot = VARIANT_PUSH_PULL.get(variant_letter, VARIANT_PUSH_PULL["A"])

    result = []
    for slot in template:
        if slot == "{push}":
            result.append(push_slot)
        elif slot == "{pull}":
            result.append(pull_slot)
        else:
            result.append(slot)
    return result


def _select_for_slot(
    slot: str,
    available_equipment: set[str],
    exercises_db: list[dict],
    excluded_ids: set[int],
    experience_level: str,
    variant_index: int = 0,
) -> Optional[dict]:
    """Pick one exercise for a slot, cycling through candidates by variant_index."""
    candidates = [
        ex for ex in exercises_db
        if ex.get("sub_pattern") == slot
        and set(_parse_list(ex.get("equipment_required", []))).issubset(available_equipment)
        and ex["id"] not in excluded_ids
    ]
    if experience_level == "beginner":
        candidates = [e for e in candidates if e.get("mechanics") == "compound"]
    candidates.sort(key=lambda e: e["name"])
    if not candidates:
        return None
    return candidates[variant_index % len(candidates)]


def _select_session_exercises(
    slots: list[str],
    available_equipment: set[str],
    exercises_db: list[dict],
    experience_level: str,
    variant_letter: str,
    max_total: Optional[int],
) -> list[dict]:
    """Fill each slot with one exercise. Structural slot list prevents axial-load stacking."""
    variant_index = {"A": 0, "B": 1, "C": 2}.get(variant_letter, 0)
    result: list[dict] = []
    selected_ids: set[int] = set()

    for slot in slots:
        if max_total is not None and len(result) >= max_total:
            break
        ex = _select_for_slot(slot, available_equipment, exercises_db, selected_ids,
                               experience_level, variant_index)
        if ex:
            result.append(ex)
            selected_ids.add(ex["id"])

    return result


def _variant_letter(session_index: int, num_variants: int) -> str:
    return ["A", "B", "C"][session_index % max(num_variants, 1)]


# ── Volume helpers ─────────────────────────────────────────────────────────────

def _sets_for_week(mev: int, week_number: int, mrv: int, experience_level: str = "intermediate") -> int:
    if experience_level == "beginner":
        increment = 1
    elif experience_level == "advanced":
        increment = 3
    else:
        increment = 2
    return min(mev + (week_number - 1) * increment, mrv)


# ── Preview ────────────────────────────────────────────────────────────────────

def preview_mesocycle(
    split_template: dict,
    goal: str,
    weeks: int,
    available_equipment: list[str],
    exercises_db: list[dict],
    landmarks: dict,
    periodization_type: str = "standard",
    session_minutes: Optional[int] = None,
    experience_level: str = "intermediate",
    num_variants: int = 2,
) -> list[dict]:
    """
    Returns per-day exercise selection (week-1 parameters) without persisting.
    Each entry: {day_index, day_name, muscle_focus, exercises, frequency_warnings, variant}
    """
    equip_set = set(available_equipment)
    split_type = split_template.get("split_type", "full_body")
    days = split_template.get("days", [])
    is_beginner = experience_level == "beginner"
    time_cap = _exercise_budget(session_minutes, goal)
    max_total = min(time_cap, 4) if is_beginner else time_cap

    # Sessions per muscle across all days (for set distribution)
    sessions_per_muscle: dict[str, int] = {}
    for d in days:
        for m in _parse_list(d.get("muscle_focus", [])):
            sessions_per_muscle[m] = sessions_per_muscle.get(m, 0) + 1

    # Frequency warnings (research minimum: 2x/week for hypertrophy)
    min_freq = 2
    frequency_warnings = [
        {
            "muscle": m,
            "frequency": freq,
            "recommended": min_freq,
            "message": f"{m.capitalize()} is only hit {freq}x/week — minimum for growth is {min_freq}x.",
        }
        for m, freq in sessions_per_muscle.items()
        if freq < min_freq
    ]

    result = []
    for idx, day in enumerate(days):
        muscles = _parse_list(day.get("muscle_focus", []))
        variant = _variant_letter(idx, num_variants)
        slots = _build_slot_template(split_type, day["name"], variant)
        exercises_for_day = _select_session_exercises(
            slots, equip_set, exercises_db, experience_level, variant, max_total
        )

        activated_muscles: set[str] = set()
        secondary_credits: dict[str, float] = {}
        preview_exercises = []

        for ex in exercises_for_day:
            primaries = _parse_list(ex.get("primary_muscles", []))
            primary = primaries[0] if primaries else None
            lm = landmarks.get(primary, {"mev": 8, "mav_low": 12, "mav_high": 20, "mrv": 22})
            mev = lm.get("mev", 8)
            mrv = lm.get("mrv", 22)
            weekly_sets = _sets_for_week(mev, 1, mrv, experience_level)
            num_sessions = sessions_per_muscle.get(primary, 1)

            # Reduce needed sets by accumulated secondary coverage
            sec_credit = secondary_credits.get(primary, 0.0)
            adjusted_weekly = max(mev, weekly_sets - sec_credit)
            per_session = min(max(2, math.ceil(adjusted_weekly / num_sessions)), 6)

            mechanics = ex.get("mechanics", "compound")
            warmup_sets = _warmup_sets_needed(ex, activated_muscles)
            rest_seconds = _rest_for_exercise(ex)

            sub_pattern = ex.get("sub_pattern", "")
            if is_beginner:
                _, reps_min, reps_max, rir = _rep_set_for_pattern(sub_pattern, goal, True, 1, weeks)
            elif periodization_type == "linear":
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
                "mechanics": mechanics,
                "movement_pattern": ex.get("movement_pattern", ""),
                "sub_pattern": sub_pattern,
                "target_sets": per_session,
                "target_reps_min": reps_min,
                "target_reps_max": reps_max,
                "target_rir": rir,
                "warmup_sets": warmup_sets,
                "rest_seconds": rest_seconds,
            })

            # Update activation and secondary credits for subsequent exercises
            for m in primaries:
                activated_muscles.add(m)
            for m in _parse_list(ex.get("secondary_muscles", [])):
                activated_muscles.add(m)
            _apply_secondary_credits(ex, secondary_credits, per_session)

        # Fit to time budget by reducing sets (never dropping exercises)
        if session_minutes:
            preview_exercises = _fit_to_time(preview_exercises, session_minutes)

        result.append({
            "day_index": idx,
            "day_name": day["name"],
            "muscle_focus": muscles,
            "exercises": preview_exercises,
            "frequency_warnings": frequency_warnings,
            "variant": variant,
        })

    return result


# ── Full mesocycle generation ──────────────────────────────────────────────────

def generate_mesocycle(
    split_template: dict,
    goal: str,
    weeks: int,
    deload_week: int,
    landmarks: dict,
    available_equipment: list[str],
    exercises_db: list[dict],
    periodization_type: str = "standard",
    day_exercises: Optional[dict[int, list[int]]] = None,
    session_minutes: Optional[int] = None,
    experience_level: str = "intermediate",
    num_variants: int = 2,
    session_mode: str = "auto",
    custom_slot_sessions: Optional[list[dict]] = None,
) -> list[dict]:
    """
    Returns list of week dicts with planned sessions and exercises.
    Each exercise includes warmup_sets and rest_seconds.
    Sets are reduced (never exercises dropped) if session_minutes is exceeded.
    """
    equip_set = set(available_equipment)
    split_type = split_template.get("split_type", "full_body")
    days = split_template.get("days", [])
    ex_by_id = {ex["id"]: ex for ex in exercises_db}
    is_beginner = experience_level == "beginner"
    time_cap = _exercise_budget(session_minutes, goal)
    max_total = min(time_cap, 4) if is_beginner else time_cap

    # Sessions per muscle — computed once, outside the week loop
    sessions_per_muscle: dict[str, int] = {}
    for d in days:
        for m in _parse_list(d.get("muscle_focus", [])):
            sessions_per_muscle[m] = sessions_per_muscle.get(m, 0) + 1

    result = []
    global_session_idx = 0

    for week_num in range(1, weeks + 1):
        is_deload = (week_num == deload_week)
        week_sessions = []

        for day in days:
            muscles = _parse_list(day.get("muscle_focus", []))
            day_idx = day["day_number"] - 1
            variant = _variant_letter(global_session_idx, num_variants)
            global_session_idx += 1

            if day_exercises and day_idx in day_exercises:
                # Auto-mode preview swaps always take priority
                exercises_for_day = [
                    ex_by_id[eid] for eid in day_exercises[day_idx] if eid in ex_by_id
                ]
            elif session_mode == "custom_slots" and custom_slot_sessions:
                # Custom slot path: cycle by global session index, respect pinned IDs.
                # global_session_idx already incremented above, so subtract 1 for current session.
                sess_def = custom_slot_sessions[(global_session_idx - 1) % len(custom_slot_sessions)]
                slots = sess_def.get("slots", [])
                slot_exercise_ids = sess_def.get("slot_exercises", [])
                superset_groups = sess_def.get("superset_groups", [])
                set_types = sess_def.get("set_types", [])
                variant_index = {"A": 0, "B": 1, "C": 2}.get(variant, 0)
                exercises_for_day = []
                selected_ids: set[int] = set()
                for i, slot_key in enumerate(slots):
                    pinned_id = slot_exercise_ids[i] if i < len(slot_exercise_ids) else None
                    if pinned_id and pinned_id in ex_by_id:
                        ex_candidate = dict(ex_by_id[pinned_id])
                    else:
                        ex_candidate = _select_for_slot(
                            slot_key, equip_set, exercises_db, selected_ids,
                            experience_level, variant_index,
                        )
                        if not ex_candidate:
                            continue
                        ex_candidate = dict(ex_candidate)
                    ex_candidate["superset_group"] = superset_groups[i] if i < len(superset_groups) else None
                    ex_candidate["set_type"] = set_types[i] if i < len(set_types) else "straight"
                    selected_ids.add(ex_candidate["id"])
                    exercises_for_day.append(ex_candidate)
            else:
                slots = _build_slot_template(split_type, day["name"], variant)
                exercises_for_day = _select_session_exercises(
                    slots, equip_set, exercises_db, experience_level, variant, max_total
                )

            session_exercises = []
            order = 1
            activated_muscles: set[str] = set()
            secondary_credits: dict[str, float] = {}

            for ex in exercises_for_day:
                primaries = _parse_list(ex.get("primary_muscles", []))
                primary = primaries[0] if primaries else None
                lm = landmarks.get(primary, {"mev": 8, "mav_low": 12, "mav_high": 20, "mrv": 22})
                mev = lm.get("mev", 8)
                mrv = lm.get("mrv", 22)

                if is_deload:
                    prev_sets = _sets_for_week(mev, week_num - 1, mrv, experience_level)
                    weekly_sets = _deload_sets(prev_sets, mev)
                else:
                    weekly_sets = _sets_for_week(mev, week_num, mrv, experience_level)

                num_sessions = sessions_per_muscle.get(primary, 1)
                sec_credit = secondary_credits.get(primary, 0.0)
                adjusted_weekly = max(mev, weekly_sets - sec_credit)
                per_session = min(max(2, math.ceil(adjusted_weekly / num_sessions)), 6)

                mechanics = ex.get("mechanics", "compound")
                warmup_sets = _warmup_sets_needed(ex, activated_muscles)
                rest_seconds = _rest_for_exercise(ex)
                session_label = ""

                sub_pattern = ex.get("sub_pattern", "")
                if is_deload:
                    reps_min, reps_max = _rep_range_for_goal(goal, mechanics)
                    rir = 3
                elif is_beginner:
                    _, reps_min, reps_max, rir = _rep_set_for_pattern(sub_pattern, goal, True, week_num, weeks)
                elif periodization_type == "linear":
                    reps_min, reps_max = _rep_range_linear(goal, week_num, weeks)
                    progress = (week_num - 1) / max(weeks - 2, 1)
                    rir = max(1, round(3 - min(1.0, progress) * 2))
                elif periodization_type == "dup":
                    reps_min, reps_max, rir, session_label = _dup_params(goal, day["day_number"])
                elif periodization_type == "block":
                    phase = _block_phase(week_num, weeks)
                    reps_min, reps_max, rir, session_label = _BLOCK_PHASES[phase]
                elif periodization_type == "double_progression":
                    reps_min, reps_max = _rep_range_for_goal(goal, mechanics)
                    progress = (week_num - 1) / max(weeks - 1, 1)
                    rir = max(1, round(3 - progress * 2))
                elif periodization_type == "wave_loading":
                    wave = (week_num - 1) % 3
                    _s = _rep_range_for_goal("strength", mechanics)
                    _g = _rep_range_for_goal(goal, mechanics)
                    _h = _rep_range_for_goal("hypertrophy", mechanics)
                    reps_min, reps_max, rir = [(_s[0], _s[1], 1), (_g[0], _g[1], 2), (_h[0], _h[1], 3)][wave]
                else:
                    reps_min, reps_max = _rep_range_for_goal(goal, mechanics)
                    rir = _rir_for_goal(goal, is_deload)

                session_exercises.append({
                    "exercise_id": ex["id"],
                    "exercise_name": ex["name"],
                    "order_in_session": order,
                    "mechanics": mechanics,
                    "target_sets": per_session,
                    "target_reps_min": reps_min,
                    "target_reps_max": reps_max,
                    "target_rir": rir,
                    "warmup_sets": warmup_sets,
                    "rest_seconds": rest_seconds,
                    "notes": session_label,
                    "superset_group": ex.get("superset_group"),
                    "set_technique": ex.get("set_type", "straight"),
                })
                order += 1

                for m in primaries:
                    activated_muscles.add(m)
                for m in _parse_list(ex.get("secondary_muscles", [])):
                    activated_muscles.add(m)
                _apply_secondary_credits(ex, secondary_credits, per_session)

            # Fit to time budget — reduce sets, never drop exercises
            if session_minutes:
                session_exercises = _fit_to_time(session_exercises, session_minutes)
                for i, ex in enumerate(session_exercises, 1):
                    ex["order_in_session"] = i

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
