from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, migrate_db, engine
from models import (
    Exercise, SplitTemplate, MuscleVolumeLandmark,
    WorkoutSet, WorkoutSession, PersonalRecord, BodyMeasurement,
    Goal, Mesocycle, MesocycleWeek, PlannedSession, PlannedExercise,
    WorkoutTemplate, TemplateExercise, WeeklyCheckin, Injury,
)
from sqlmodel import Session, select
from routers import exercises, sessions, history, profile, ollama
from routers import programs, landmarks, volume, prs, templates, measurements, export, recovery, liftsaur_sync, goals, injuries, analytics, import_queue, google_fit

app = FastAPI(title="LiftForge API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(exercises.router)
app.include_router(sessions.router)
app.include_router(history.router)
app.include_router(profile.router)
app.include_router(ollama.router)
app.include_router(programs.router)
app.include_router(landmarks.router)
app.include_router(volume.router)
app.include_router(prs.router)
app.include_router(templates.router)
app.include_router(measurements.router)
app.include_router(export.router)
app.include_router(recovery.router)
app.include_router(liftsaur_sync.router)
app.include_router(goals.router)
app.include_router(injuries.router)
app.include_router(analytics.router)
app.include_router(import_queue.router)
app.include_router(google_fit.router)


def _backfill_exercise_aliases(session: Session) -> None:
    """Merge missing alias variants into seeded exercises so imports don't fragment the DB."""
    import json as _json
    EXTRA: dict[str, list[str]] = {
        "Barbell Bench Press":          ["flat bench press", "bench"],
        "Incline Barbell Bench Press":  ["incline bench press", "incline barbell bench"],
        "Barbell Overhead Press":       ["overhead press", "shoulder press"],
        "Barbell Row":                  ["bent over row", "barbell bent-over row"],
        "Pull-Up":                      ["pull up", "pull ups", "pull-ups"],
        "Chin-Up":                      ["chin up", "chin ups"],
        "Romanian Deadlift":            ["romanian deadlift"],
        "Barbell Back Squat":           ["barbell squat"],
        "Conventional Deadlift":        ["dl"],
    }
    changed = 0
    for ex_name, extras in EXTRA.items():
        ex = session.exec(select(Exercise).where(Exercise.name == ex_name)).first()
        if not ex:
            continue
        current = _json.loads(ex.aliases or "[]")
        current_lower = {a.lower() for a in current}
        to_add = [a for a in extras if a.lower() not in current_lower]
        if to_add:
            ex.aliases = _json.dumps(current + to_add)
            session.add(ex)
            changed += 1
    if changed:
        session.commit()


def _backfill_sub_patterns(session: Session) -> None:
    """Compute and write sub_pattern for any exercises that don't have one yet."""
    import json as _json
    from seed_data import _compute_sub_pattern
    needs_backfill = [ex for ex in session.exec(select(Exercise)).all() if not ex.sub_pattern]
    if not needs_backfill:
        return
    for ex in needs_backfill:
        try:
            pm = _json.loads(ex.primary_muscles)
        except Exception:
            pm = []
        ex.sub_pattern = _compute_sub_pattern(
            ex.movement_pattern or "",
            ex.force or "",
            pm,
            ex.mechanics or "",
            ex.name,
        )
        session.add(ex)
    session.commit()
    print(f"Backfilled sub_pattern for {len(needs_backfill)} exercises.")


def _backfill_secondary_muscles(session: Session) -> None:
    """Write secondary_muscles from seed data to any exercise that has an empty array."""
    import json as _json
    from seed_data import EXERCISES as _EXERCISES
    seed_map = {ex["name"]: ex.get("secondary_muscles", []) for ex in _EXERCISES}
    all_exercises = session.exec(select(Exercise)).all()
    updated = 0
    for ex in all_exercises:
        if ex.secondary_muscles and ex.secondary_muscles != "[]":
            continue
        seed_secondary = seed_map.get(ex.name, [])
        if seed_secondary:
            ex.secondary_muscles = _json.dumps(seed_secondary)
            session.add(ex)
            updated += 1
    if updated:
        session.commit()
        print(f"Backfilled secondary_muscles for {updated} exercises.")


_COMPOUND_SECONDARY_ADDITIONS = {
    "Conventional Deadlift":  ["abs"],
    "Romanian Deadlift":      ["abs"],
    "Trap Bar Deadlift":      ["abs"],
    "Stiff-Leg Deadlift":     ["abs"],
    "Sumo Deadlift":          ["abs"],
    "Barbell Overhead Press": ["abs"],
    "Dumbbell Overhead Press":["abs"],
    "Barbell Back Squat":     ["abs", "calves"],
    "Front Squat":            ["abs", "calves"],
    "Leg Press":              ["calves"],
    "Bulgarian Split Squat":  ["calves"],
    "Lunge":                  ["calves"],
    "Walking Lunge":          ["calves"],
    "Pull-Up":                ["abs"],
    "Chin-Up":                ["abs"],
}


def _backfill_compound_secondaries(session: Session) -> None:
    """Merge abs/calves into compound exercises that were seeded without them."""
    import json as _json
    updated = 0
    for name, to_add in _COMPOUND_SECONDARY_ADDITIONS.items():
        ex = session.exec(select(Exercise).where(Exercise.name == name)).first()
        if not ex:
            continue
        try:
            current = _json.loads(ex.secondary_muscles or "[]")
        except Exception:
            current = []
        merged = list(dict.fromkeys(current + [m for m in to_add if m not in current]))
        if merged != current:
            ex.secondary_muscles = _json.dumps(merged)
            session.add(ex)
            updated += 1
    if updated:
        session.commit()
        print(f"Backfilled compound secondary muscles for {updated} exercises.")


def _purge_redundant_exercises(session: Session) -> None:
    """Remove exercises that are exact duplicates of better-named alternatives, only if never logged."""
    to_purge = ["Machine Lateral Raise", "Cross-Body Hammer Curl"]
    for name in to_purge:
        ex = session.exec(select(Exercise).where(Exercise.name == name)).first()
        if not ex:
            continue
        used = session.exec(select(WorkoutSet).where(WorkoutSet.exercise_id == ex.id).limit(1)).first()
        if used:
            continue
        session.delete(ex)
    session.commit()


def _fix_exercise_categories(session: Session) -> None:
    """Correct miscategorizations and add missing secondary muscles. All ops are idempotent."""
    import json as _json

    fixes = [
        # (name, field, new_json_value)
        ("Reverse Curl",    "primary_muscles",   _json.dumps(["biceps"])),
        ("Reverse Curl",    "secondary_muscles",  _json.dumps(["forearms"])),
        ("Upright Row",     "primary_muscles",   _json.dumps(["traps"])),
        ("Upright Row",     "secondary_muscles",  _json.dumps(["shoulders", "biceps"])),
        ("Band Pull-Apart", "mechanics",          "compound"),
        ("Shrug",           "equipment_required", _json.dumps(["barbell", "dumbbell"])),
    ]
    for name, field, value in fixes:
        ex = session.exec(select(Exercise).where(Exercise.name == name)).first()
        if ex and getattr(ex, field) != value:
            setattr(ex, field, value)
            session.add(ex)

    # Remove "cable upright row" alias from Upright Row
    upright = session.exec(select(Exercise).where(Exercise.name == "Upright Row")).first()
    if upright:
        aliases = _json.loads(upright.aliases)
        cleaned = [a for a in aliases if a.lower() != "cable upright row"]
        if cleaned != aliases:
            upright.aliases = _json.dumps(cleaned)
            session.add(upright)

    # Add missing secondary muscles
    secondary_additions = {
        "Cable Curl":                               "forearms",
        "Preacher Curl":                            "forearms",
        "Concentration Curl":                       "forearms",
        "Incline Dumbbell Curl":                    "forearms",
        "Machine Curl":                             "forearms",
        "Tricep Pushdown (rope)":                   "forearms",
        "Tricep Pushdown (bar)":                    "forearms",
        "Skull Crushers":                           "forearms",
        "Overhead Tricep Extension (dumbbell)":     "forearms",
        "Overhead Tricep Extension (cable)":        "forearms",
        "Kickback":                                 "forearms",
        "Dumbbell Flye":                            "shoulders",
        "Cable Crossover":                          "shoulders",
        "Pec Deck Machine":                         "shoulders",
    }
    for ex_name, muscle in secondary_additions.items():
        ex = session.exec(select(Exercise).where(Exercise.name == ex_name)).first()
        if not ex:
            continue
        secondaries = _json.loads(ex.secondary_muscles)
        if muscle not in secondaries:
            secondaries.append(muscle)
            ex.secondary_muscles = _json.dumps(secondaries)
            session.add(ex)

    session.commit()


def _backfill_landmark_goals(session: Session) -> None:
    """Seed goal-specific landmark rows for goals not yet in the DB."""
    from seed_data import LANDMARKS as _LANDMARKS
    existing = session.exec(select(MuscleVolumeLandmark)).all()
    existing_keys = {(lm.goal, lm.muscle, lm.user_id) for lm in existing}
    added = 0
    for goal, muscle, mev, mav_low, mav_high, mrv in _LANDMARKS:
        if (goal, muscle, 1) not in existing_keys:
            session.add(MuscleVolumeLandmark(
                user_id=1, goal=goal, muscle=muscle,
                mev=mev, mav_low=mav_low, mav_high=mav_high, mrv=mrv,
            ))
            added += 1
    if added:
        session.commit()
        print(f"Backfilled {added} landmark rows for new goals.")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    migrate_db()
    with Session(engine) as session:
        # Seed exercises if table is empty
        exercise_count = session.exec(select(Exercise)).all()
        if not exercise_count:
            from seed_data import seed
            seed(session)

        # Seed splits if table is empty
        split_count = session.exec(select(SplitTemplate)).all()
        if not split_count:
            from seed_data import seed_splits
            seed_splits(session)

        # Seed landmarks if table is empty
        landmark_count = session.exec(select(MuscleVolumeLandmark)).all()
        if not landmark_count:
            from seed_data import seed_landmarks
            seed_landmarks(session)

        # Ensure key exercises have all name-variant aliases for import matching
        _backfill_exercise_aliases(session)
        # Backfill sub_pattern for exercises seeded before this field existed
        _backfill_sub_patterns(session)
        # Backfill secondary_muscles for exercises seeded before this field was populated
        _backfill_secondary_muscles(session)
        # Merge abs/calves into compound exercises missing them
        _backfill_compound_secondaries(session)
        # Seed goal-specific landmark rows for any goals not yet in the DB
        _backfill_landmark_goals(session)
        # Remove redundant duplicate exercises (only if never logged)
        _purge_redundant_exercises(session)
        # Fix miscategorizations and add missing secondary muscles
        _fix_exercise_categories(session)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "liftforge"}


@app.delete("/api/reset")
def reset_app():
    """Wipe all user data. Keeps exercise library, split templates, and landmarks."""
    _WIPE_ORDER = [
        WorkoutSet, WorkoutSession, PersonalRecord, BodyMeasurement,
        Goal, PlannedExercise, PlannedSession, MesocycleWeek, Mesocycle,
        TemplateExercise, WorkoutTemplate, WeeklyCheckin, Injury,
    ]
    with Session(engine) as session:
        for model in _WIPE_ORDER:
            rows = session.exec(select(model)).all()
            for row in rows:
                session.delete(row)
        session.commit()
    return {"ok": True}
