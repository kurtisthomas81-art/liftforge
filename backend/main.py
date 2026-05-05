from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, migrate_db, engine
from models import Exercise, SplitTemplate, MuscleVolumeLandmark
from sqlmodel import Session, select
from routers import exercises, sessions, history, profile, ollama
from routers import programs, landmarks, volume, prs, templates, measurements, export, recovery, liftsaur_sync, goals, injuries

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


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "liftforge"}
