from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Exercise(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    aliases: str = Field(default="[]")          # JSON list of str
    movement_pattern: str = Field(default="")   # push|pull|hinge|squat|carry|core|isolation
    primary_muscles: str = Field(default="[]")  # JSON list of str
    secondary_muscles: str = Field(default="[]")
    equipment_required: str = Field(default="[]")
    mechanics: str = Field(default="compound")  # compound|isolation
    force: str = Field(default="push")          # push|pull|static|hinge
    is_bilateral: bool = Field(default=True)
    notes: str = Field(default="")
    substitution_ids: str = Field(default="[]") # JSON list of int
    is_custom: bool = Field(default=False)


class WorkoutSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    name: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)


class WorkoutSet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="workoutsession.id", index=True)
    exercise_id: int = Field(foreign_key="exercise.id", index=True)
    set_number: int = Field(default=1)
    weight: Optional[float] = Field(default=None)   # nullable for bodyweight
    reps: int = Field(default=0)
    rir: Optional[int] = Field(default=None)        # 0-4, nullable
    notes: Optional[str] = Field(default=None)


class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, unique=True, index=True)
    display_name: str = Field(default="Lifter")
    unit_preference: str = Field(default="lbs")    # lbs|kg
    experience_level: str = Field(default="intermediate")  # beginner|intermediate|advanced


class UserEquipment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    equipment: str = Field(default="")
    available: bool = Field(default=True)
