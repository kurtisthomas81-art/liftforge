"""
Program balance checker — analyzes weekly slot distribution across preview sessions.
Returns push/pull ratio, upper/lower ratio, missing patterns, and actionable suggestions.
"""

PUSH_PATTERNS = {"horizontal_push", "vertical_push"}
PULL_PATTERNS = {"horizontal_pull", "vertical_pull"}
LOWER_PATTERNS = {"knee_dominant", "hip_dominant"}
UPPER_PATTERNS = PUSH_PATTERNS | PULL_PATTERNS

_PATTERN_FRIENDLY: dict[str, str] = {
    "horizontal_push": "horizontal pushing (bench press, push-ups)",
    "vertical_push":   "vertical pushing (overhead press)",
    "horizontal_pull": "horizontal pulling (barbell row, cable row)",
    "vertical_pull":   "vertical pulling (lat pulldown, pull-ups)",
    "knee_dominant":   "knee-dominant lower (squats, leg press)",
    "hip_dominant":    "hip-dominant lower (deadlifts, RDLs, hip thrusts)",
}


def check_program_balance(preview_sessions: list[dict]) -> dict:
    """
    Input: list of day preview dicts (same shape as preview_mesocycle() output).
    Each session dict has an 'exercises' list; each exercise has a 'sub_pattern' field.

    Returns:
        is_balanced      bool
        push_pull_ratio  float  (1.0 = ideal; warn if < 0.72 or > 1.4)
        upper_lower_ratio float (ideal 1.0–1.8 for general/hypertrophy)
        pattern_counts   dict[str, int]
        missing_patterns list[str]
        warnings         list[str]
        suggestions      list[str]
    """
    pattern_counts: dict[str, int] = {}

    for session in preview_sessions:
        for ex in session.get("exercises", []):
            sp = ex.get("sub_pattern", "")
            if sp:
                pattern_counts[sp] = pattern_counts.get(sp, 0) + 1

    total_push  = sum(pattern_counts.get(p, 0) for p in PUSH_PATTERNS)
    total_pull  = sum(pattern_counts.get(p, 0) for p in PULL_PATTERNS)
    total_upper = total_push + total_pull
    total_lower = sum(pattern_counts.get(p, 0) for p in LOWER_PATTERNS)

    push_pull_ratio   = round(total_push  / max(total_pull,  1), 2)
    upper_lower_ratio = round(total_upper / max(total_lower, 1), 2)

    warnings:   list[str] = []
    suggestions: list[str] = []

    # ── Push / pull balance ────────────────────────────────────────────────────
    if total_pull == 0 and total_push > 0:
        warnings.append("No pulling movements detected this week")
        suggestions.append(
            "Add a row (horizontal pull) or lat pulldown / pull-up (vertical pull) to at least one session"
        )
    elif total_push == 0 and total_pull > 0:
        warnings.append("No pushing movements detected this week")
        suggestions.append(
            "Add a bench press or overhead press (push pattern) to at least one session"
        )
    elif push_pull_ratio > 1.4:
        warnings.append(f"Push-heavy — {total_push} push vs {total_pull} pull movements per week")
        suggestions.append("Add more pulling movements (rows, pulldowns) for shoulder health and balance")
    elif push_pull_ratio < 0.72:
        warnings.append(f"Pull-heavy — {total_pull} pull vs {total_push} push movements per week")
        suggestions.append("Add more pushing movements (press patterns) for balanced upper body development")

    # ── Upper / lower balance ─────────────────────────────────────────────────
    if total_lower == 0 and total_upper > 0:
        warnings.append("No lower body exercises in this program")
        suggestions.append(
            "Add at least one squat or deadlift pattern (knee / hip dominant) per lower-body or full-body session"
        )
    elif total_upper == 0 and total_lower > 0:
        warnings.append("No upper body exercises in this program")
        suggestions.append("Add pushing and pulling movements for complete upper body development")
    elif total_lower > 0 and upper_lower_ratio > 3.0:
        warnings.append(f"Upper-heavy program — {total_upper} upper vs {total_lower} lower movements per week")
        suggestions.append("Add more lower body work (squats, deadlifts) for overall athleticism")

    # ── Missing individual patterns ───────────────────────────────────────────
    missing_patterns: list[str] = [
        p for p in list(PUSH_PATTERNS) + list(PULL_PATTERNS) + list(LOWER_PATTERNS)
        if pattern_counts.get(p, 0) == 0
    ]

    return {
        "is_balanced":      len(warnings) == 0,
        "push_pull_ratio":  push_pull_ratio,
        "upper_lower_ratio": upper_lower_ratio,
        "pattern_counts":   pattern_counts,
        "missing_patterns": missing_patterns,
        "warnings":         warnings,
        "suggestions":      suggestions,
    }
