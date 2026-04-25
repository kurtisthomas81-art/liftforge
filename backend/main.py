from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, migrate_db, engine
from models import Exercise, SplitTemplate, MuscleVolumeLandmark
from sqlmodel import Session, select
from routers import exercises, sessions, history, profile, ollama
from routers import programs, landmarks, volume, prs, templates, measurements, export, recovery, liftsaur_sync

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


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "liftforge"}
