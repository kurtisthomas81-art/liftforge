"""
Published program library — static definitions for well-known training programs.
Exercise names must match seed_data.py exactly; unresolved names are silently skipped.
"""

from datetime import date as _date

# ── Metadata catalogue ─────────────────────────────────────────────────────────

PROGRAMS: dict[str, dict] = {
    "starting-strength": {
        "slug": "starting-strength",
        "name": "Starting Strength",
        "author": "Mark Rippetoe",
        "description": (
            "The gold standard beginner program. A/B alternating sessions built around "
            "squat, press, and deadlift with linear weight increases every session."
        ),
        "goal": "strength",
        "difficulty": "beginner",
        "days_per_week": 3,
        "weeks": 4,
        "deload_week": 4,
        "day_slots": [0, 2, 4],  # Mon / Wed / Fri
    },
    "gzclp": {
        "slug": "gzclp",
        "name": "GZCLP",
        "author": "Cody LeFever",
        "description": (
            "GZCL-methodology beginner/intermediate program. Three tiered sessions (T1 heavy "
            "5×3+, T2 moderate 3×10, T3 accessory volume) rotating across squat, bench, "
            "deadlift, and press."
        ),
        "goal": "strength",
        "difficulty": "beginner",
        "days_per_week": 3,
        "weeks": 4,
        "deload_week": 4,
        "day_slots": [0, 2, 4],
    },
    "531-bbb": {
        "slug": "531-bbb",
        "name": "5/3/1 Boring But Big",
        "author": "Jim Wendler",
        "description": (
            "4-day intermediate strength program with a 3-week intensity wave "
            "(5s → 3s → 5/3/1+) followed by a deload. Each main lift is paired with "
            "5×10 BBB back-off sets at ~60% training max."
        ),
        "goal": "strength",
        "difficulty": "intermediate",
        "days_per_week": 4,
        "weeks": 4,
        "deload_week": 4,
        "day_slots": [0, 1, 3, 4],  # Mon / Tue / Thu / Fri
    },
    "nsuns-cap3": {
        "slug": "nsuns-cap3",
        "name": "nSuns CAP3",
        "author": "nSuns (Reddit)",
        "description": (
            "High-volume 5/3/1 variant running 5 days/week. Main lifts use a 9-set "
            "ladder (heavy cluster + back-off volume); extensive accessory work. "
            "Significantly more weekly volume than standard 5/3/1."
        ),
        "goal": "strength",
        "difficulty": "intermediate",
        "days_per_week": 5,
        "weeks": 4,
        "deload_week": 4,
        "day_slots": [0, 1, 2, 3, 4],  # Mon–Fri
    },
    "nippard-phul": {
        "slug": "nippard-phul",
        "name": "Jeff Nippard PHUL",
        "author": "Jeff Nippard",
        "description": (
            "Power Hypertrophy Upper Lower — 4 days/week over 8 weeks. Each muscle "
            "is hit twice: once in a heavy power session (3–5 reps) and once in a "
            "hypertrophy session (8–15 reps)."
        ),
        "goal": "hypertrophy",
        "difficulty": "intermediate",
        "days_per_week": 4,
        "weeks": 8,
        "deload_week": 8,
        "day_slots": [0, 1, 3, 4],
    },
}


# ── Schedule builder ───────────────────────────────────────────────────────────

def build_schedule(slug: str, exercise_lookup: dict[str, int]) -> list[dict]:
    """
    Return weeks_data compatible with programs.py _build_planned_sessions().
    exercise_lookup maps exercise name → exercise id; missing names are skipped.
    """

    def ex(name: str, sets: int, rmin: int, rmax: int, rir: int, notes: str = ""):
        eid = exercise_lookup.get(name)
        if eid is None:
            return None
        return {
            "exercise_id": eid,
            "exercise_name": name,
            "order_in_session": 0,  # filled in by _session()
            "target_sets": sets,
            "target_reps_min": rmin,
            "target_reps_max": rmax,
            "target_rir": rir,
            "notes": notes,
        }

    def session(label: str, day_num: int, exercises_raw: list) -> dict:
        exs = [e for e in exercises_raw if e is not None]
        for i, e in enumerate(exs):
            e["order_in_session"] = i + 1
        return {
            "day_number": day_num,
            "split_day_name": label,
            "split_day_id": None,
            "muscles": [],
            "exercises": exs,
        }

    def week(week_num: int, is_deload: bool, sessions: list) -> dict:
        return {"week_number": week_num, "is_deload": is_deload, "sessions": sessions}

    # ── Starting Strength ──────────────────────────────────────────────────────
    if slug == "starting-strength":
        def ss_a(deload=False):
            s, rir = (2, 2) if deload else (3, 1)
            return [
                ex("Barbell Back Squat", s, 5, 5, rir),
                ex("Barbell Bench Press", s, 5, 5, rir),
                ex("Conventional Deadlift", 1, 5, 5, rir),
            ]

        def ss_b(deload=False):
            s, rir = (2, 2) if deload else (3, 1)
            return [
                ex("Barbell Back Squat", s, 5, 5, rir),
                ex("Barbell Overhead Press", s, 5, 5, rir),
                ex("Barbell Row", s, 5, 5, rir),
            ]

        return [
            week(1, False, [session("Workout A", 1, ss_a()), session("Workout B", 2, ss_b()), session("Workout A", 3, ss_a())]),
            week(2, False, [session("Workout B", 1, ss_b()), session("Workout A", 2, ss_a()), session("Workout B", 3, ss_b())]),
            week(3, False, [session("Workout A", 1, ss_a()), session("Workout B", 2, ss_b()), session("Workout A", 3, ss_a())]),
            week(4, True,  [session("Workout B", 1, ss_b(True)), session("Workout A", 2, ss_a(True)), session("Workout B", 3, ss_b(True))]),
        ]

    # ── GZCLP ──────────────────────────────────────────────────────────────────
    if slug == "gzclp":
        def gzclp_a():
            return [
                ex("Barbell Back Squat",  5, 3, 5, 1, "T1 — last set AMRAP"),
                ex("Barbell Bench Press", 3, 10, 10, 2, "T2"),
                ex("Lat Pulldown",        3, 15, 15, 2, "T3"),
            ]

        def gzclp_b():
            return [
                ex("Barbell Bench Press",     5, 3, 5, 1, "T1 — last set AMRAP"),
                ex("Barbell Overhead Press",  3, 10, 10, 2, "T2"),
                ex("Pull-Up",                 3, 8, 15, 2, "T3 — AMRAP each set"),
            ]

        def gzclp_c():
            return [
                ex("Conventional Deadlift", 5, 3, 5, 1, "T1 — last set AMRAP"),
                ex("Barbell Back Squat",    3, 10, 10, 2, "T2"),
                ex("Barbell Row",           3, 10, 12, 2, "T3"),
            ]

        def gzclp_deload():
            return [
                ex("Barbell Back Squat",     3, 5, 5, 3, "Deload — ~80% usual weight"),
                ex("Barbell Bench Press",    3, 5, 5, 3, "Deload"),
                ex("Conventional Deadlift",  2, 5, 5, 3, "Deload"),
            ]

        schedule = []
        for w in range(1, 5):
            is_dl = w == 4
            if is_dl:
                sessions = [
                    session("Deload A", 1, gzclp_deload()),
                    session("Deload B", 2, [ex("Barbell Overhead Press", 3, 5, 5, 3, "Deload"), ex("Barbell Row", 3, 5, 5, 3, "Deload")]),
                    session("Deload C", 3, [ex("Conventional Deadlift", 2, 5, 5, 3, "Deload"), ex("Lat Pulldown", 3, 10, 10, 3, "Deload")]),
                ]
            else:
                sessions = [
                    session("Session A", 1, gzclp_a()),
                    session("Session B", 2, gzclp_b()),
                    session("Session C", 3, gzclp_c()),
                ]
            schedule.append(week(w, is_dl, sessions))
        return schedule

    # ── 5/3/1 Boring But Big ───────────────────────────────────────────────────
    if slug == "531-bbb":
        ohp_acc   = [ex("Chin-Up",      5, 8, 10, 2), ex("Dumbbell Row",    5, 10, 15, 2)]
        dl_acc    = [ex("Lying Leg Curl", 3, 10, 15, 2), ex("Ab Wheel Rollout", 3, 8, 10, 2)]
        bench_acc = [ex("Dips (tricep)", 5, 8, 12, 2), ex("Dumbbell Row",    5, 10, 15, 2)]
        squat_acc = [ex("Lying Leg Curl", 3, 10, 15, 2), ex("Ab Wheel Rollout", 3, 10, 15, 2)]

        # (sets, reps_min, reps_max, rir) for main lift per week
        wave = [(3, 5, 5, 2), (3, 3, 3, 1), (3, 1, 5, 0), (3, 5, 5, 4)]
        notes_wave = ["5s week — last set AMRAP", "3s week — last set AMRAP", "1s week — 5/3/1+", "Deload"]

        def bbb_day(main, bbb, accessories, sets, rmin, rmax, rir, deload, label, day_num):
            exs = [ex(main, sets, rmin, rmax, rir, notes_wave[day_num])]
            if not deload:
                exs.append(ex(bbb, 5, 10, 10, 3, "Boring But Big — 5×10 @ ~60% TM"))
                exs.extend(accessories)
            return exs

        schedule = []
        for w_idx, (sets, rmin, rmax, rir) in enumerate(wave):
            w_num = w_idx + 1
            is_dl = w_num == 4
            note_i = w_idx
            sessions = [
                session("OHP Day",   1, bbb_day("Barbell Overhead Press", "Barbell Overhead Press", ohp_acc,   sets, rmin, rmax, rir, is_dl, label=notes_wave[note_i], day_num=note_i)),
                session("DL Day",    2, bbb_day("Conventional Deadlift",  "Conventional Deadlift",  dl_acc,    sets, rmin, rmax, rir, is_dl, label=notes_wave[note_i], day_num=note_i)),
                session("Bench Day", 3, bbb_day("Barbell Bench Press",    "Barbell Bench Press",    bench_acc, sets, rmin, rmax, rir, is_dl, label=notes_wave[note_i], day_num=note_i)),
                session("Squat Day", 4, bbb_day("Barbell Back Squat",     "Barbell Back Squat",     squat_acc, sets, rmin, rmax, rir, is_dl, label=notes_wave[note_i], day_num=note_i)),
            ]
            schedule.append(week(w_num, is_dl, sessions))
        return schedule

    # ── nSuns CAP3 ─────────────────────────────────────────────────────────────
    if slug == "nsuns-cap3":
        def nsuns_day1_bench(is_dl=False):
            if is_dl:
                return [ex("Barbell Bench Press", 3, 5, 5, 3, "Deload")]
            return [
                ex("Barbell Bench Press",        4, 4, 6, 1, "Main cluster — heavy sets"),
                ex("Barbell Bench Press",        4, 8, 10, 2, "Back-off volume"),
                ex("Incline Barbell Bench Press", 3, 8, 12, 2),
                ex("Tricep Pushdown (rope)",      3, 10, 15, 2),
                ex("Lateral Raise",               3, 12, 15, 2),
            ]

        def nsuns_day2_squat(is_dl=False):
            if is_dl:
                return [ex("Barbell Back Squat", 3, 5, 5, 3, "Deload")]
            return [
                ex("Barbell Back Squat",  4, 4, 6, 1, "Main cluster"),
                ex("Barbell Back Squat",  4, 8, 10, 2, "Back-off volume"),
                ex("Romanian Deadlift",   3, 8, 12, 2),
                ex("Leg Press",           3, 10, 15, 2),
                ex("Lying Leg Curl",      3, 10, 15, 2),
            ]

        def nsuns_day3_ohp(is_dl=False):
            if is_dl:
                return [ex("Barbell Overhead Press", 3, 5, 5, 3, "Deload")]
            return [
                ex("Barbell Overhead Press",   4, 4, 6, 1, "Main cluster"),
                ex("Barbell Overhead Press",   4, 8, 10, 2, "Back-off volume"),
                ex("Close-Grip Bench Press",   3, 8, 12, 2),
                ex("Barbell Row",              4, 8, 12, 2),
                ex("Face Pull",                3, 12, 15, 2),
            ]

        def nsuns_day4_deadlift(is_dl=False):
            if is_dl:
                return [ex("Conventional Deadlift", 2, 5, 5, 3, "Deload")]
            return [
                ex("Conventional Deadlift",  4, 3, 5, 1, "Main cluster"),
                ex("Conventional Deadlift",  3, 8, 8, 2, "Back-off volume"),
                ex("Leg Extension",          3, 10, 15, 2),
                ex("Ab Wheel Rollout",        3, 8, 10, 2),
            ]

        def nsuns_day5_bench2(is_dl=False):
            if is_dl:
                return [ex("Incline Barbell Bench Press", 3, 8, 12, 3, "Deload")]
            return [
                ex("Incline Barbell Bench Press", 4, 6, 10, 2, "Secondary bench"),
                ex("Lat Pulldown",                4, 8, 12, 2),
                ex("Dumbbell Curl",               3, 10, 12, 2),
                ex("Overhead Tricep Extension (dumbbell)", 3, 10, 12, 2),
                ex("Lateral Raise",               3, 12, 15, 2),
            ]

        schedule = []
        for w in range(1, 5):
            is_dl = w == 4
            sessions = [
                session("Bench",    1, nsuns_day1_bench(is_dl)),
                session("Squat",    2, nsuns_day2_squat(is_dl)),
                session("OHP",      3, nsuns_day3_ohp(is_dl)),
                session("Deadlift", 4, nsuns_day4_deadlift(is_dl)),
                session("Bench 2",  5, nsuns_day5_bench2(is_dl)),
            ]
            schedule.append(week(w, is_dl, sessions))
        return schedule

    # ── Jeff Nippard PHUL ──────────────────────────────────────────────────────
    if slug == "nippard-phul":
        def phul_upper_power():
            return [
                ex("Barbell Bench Press",      3, 3, 5, 1),
                ex("Barbell Row",              3, 3, 5, 1),
                ex("Barbell Overhead Press",   3, 6, 10, 2),
                ex("Pull-Up",                  3, 6, 10, 2),
                ex("Close-Grip Bench Press",   3, 6, 10, 2),
                ex("Barbell Curl",             3, 6, 10, 2),
            ]

        def phul_lower_power():
            return [
                ex("Barbell Back Squat",   3, 3, 5, 1),
                ex("Romanian Deadlift",    3, 3, 5, 1),
                ex("Leg Press",            3, 6, 10, 2),
                ex("Seated Leg Curl",      3, 6, 10, 2),
                ex("Standing Calf Raise",  3, 6, 10, 2),
            ]

        def phul_upper_hyp():
            return [
                ex("Incline Barbell Bench Press", 3, 8, 12, 2),
                ex("Lat Pulldown",                3, 8, 12, 2),
                ex("Cable Flye High-to-Low",      3, 8, 12, 2),
                ex("Dumbbell Overhead Press",     3, 8, 12, 2),
                ex("Skull Crushers",              3, 8, 12, 2),
                ex("Dumbbell Curl",               3, 8, 12, 2),
                ex("Tricep Pushdown (rope)",      3, 10, 15, 2),
            ]

        def phul_lower_hyp():
            return [
                ex("Front Squat",          3, 8, 12, 2),
                ex("Romanian Deadlift",    3, 8, 12, 2),
                ex("Leg Press",            3, 10, 15, 2),
                ex("Seated Leg Curl",      3, 10, 15, 2),
                ex("Leg Extension",        3, 10, 15, 2),
                ex("Seated Calf Raise",    3, 10, 15, 2),
            ]

        def phul_deload():
            return [
                session("Upper Power (Deload)", 1, [ex("Barbell Bench Press", 2, 5, 5, 3, "Deload"), ex("Pull-Up", 2, 6, 8, 3, "Deload")]),
                session("Lower Power (Deload)", 2, [ex("Barbell Back Squat", 2, 5, 5, 3, "Deload"), ex("Romanian Deadlift", 2, 5, 5, 3, "Deload")]),
                session("Upper Hyp (Deload)",   3, [ex("Incline Barbell Bench Press", 2, 8, 10, 3, "Deload"), ex("Lat Pulldown", 2, 8, 10, 3, "Deload")]),
                session("Lower Hyp (Deload)",   4, [ex("Barbell Back Squat", 2, 8, 10, 3, "Deload"), ex("Seated Leg Curl", 2, 10, 12, 3, "Deload")]),
            ]

        schedule = []
        for w in range(1, 9):
            is_dl = w == 8
            if is_dl:
                sessions = phul_deload()
            else:
                sessions = [
                    session("Upper Power",      1, phul_upper_power()),
                    session("Lower Power",      2, phul_lower_power()),
                    session("Upper Hypertrophy",3, phul_upper_hyp()),
                    session("Lower Hypertrophy",4, phul_lower_hyp()),
                ]
            schedule.append(week(w, is_dl, sessions))
        return schedule

    raise ValueError(f"Unknown published program slug: {slug}")
