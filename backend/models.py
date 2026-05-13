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
    sub_pattern: str = Field(default="")        # hip_dominant|knee_dominant|horizontal_push|vertical_push|horizontal_pull|vertical_pull|core|""


class WorkoutSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    name: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    readiness_rating: Optional[int] = Field(default=None)   # 1-5 pre-session
    post_session_rpe: Optional[int] = Field(default=None)   # 1-10 post-session
    source: Optional[str] = Field(default=None)             # "liftosaur" for synced imports


class WorkoutSet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="workoutsession.id", index=True)
    exercise_id: int = Field(foreign_key="exercise.id", index=True)
    set_number: int = Field(default=1)
    weight: Optional[float] = Field(default=None)   # nullable for bodyweight
    reps: int = Field(default=0)
    rir: Optional[int] = Field(default=None)        # 0-4, nullable
    notes: Optional[str] = Field(default=None)
    set_type: str = Field(default="straight")       # straight|warmup|drop|rest_pause
    rest_seconds: Optional[int] = Field(default=None)
    superset_group: Optional[int] = Field(default=None)  # exercises sharing same int are paired
    is_done: bool = Field(default=False)


class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, unique=True, index=True)
    display_name: str = Field(default="Lifter")
    unit_preference: str = Field(default="lbs")    # lbs|kg
    sex: Optional[str] = Field(default=None)       # male|female
    experience_level: str = Field(default="intermediate")  # beginner|intermediate|advanced
    default_rest_seconds: int = Field(default=90)
    liftsaur_api_token: Optional[str] = Field(default=None)
    preferred_session_minutes: int = Field(default=60)


class UserEquipment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    equipment: str = Field(default="")
    available: bool = Field(default=True)


class PersonalRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    exercise_id: int = Field(foreign_key="exercise.id", index=True)
    pr_type: str  # "e1rm"|"weight"|"reps"
    value: float
    achieved_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: int = Field(foreign_key="workoutsession.id")


# ── Program / Mesocycle tables ─────────────────────────────────────────────────

class SplitTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(unique=True)
    days_per_week: int
    split_type: str  # "full_body"|"upper_lower"|"ppl"|"bro"|"phul"|"phat"|"hybrid"|"custom"
    description: str = Field(default="")
    frequency_note: str = Field(default="")
    is_builtin: bool = Field(default=True)
    is_recommended: bool = Field(default=False)


class SplitDay(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="splittemplate.id")
    day_number: int  # 1-based
    name: str
    muscle_focus: str = Field(default="[]")  # JSON list of muscles


class MuscleVolumeLandmark(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    goal: str = Field(default="hypertrophy")  # hypertrophy|general_fitness|strength|recomp
    muscle: str
    mev: int
    mav_low: int
    mav_high: int
    mrv: int


class Mesocycle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    name: str
    split_template_id: Optional[int] = Field(default=None, foreign_key="splittemplate.id")
    weeks_total: int = Field(default=5)
    current_week: int = Field(default=1)
    status: str = Field(default="active")  # active|completed|abandoned
    goal: str = Field(default="hypertrophy")  # hypertrophy|strength|recomp
    start_date: Optional[str] = Field(default=None)  # ISO date string
    deload_week: int = Field(default=5)
    periodization_type: str = Field(default="standard")  # standard|linear|dup|block|double_progression|wave_loading
    num_variants: int = Field(default=2)        # 1=no variation, 2=A/B, 3=A/B/C
    session_counter: int = Field(default=0)     # incremented each time a session is started
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MesocycleWeek(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mesocycle_id: int = Field(foreign_key="mesocycle.id")
    week_number: int
    is_deload: bool = Field(default=False)


class PlannedSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mesocycle_week_id: int = Field(foreign_key="mesocycleweek.id")
    split_day_id: Optional[int] = Field(default=None, foreign_key="splitday.id")
    day_of_week: int  # 0=Mon, 6=Sun
    session_id: Optional[int] = Field(default=None, foreign_key="workoutsession.id")


class PlannedExercise(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    planned_session_id: int = Field(foreign_key="plannedsession.id")
    exercise_id: int = Field(foreign_key="exercise.id")
    order_in_session: int = Field(default=1)
    target_sets: int
    target_reps_min: int
    target_reps_max: int
    target_rir: int = Field(default=2)
    notes: str = Field(default="")
    superset_group: Optional[int] = Field(default=None)
    set_technique: str = Field(default="straight")  # straight|drop|rest_pause|myorep


# ── Phase 3 tables ─────────────────────────────────────────────────────────────

class WorkoutTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1)
    name: str
    notes: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TemplateExercise(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="workouttemplate.id")
    exercise_id: int = Field(foreign_key="exercise.id")
    order_in_template: int = Field(default=1)
    target_sets: int = Field(default=3)
    target_reps_min: int = Field(default=8)
    target_reps_max: int = Field(default=12)
    target_rir: int = Field(default=2)
    notes: str = Field(default="")
    superset_group: Optional[int] = Field(default=None)


class WeeklyCheckin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    week_start: str                           # ISO Monday date "YYYY-MM-DD"
    energy: int                               # 1–5
    sleep_quality: int                        # 1–5
    stress: int                               # 1–5  (5 = most stressed)
    soreness: int                             # 1–5
    notes: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Goal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    exercise_id: int = Field(foreign_key="exercise.id", index=True)
    goal_type: str                                    # e1rm | weight | reps
    target_value: float
    deadline: Optional[str] = Field(default=None)    # ISO date YYYY-MM-DD
    status: str = Field(default="active")            # active | achieved | expired
    achieved_at: Optional[datetime] = Field(default=None)
    achieved_session_id: Optional[int] = Field(default=None, foreign_key="workoutsession.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Injury(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    body_part: str   # shoulder|elbow|wrist|lower_back|upper_back|hip|knee|ankle|neck
    severity: str = Field(default="mild")   # mild|moderate|severe
    notes: str = Field(default="")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExerciseImportQueue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    raw_name: str                           # exact string from the import source
    source: str = Field(default="liftosaur")
    status: str = Field(default="pending")  # pending | resolved | dismissed
    resolved_exercise_id: Optional[int] = Field(default=None)
    pending_sets: str = Field(default="[]") # JSON: [{session_id, set_number, weight, reps, set_type}]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BodyMeasurement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=1)
    date: str  # ISO date string "YYYY-MM-DD"
    body_weight: Optional[float] = Field(default=None)
    body_fat_pct: Optional[float] = Field(default=None)
    waist_in: Optional[float] = Field(default=None)
    chest_in: Optional[float] = Field(default=None)
    hips_in: Optional[float] = Field(default=None)
    left_arm_in: Optional[float] = Field(default=None)
    right_arm_in: Optional[float] = Field(default=None)
    left_quad_in: Optional[float] = Field(default=None)
    right_quad_in: Optional[float] = Field(default=None)
    notes: str = Field(default="")
