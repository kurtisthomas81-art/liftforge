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
        ("userprofile", "liftsaur_api_token", "TEXT"),
    ]
    with engine.connect() as conn:
        for table, col, typedef in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}"))
                conn.commit()
            except Exception:
                pass  # column already exists


def get_session():
    with Session(engine) as session:
        yield session
