import os
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:////app/data/liftforge.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def migrate_db():
    """Add columns that were introduced after initial DB creation."""
    new_cols = [
        ("workoutsession", "readiness_rating", "INTEGER"),
        ("workoutsession", "post_session_rpe", "INTEGER"),
        ("userprofile", "display_name", "TEXT DEFAULT 'Lifter'"),
        ("userprofile", "unit_preference", "TEXT DEFAULT 'lbs'"),
        ("userprofile", "experience_level", "TEXT DEFAULT 'intermediate'"),
        ("userprofile", "default_rest_seconds", "INTEGER DEFAULT 90"),
        ("userprofile", "liftsaur_api_token", "TEXT"),
        ("userprofile", "preferred_session_minutes", "INTEGER DEFAULT 60"),
        ("userprofile", "sex", "TEXT"),
        ("mesocycle", "periodization_type", "TEXT DEFAULT 'standard'"),
        ("workoutset", "set_type", "TEXT DEFAULT 'straight'"),
        ("workoutset", "rir", "INTEGER"),
        ("workoutset", "notes", "TEXT"),
        ("workoutset", "superset_group", "INTEGER"),
        ("plannedexercise", "superset_group", "INTEGER"),
        ("templateexercise", "superset_group", "INTEGER"),
        ("exercise", "sub_pattern", "TEXT DEFAULT ''"),
        ("mesocycle", "num_variants", "INTEGER DEFAULT 2"),
        ("mesocycle", "session_counter", "INTEGER DEFAULT 0"),
        ("musclevolumelandmark", "goal", "TEXT DEFAULT 'hypertrophy'"),
        ("plannedexercise", "set_technique", "TEXT DEFAULT 'straight'"),
    ]
    with engine.connect() as conn:
        for table, col, typedef in new_cols:
            try:
                existing = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                col_names = [row[1] for row in existing]
                if col not in col_names:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}"))
                    conn.commit()
            except Exception:
                pass


def get_session():
    with Session(engine) as session:
        yield session
