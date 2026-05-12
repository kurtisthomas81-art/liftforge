from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, migrate_db, engine
from models import Exercise, SplitTemplate, MuscleVolumeLandmark
from sqlmodel import Session, select
from routers import exercises, sessions, history, profile, ollama
from routers import programs, landmarks, volume, prs, templates, measurements, export, recovery, liftsaur_sync, goals, injuries, analytics

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

        # Backfill sub_pattern for exercises seeded before this field existed
        _backfill_sub_patterns(session)
        # Backfill secondary_muscles for exercises seeded before this field was populated
        _backfill_secondary_muscles(session)
        # Merge abs/calves into compound exercises missing them
        _backfill_compound_secondaries(session)
        # Seed goal-specific landmark rows for any goals not yet in the DB
        _backfill_landmark_goals(session)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "liftforge"}
