from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, engine
from models import Exercise
from sqlmodel import Session, select
from routers import exercises, sessions, history, profile, ollama

app = FastAPI(title="LiftForge API", version="1.0.0")

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


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # Seed exercises if table is empty
    with Session(engine) as session:
        count = session.exec(select(Exercise)).all()
        if not count:
            from seed_data import seed
            seed(session)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "liftforge"}
